"""Compare old and 2025-updated DEA drafts, without changing canonical data."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {"municipality", "municipality_code", "nearest_dea_code",
            "travel_time_minutes", "distance_km"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(folder: Path, label: str, expected: set[str], errors: list[str]) -> tuple[dict, dict]:
    data = folder / "dea_accessibility_minutes.csv"
    qa_file = folder / "dea_accessibility_qa.json"
    qa = json.loads(qa_file.read_text(encoding="utf-8"))
    with data.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not REQUIRED <= set(reader.fieldnames or ()):
            raise ValueError(f"{label}: missing required DEA columns")
        records = list(reader)
    by_code = {row["municipality_code"]: row for row in records}
    if len(records) != 27 or len(by_code) != 27 or set(by_code) != expected:
        errors.append(f"{label}: 27 origin codes or canonical registry mismatch")
    if qa.get("data_csv_sha256") != sha256(data):
        errors.append(f"{label}: data SHA does not match corresponding QA")
    if qa.get("indicator_id") != "dea_accessibility":
        errors.append(f"{label}: QA indicator mismatch")
    if qa.get("origin_count") != 27 or qa.get("route_pair_count") != qa.get("expected_route_pairs"):
        errors.append(f"{label}: incomplete QA route grid")
    if qa.get("validated_for_release") is not False:
        errors.append(f"{label}: draft must not be treated as released")
    return by_code, qa


def evaluate(old_dir: Path, new_dir: Path, registry: Path, hospitals: Path) -> dict:
    with registry.open(encoding="utf-8", newline="") as f:
        canonical = list(csv.DictReader(f))
    expected = {row["istat_code"] for row in canonical}
    if len(canonical) != 27 or len(expected) != 27:
        raise ValueError("The canonical municipality registry must contain 27 unique codes")
    problems: list[str] = []
    old, old_qa = _load(old_dir, "baseline", expected, problems)
    new, new_qa = _load(new_dir, "2025 candidate", expected, problems)
    if new_qa.get("hospital_snapshot_reference_years") != ["2025"]:
        problems.append("2025 draft does not use only the 2025 hospital reference")
    if new_qa.get("hospitals_csv_sha256") != sha256(hospitals):
        problems.append("2025 hospital reference SHA mismatch")
    if new_qa.get("hospital_facility_count") != 30 or new_qa.get("eligible_dea_municipality_count") != 23:
        problems.append("2025 facility or municipality count mismatch")
    comparisons = []
    for code in sorted(expected):
        if code not in old or code not in new:
            continue
        a, b = old[code], new[code]
        try:
            old_minutes = Decimal(a["travel_time_minutes"])
            new_minutes = Decimal(b["travel_time_minutes"])
            old_km = Decimal(a["distance_km"])
            new_km = Decimal(b["distance_km"])
            if not all(v.is_finite() and v >= 0 for v in (old_minutes, new_minutes, old_km, new_km)):
                raise ValueError("Invalid time or km")
        except (InvalidOperation, ValueError) as exc:
            problems.append(f"{code}: invalid time/distance: {exc}")
            continue
        comparisons.append({
            "municipality_code": code,
            "municipality": b["municipality"],
            "old_destination": a["nearest_dea_code"],
            "new_destination": b["nearest_dea_code"],
            "old_minutes": str(old_minutes),
            "new_minutes": str(new_minutes),
            "difference_minutes": str(new_minutes - old_minutes),
            "old_km": str(old_km),
            "new_km": str(new_km),
            "destination_changed": a["nearest_dea_code"] != b["nearest_dea_code"],
            "minutes_changed": old_minutes != new_minutes,
            "km_changed": old_km != new_km,
        })
    return {
        "indicator_id": "dea_accessibility",
        "technical_consistency_pass": not problems and len(comparisons) == 27,
        "technical_blockers": problems,
        "rows_compared": len(comparisons),
        "new_ministry_reference_sha256": sha256(hospitals),
        "baseline_data_sha256": old_qa.get("data_csv_sha256"),
        "new_data_sha256": new_qa.get("data_csv_sha256"),
        "municipalities_with_changed_destination": sum(x["destination_changed"] for x in comparisons),
        "municipalities_with_changed_minutes": sum(x["minutes_changed"] for x in comparisons),
        "municipalities_with_changed_distance": sum(x["km_changed"] for x in comparisons),
        "rows": comparisons,
        "validated_for_release": False,
        "human_review_required": True,
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Compare two DEA candidates, fail closed on QA integrity")
    p.add_argument("--old-dir", type=Path, required=True)
    p.add_argument("--new-dir", type=Path, required=True)
    p.add_argument("--registry", type=Path, default=ROOT / "data/municipalities.csv")
    p.add_argument("--hospitals", type=Path, default=ROOT / "data/reference/piemonte_dea_hospitals.csv")
    p.add_argument("--out-dir", type=Path, default=ROOT / "outputs/quality/dea_2025_draft_comparison")
    p.add_argument("--strict", action="store_true")
    a = p.parse_args()
    if a.out_dir.exists():
        raise FileExistsError("Use a fresh --out-dir; existing comparison evidence must not be overwritten")
    report = evaluate(a.old_dir, a.new_dir, a.registry, a.hospitals)
    a.out_dir.mkdir(parents=True)
    (a.out_dir / "comparison.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"DEA candidate comparison: {report['rows_compared']}/27; technical pass={report['technical_consistency_pass']}")
    for label in ("municipalities_with_changed_destination", "municipalities_with_changed_minutes",
                  "municipalities_with_changed_distance"):
        print(f"{label}: {report[label]}")
    for item in report["rows"]:
        if item["minutes_changed"] or item["destination_changed"]:
            print(f"{item['municipality']}: {item['old_destination']} {item['old_minutes']} -> "
                  f"{item['new_destination']} {item['new_minutes']} minutes")
    if report["technical_blockers"]:
        print("Integrity blockers: " + "; ".join(report["technical_blockers"]))
    print("Human scientific review still required; no canonical data changed.")
    if a.strict and not report["technical_consistency_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
