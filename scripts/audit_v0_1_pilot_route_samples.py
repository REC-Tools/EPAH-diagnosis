"""Inspect 3 original ISTAT road records per accessibility indicator for the 27-town v0.1.

Read-only evidence. Does not sign human approvals, alter canonical values,
claim national nearest-service coverage, or replace source/license review.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import zipfile
from pathlib import Path

from epah_diagnosis.service_access import _as_float, _detect_delimiter, _matrix_columns

ROOT = Path(__file__).resolve().parents[1]
ORIGINS = ("001073", "001224", "001066")  # Ceresole Reale, Ronco Canavese, Castellamonte
INPUTS = {
    "dea_accessibility": ("dea_accessibility_minutes.csv", "dea_accessibility_qa.json", "nearest_dea_code"),
    "rail_accessibility": ("rail_accessibility_minutes.csv", "rail_accessibility_qa.json", "nearest_service_code"),
    "upper_secondary_accessibility": ("upper_secondary_accessibility_minutes.csv", "upper_secondary_accessibility_qa.json", "nearest_service_code"),
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize_code(value: object) -> str:
    code = str(value or "").strip()
    return code.zfill(6) if code.isdigit() and 1 <= len(code) <= 6 else ""


def load_draft(kind: str, path: Path, source_sha: str) -> list[dict]:
    csv_name, qa_name, dest_field = INPUTS[kind]
    qa = json.loads((path / qa_name).read_text(encoding="utf-8"))
    file = path / csv_name
    if any((qa.get("indicator_id") != kind, qa.get("origin_count") != 27,
            qa.get("qa_status") != "technical_checks_only",
            qa.get("validated_for_release") is not False)):
        raise ValueError(f"{kind}: draft is not the expected 27-town technical QA")
    if qa.get("road_zip_sha256") != source_sha or qa.get("data_csv_sha256") != sha256(file):
        raise ValueError(f"{kind}: original road source or draft checksum has changed")
    with file.open(encoding="utf-8-sig", newline="") as handle:
        records = list(csv.DictReader(handle))
    by_code = {r["municipality_code"]: r for r in records}
    if len(records) != 27 or len(by_code) != 27 or set(ORIGINS) - set(by_code):
        raise ValueError(f"{kind}: expected the same 27 origin municipalities")
    return [
        {
            "indicator_id": kind,
            "origin": origin,
            "origin_name": by_code[origin]["municipality"],
            "destination": by_code[origin][dest_field],
            "declared_minutes": by_code[origin]["travel_time_minutes"],
            "declared_km": by_code[origin]["distance_km"],
        } for origin in ORIGINS
    ]


def source_route_evidence(archive_path: Path, sample_pairs: set[tuple[str, str]]) -> dict:
    found = {}
    schema = False
    origins = {o for o, _ in sample_pairs}
    destinations = {d for _, d in sample_pairs}
    with zipfile.ZipFile(archive_path) as archive:
        filenames = sorted(x for x in archive.namelist() if x.lower().endswith(".csv"))
        if not filenames:
            raise ValueError("No original ISTAT road CSVs found")
        for name in filenames:
            with archive.open(name) as raw:
                stream = io.TextIOWrapper(raw, encoding="utf-8-sig", errors="replace", newline="")
                delimiter = _detect_delimiter(stream.read(8192))
                stream.seek(0)
                reader = csv.DictReader(stream, delimiter=delimiter)
                if not reader.fieldnames:
                    continue
                try:
                    fields = _matrix_columns(reader.fieldnames)
                except ValueError:
                    continue
                if "distance" not in fields:
                    raise ValueError("Original ISTAT road CSV lacks KM_TOT")
                schema = True
                for row_number, row in enumerate(reader, 2):
                    origin = normalize_code(row.get(fields["origin_code"]))
                    if origin not in origins:
                        continue
                    dest = normalize_code(row.get(fields["destination_code"]))
                    key = origin, dest
                    if dest not in destinations or key not in sample_pairs:
                        continue
                    if key in found:
                        raise ValueError(f"Duplicate original ISTAT road pair {key}")
                    minutes = _as_float(row.get(fields["time"]))
                    km = _as_float(row.get(fields["distance"]))
                    if not (math.isfinite(minutes) and math.isfinite(km) and
                            0 <= minutes <= 1440 and 0 <= km <= 3000):
                        raise ValueError(f"Invalid original route pair {key}")
                    found[key] = {"original_minutes": minutes, "original_km": km,
                                  "zip_member": name, "original_csv_row": row_number}
    if not schema:
        raise ValueError("No usable ISTAT road table schema")
    return found


def audit(road_zip: Path, drafts: dict[str, Path]) -> dict:
    origin_sha = sha256(road_zip)
    selected = [r for kind, path in drafts.items() for r in load_draft(kind, path, origin_sha)]
    pairs = {(r["origin"], r["destination"]) for r in selected}
    evidence = source_route_evidence(road_zip, pairs)
    results = []
    for record in selected:
        pair = record["origin"], record["destination"]
        found = evidence.get(pair)
        matched = bool(found and
                       abs(found["original_minutes"] - float(record["declared_minutes"])) <= .011
                       and abs(found["original_km"] - float(record["declared_km"])) <= .011)
        results.append({**record, **(found or {}), "matches_original": matched})
    return {
        "review_scope": "v0.1 27 original municipalities; curated service destinations",
        "road_zip_sha256": origin_sha,
        "sampled_origin_codes": list(ORIGINS),
        "sampled_indicators": sorted(drafts),
        "comparisons": results,
        "routes_checked": len(results),
        "matches": sum(r["matches_original"] for r in results),
        "technical_pass": bool(len(results) == 9 and all(r["matches_original"] for r in results)),
        "validated_for_release": False,
        "human_review_required": True,
        "limitations": "9 exact original route cross-checks only; no national service coverage and no human sign-off.",
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Audit nine ISTAT original sample routes; no data promotion")
    p.add_argument("--road-zip", type=Path, default=ROOT / "data/downloads/Piemonte.zip")
    p.add_argument("--dea-draft", type=Path, default=ROOT / "outputs/quality/dea_accessibility_2025_v03")
    p.add_argument("--rail-draft", type=Path, default=ROOT / "outputs/quality/rail_accessibility_v01")
    p.add_argument("--school-draft", type=Path, default=ROOT / "outputs/quality/upper_secondary_accessibility_v01")
    p.add_argument("--out-dir", type=Path, default=ROOT / "outputs/quality/v0_1_pilot_route_samples_v01")
    p.add_argument("--strict", action="store_true")
    args = p.parse_args()
    if args.out_dir.exists():
        raise FileExistsError("Use a new --out-dir; previous route evidence cannot be overwritten")
    report = audit(args.road_zip, {
        "dea_accessibility": args.dea_draft, "rail_accessibility": args.rail_draft,
        "upper_secondary_accessibility": args.school_draft,
    })
    args.out_dir.mkdir(parents=True)
    (args.out_dir / "samples.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"v0.1 samples: {report['matches']}/{report['routes_checked']} match the original ISTAT ZIP")
    print("Technical sample audit:", "PASS" if report["technical_pass"] else "BLOCKED")
    print("Human source/license and methodology sign-offs are still required.")
    if args.strict and not report["technical_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
