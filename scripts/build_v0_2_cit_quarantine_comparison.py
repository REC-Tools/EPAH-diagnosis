"""Cross-check the two QA-only CIT outputs, excluding unresolved municipalities.

Reads only quarantine artifacts from prepare_piemonte_cit_wide.py.
Produces no map, no release-ready artifact, and no canonical changes.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data/municipalities.csv"
QA_FUEL = ROOT / "outputs/quality/cit_fuel_quarantine_v02"
QA_AGE = ROOT / "outputs/quality/cit_age_quarantine_v02"
OUT = ROOT / "outputs/quality/cit_quarantine_comparison_v02"
EXPECTED_SOURCE_HASHES = {
    "fuel": "7659242c31a4dd47d24e4d65b9075f90845a8f81829eff27cf485c24027793b4",
    "age": "4b506567cb3ea3aeb355eed021a30aa83f4c55d6729e9ae99bb825e71484712a",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1_048_576), b""):
            h.update(part)
    return h.hexdigest()


def registry_codes(path: Path) -> dict[str, str]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        entries = list(csv.DictReader(stream))
    codes = {entry["istat_code"]: entry["municipality"] for entry in entries}
    if len(entries) != 27 or len(codes) != 27 or len(set(codes.values())) != 27:
        raise ValueError("Expected 27 unique registry municipalities")
    return codes


def parse_count(value: str, label: str) -> int:
    text = str(value or "")
    if not text.isdigit():
        raise ValueError(f"{label} is not an integer count: {value!r}")
    return int(text)


def checked_percent(value: str, numerator: int, denominator: int, label: str) -> float:
    if denominator <= 0 or numerator < 0 or numerator > denominator:
        raise ValueError(f"{label}: invalid numerator/denominator")
    try:
        percentage = float(value)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"{label}: missing or invalid percent") from exc
    if not math.isfinite(percentage) or abs(percentage - 100 * numerator / denominator) > 0.011:
        raise ValueError(f"{label}: displayed percent inconsistent with counts")
    return percentage


def load_quarantine(folder: Path, mode: str, registry: dict[str, str],
                    registry_hash: str) -> tuple[dict[str, dict], dict, dict]:
    filename = "cit_fuel_27.csv" if mode == "fuel" else "cit_generator_age_27.csv"
    csv_file, qa_file, conflicts_file = (
        folder / filename, folder / "cit_qa.json",
        folder / "cit_conflicts_for_review.json"
    )
    qa = json.loads(qa_file.read_text(encoding="utf-8"))
    review = json.loads(conflicts_file.read_text(encoding="utf-8"))
    quarantined = qa.get("quarantined_municipalities")
    if (qa.get("qa_status") != "technical_incomplete_do_not_publish"
            or qa.get("validated_for_release") is not False
            or qa.get("source_matches_user_inspection_hash") is not True
            or qa.get("source_csv_sha256") != EXPECTED_SOURCE_HASHES[mode]
            or qa.get("registry_csv_sha256") != registry_hash
            or qa.get("output_csv_sha256") != sha256(csv_file)
            or qa.get("municipalities_expected") != 27
            or qa.get("municipalities_with_generator_data") != 26
            or qa.get("source_schema", {}).get("conflict_policy") != "quarantine_without_resolving"
            or quarantined != ["001199"]
            or review.get("quarantined_municipalities") != quarantined
            or review.get("source_csv_sha256") != qa.get("source_csv_sha256")
            or review.get("status") != "human_source_review_required"
            or review.get("conflicts") !=
                qa.get("source_schema", {}).get("quarantined_duplicate_conflicts")
            or qa.get("indicator_id") != (
                "cit_diesel_lpg_generator_share" if mode == "fuel"
                else "cit_older_generator_share")):
        raise ValueError(f"{mode}: not a verified 26/27 technical quarantine")
    if (len(review["conflicts"]) != 1
            or review["conflicts"][0]["istat_code"] != "001199"
            or review["conflicts"][0]["status"] != "conflicting_counts"
            or len(review["conflicts"][0].get("source_records", [])) < 2):
        raise ValueError(f"{mode}: inadequate conflicting-source provenance")
    with csv_file.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != 27 or len({r.get("istat_code") for r in rows}) != 27:
        raise ValueError(f"{mode}: expected exactly 27 distinct rows")
    result = {}
    for row in rows:
        code = row["istat_code"]
        if code not in registry or row["municipality"] != registry[code]:
            raise ValueError(f"{mode}: registry mismatch")
        if code in quarantined:
            if (row.get("observation_status") != "source_conflict_quarantined"
                    or row.get("generator_groups_total") != ""
                    or row.get("diesel_lpg_share_pct" if mode == "fuel"
                               else "older_generator_share_pct") != ""):
                raise ValueError(f"{mode}: quarantined value cannot be numeric")
            continue
        if row.get("observation_status") != "technical_observation":
            raise ValueError(f"{mode}: other municipalities must have measured counts")
        groups = parse_count(row["generator_groups_total"], f"{code} groups")
        if mode == "fuel":
            known = parse_count(row["classified_groups"], f"{code} classified")
            unknown = parse_count(row["unclassified_groups"], f"{code} unknown")
            components = ["natural_gas_groups", "diesel_groups", "lpg_groups",
                          "solid_fuels_groups", "electricity_groups", "other_groups"]
            fuel_counts = [parse_count(row[x], f"{code} {x}") for x in components]
            numerator = fuel_counts[1] + fuel_counts[2]
            if (known + unknown != groups or sum(fuel_counts) != known
                    or row["denominator"] != "classified_generator_groups"):
                raise ValueError(f"{code}: fuel count totals inconsistent")
            score = checked_percent(row["diesel_lpg_share_pct"], numerator,
                                    known, f"{code} diesel+LPG")
            value = {"numerator": numerator, "denominator": known,
                     "groups": groups, "share_pct": score}
        else:
            known = parse_count(row["groups_with_known_year"], f"{code} dated")
            unknown = parse_count(row["groups_with_unknown_year"], f"{code} undated")
            older = parse_count(row["groups_aged_20_or_more"], f"{code} older")
            ambiguous = parse_count(row["groups_ambiguous_age"], f"{code} ambiguous")
            if (known + unknown != groups or older + ambiguous > known
                    or row["denominator"] != "generator_groups_with_known_installation_year"):
                raise ValueError(f"{code}: age bin totals inconsistent")
            lower = checked_percent(row["older_generator_share_pct"], older,
                                    known, f"{code} 20y lower bound")
            upper = checked_percent(row["older_upper_bound_share_pct"],
                                    older + ambiguous, known,
                                    f"{code} 20y upper bound")
            value = {"numerator": older, "denominator": known,
                     "groups": groups, "share_pct": lower,
                     "upper_bound_pct": upper, "ambiguous_groups": ambiguous}
        result[code] = value
    if len(result) != 26 or "001199" in result:
        raise ValueError(f"{mode}: expected 26 uncontested codes, excluding Pont")
    if mode == "age":
        if (qa.get("age_metric") != "conservative_lower_bound_for_20_years"
                or qa.get("older_years_threshold") != 20
                or sum(x["ambiguous_groups"] for x in result.values()) !=
                    qa.get("age_interval_uncertainty_groups")):
            raise ValueError("Age threshold/uncertainty fails QA reconciliation")
    return result, qa, review


def create_review(fuel_dir: Path, age_dir: Path, registry_path: Path,
                  destination: Path) -> Path:
    if destination.exists():
        raise FileExistsError("Preserve previous QA evidence; choose a fresh --out-dir")
    registry = registry_codes(registry_path)
    registry_hash = sha256(registry_path)
    fuel, fuel_qa, fuel_review = load_quarantine(
        fuel_dir, "fuel", registry, registry_hash)
    age, age_qa, age_review = load_quarantine(
        age_dir, "age", registry, registry_hash)
    if set(fuel) != set(age) or len(set(fuel) & set(age)) != 26:
        raise ValueError("Inconsistent 26-town CIT coverage between two sources")
    if (fuel_qa["snapshot_date_operator_reported"] !=
            age_qa["snapshot_date_operator_reported"]):
        raise ValueError("Fuel/age local reference dates differ")
    joined = []
    for code in sorted(fuel, key=lambda c: registry[c]):
        f, a = fuel[code], age[code]
        joined.append({
            "municipality": registry[code], "istat_code": code,
            "fuel_gasolio_gpl_n": f["numerator"],
            "fuel_classified_groups_n": f["denominator"],
            "fuel_gasolio_gpl_share_pct": f"{f['share_pct']:.2f}",
            "age_certain_20plus_n": a["numerator"],
            "age_dated_groups_n": a["denominator"],
            "age_ambiguous_bin_n": a["ambiguous_groups"],
            "age_minimum_20plus_pct": f"{a['share_pct']:.2f}",
            "age_maximum_20plus_pct": f"{a['upper_bound_pct']:.2f}",
            "observation_status": "technical_QA_only",
            "analysis_reference_date": fuel_qa["snapshot_date_operator_reported"],
        })
    def aggregate(results):
        numerator = sum(r["numerator"] for r in results.values())
        denominator = sum(r["denominator"] for r in results.values())
        return {"numerator": numerator, "denominator": denominator,
                "pooled_pct": round(100 * numerator / denominator, 2),
                "mean_municipal_pct": round(
                    statistics.fmean(r["share_pct"] for r in results.values()), 2)}
    summary = {
        "status": "technical_QA_only_incomplete_do_not_publish",
        "project": "26-IT-Unione-TA26",
        "scope": "26 of 27 municipalities; Pont Canavese intentionally excluded",
        "valid_municipalities": 26, "municipalities_expected": 27,
        "excluded": [{"istat_code": "001199", "municipality": registry["001199"],
                      "reason": "conflicting_official_source_rows"}],
        "fuel": aggregate(fuel), "age_minimum": aggregate(age),
        "age_uncertainty_groups": sum(
            r["ambiguous_groups"] for r in age.values()),
        "age_pooled_upper_pct": round(100 * (
            sum(r["numerator"] + r["ambiguous_groups"] for r in age.values()) /
            sum(r["denominator"] for r in age.values())), 2),
        "reference_date_not_original_snapshot": fuel_qa["snapshot_date_operator_reported"],
        "source_checksums": EXPECTED_SOURCE_HASHES,
        "limits": [
            "Missing Pont Canavese is not zero; exclude from all statistics.",
            "Fuel and installation denominators count generator groups, not households.",
            "20y installation age is a lower/upper interval, not a precise percent.",
            "Statistics describe only 26 uncontested municipalities.",
            "This technical QA output cannot be used as the final EPAH CIT PDF.",
        ],
    }
    conflicts = {
        "status": "human_source_review_required",
        "source_data_modified": False,
        "excluded_istat_code": "001199",
        "fuel": fuel_review,
        "age": age_review,
        "interpretation": "No source record selected, summed or overwritten.",
        "next_action": "Request clarification of overlapping CIT municipality aggregates "
                       "from Regione Piemonte/CSI Piemonte.",
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".cit-26-qa-", dir=destination.parent) as temp:
        stage = Path(temp) / "review"
        stage.mkdir()
        output_csv = stage / "cit_26_municipality_technical_comparison.csv"
        with output_csv.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(joined[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(joined)
        (stage / "cit_26_qa_summary.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8")
        (stage / "cit_pont_canavese_source_review.json").write_text(
            json.dumps(conflicts, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8")
        (stage / "README.md").write_text(
            "# CIT: 26 Comuni, solo controllo tecnico\n\n"
            "I due CSV CIT originali presentano conteggi discordanti per "
            "Pont Canavese (ISTAT 001199): non e stato calcolato alcun valore "
            "per quel Comune. I dati dei restanti 26 Comuni sono preliminari. "
            "Non pubblicare o inserire nel PDF EPAH v0.2 come dati validati. "
            "I 6.881 gruppi nella classe di eta ambigua (dato osservato "
            "nei log del 30/10/2026) non sono duplicati di Pont; "
            "il numero effettivo e ricalcolato dai file locali.\n",
            encoding="utf-8")
        summary["output_csv_sha256"] = sha256(output_csv)
        (stage / "cit_26_qa_summary.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8")
        stage.rename(destination)
    return destination


def main() -> None:
    p = argparse.ArgumentParser(
        description="Join the verified 26-town CIT quarantine outputs for internal QA")
    p.add_argument("--fuel-dir", type=Path, default=QA_FUEL)
    p.add_argument("--age-dir", type=Path, default=QA_AGE)
    p.add_argument("--registry", type=Path, default=REGISTRY)
    p.add_argument("--out-dir", type=Path, default=OUT)
    args = p.parse_args()
    target = create_review(args.fuel_dir, args.age_dir, args.registry, args.out_dir)
    print("CIT QUARANTINE CROSS-CHECK: 26/27, PONT CANAVESE EXCLUDED")
    print("STATUS: INTERNAL QA ONLY - NO RELEASE / NO PDF / NO MAP")
    print("Files:", target)


if __name__ == "__main__":
    main()
