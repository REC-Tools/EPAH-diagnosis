"""Fail-closed v0.1 release readiness, with separate data, review and artifact gates.

The offline checks do not certify a source or authenticate a human reviewer.
They only verify structured evidence and detect missing prerequisites.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

from epah_diagnosis.cli import read_municipalities


ROOT = Path(__file__).resolve().parents[1]
RELEASE_CONFIG = ROOT / "config" / "release_v0_1.json"
CATALOG_FILE = ROOT / "config" / "indicators.json"
REVIEWS_FILE = ROOT / "config" / "release_reviews_v0_1.json"
MATRIX_FILE = ROOT / "data" / "verification_matrix.csv"
MUNICIPALITIES_FILE = ROOT / "data" / "municipalities.csv"
OUTPUT_DIR = ROOT / "outputs" / "v0.1"

REQUIRED_COLUMNS = {
    "municipality", "indicator_id", "status", "value", "year",
    "unit", "source_url", "quality", "limitations",
}
UNIT_ALIASES = {
    "%": {"%"},
    "GG": {"GG"},
    "m": {"m", "m s.l.m."},
    "class": {"class", "classe A-F"},
    "minutes": {"minutes", "minuti"},
}
PERCENT_INDICATORS = {
    "population_65_plus", "income_vulnerability", "old_building_stock",
}
ALLOWED_MATURITY = {"OPERATIONAL", "VALIDATED"}
AFFORDABILITY_SUBINDICATORS = {
    "inability_keep_home_warm", "utility_bill_arrears",
    "inability_keep_home_cool", "reduced_heating_for_cost",
}


def _valid_url(value: str) -> bool:
    try:
        parsed = urlsplit(value)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except ValueError:
        return False


def _valid_date(value: str) -> bool:
    try:
        return date.fromisoformat(value).isoformat() == value
    except (ValueError, TypeError):
        return False


def _value_problem(indicator_id: str, value: str, unit: str) -> str | None:
    if not value:
        return "empty value"
    if unit == "class":
        if indicator_id == "snai_classification" and value not in set("ABCDEF"):
            return "SNAI class must be A-F"
        return None
    try:
        number = float(value)
    except ValueError:
        return "value is not numeric"
    if not math.isfinite(number):
        return "value is not finite"
    if indicator_id in PERCENT_INDICATORS or unit == "%":
        if not 0 <= number <= 100:
            return "percentage outside 0-100"
    elif indicator_id == "heating_degree_days":
        if not 0 <= number <= 10000:
            return "heating degree days outside 0-10000"
    elif indicator_id == "mean_altitude":
        if not -500 <= number <= 9000:
            return "altitude outside -500..9000 m"
    elif unit == "minutes":
        if not 0 <= number <= 1440:
            return "travel time outside 0-1440 minutes"
    return None


def _methodology_reviews(
    core: tuple[str, ...],
    catalog: dict[str, dict],
    reviews_file: Path,
) -> dict[str, list[str]]:
    failures: dict[str, list[str]] = defaultdict(list)
    if not reviews_file.is_file():
        failures["manifest"].append("review manifest missing")
        return dict(failures)

    try:
        data = json.loads(reviews_file.read_text(encoding="utf-8"))
        entries = data["methodology_approvals"]
        if not isinstance(entries, list):
            raise ValueError("methodology_approvals must be a list")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        failures["manifest"].append(f"invalid review manifest: {exc}")
        return dict(failures)

    indexed: dict[str, dict] = {}
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("indicator_id"), str):
            failures["manifest"].append("review entry lacks indicator_id")
            continue
        identifier = entry["indicator_id"]
        if identifier in indexed:
            failures["manifest"].append(f"duplicate review entry: {identifier}")
        if identifier not in core:
            failures["manifest"].append(f"unexpected review entry: {identifier}")
        indexed[identifier] = entry

    for identifier in core:
        indicator = catalog.get(identifier, {})
        if indicator.get("methodological_maturity") not in ALLOWED_MATURITY:
            failures[identifier].append("catalog maturity must be OPERATIONAL or VALIDATED")
        review = indexed.get(identifier)
        if review is None:
            failures[identifier].append("human methodology approval missing")
            continue
        if review.get("decision") != "approved":
            failures[identifier].append("decision is not approved")
        if not isinstance(review.get("reviewed_by"), str) or not review["reviewed_by"].strip():
            failures[identifier].append("reviewer missing")
        if not _valid_date(review.get("reviewed_on")):
            failures[identifier].append("invalid review date")
        evidence = review.get("evidence_url")
        if not isinstance(evidence, str) or not _valid_url(evidence):
            failures[identifier].append("review evidence URL missing or invalid")

    return dict(failures)


def _artifact_problems(required: list, output_dir: Path) -> list[str]:
    failures: list[str] = []
    if not required:
        return ["required_artifacts is empty or missing"]
    root = output_dir.resolve()
    for item in required:
        if not isinstance(item, str) or not item.strip():
            failures.append("invalid artifact path")
            continue
        path = (root / item).resolve()
        if not path.is_relative_to(root):
            failures.append(f"artifact path escapes output directory: {item}")
        elif not path.is_file() or path.stat().st_size == 0:
            failures.append(f"missing or empty artifact: {item}")
    return failures


def evaluate(
    matrix_file: Path = MATRIX_FILE,
    municipalities_file: Path = MUNICIPALITIES_FILE,
    release_config: Path = RELEASE_CONFIG,
    catalog_file: Path = CATALOG_FILE,
    reviews_file: Path = REVIEWS_FILE,
    output_dir: Path = OUTPUT_DIR,
    phase: str = "inputs",
) -> dict:
    if phase not in {"inputs", "release"}:
        raise ValueError("phase must be 'inputs' or 'release'")
    release = json.loads(release_config.read_text(encoding="utf-8"))
    catalog_items = json.loads(catalog_file.read_text(encoding="utf-8"))["indicators"]
    municipalities = read_municipalities(municipalities_file)
    core = tuple(release["core_indicators"])
    catalog = {item["id"]: item for item in catalog_items}
    expected = set(municipalities)

    config_errors = []
    if len(municipalities) != release["release_criteria"]["municipalities"]:
        config_errors.append("municipality registry does not match release criteria")
    if not core or len(core) != len(set(core)):
        config_errors.append("core indicator IDs are empty or duplicated")
    if len(catalog_items) != len(catalog):
        config_errors.append("duplicate catalog IDs")
    if set(core) != set(catalog):
        config_errors.append("core indicator IDs do not match canonical catalog")

    with matrix_file.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        missing_columns = sorted(REQUIRED_COLUMNS - set(reader.fieldnames or []))
        if missing_columns:
            raise ValueError("Matrix missing required columns: " + ", ".join(missing_columns))
        rows = list(reader)

    indexed: dict[tuple[str, str], dict] = {}
    duplicates: set[tuple[str, str]] = set()
    unexpected_municipalities: set[str] = set()
    unexpected_indicators: set[str] = set()
    extensions = release.get("extensions", [])
    extension_ids = {item["id"] for item in extensions} | AFFORDABILITY_SUBINDICATORS

    for row in rows:
        municipality = row["municipality"].strip()
        identifier = row["indicator_id"].strip()
        key = (municipality, identifier)
        if key in indexed:
            duplicates.add(key)
        indexed[key] = row
        if municipality not in expected:
            unexpected_municipalities.add(municipality)
        if identifier not in core and identifier not in extension_ids:
            unexpected_indicators.add(identifier)

    missing: dict[str, list[str]] = defaultdict(list)
    unvalidated: dict[str, list[str]] = defaultdict(list)
    empty: dict[str, list[str]] = defaultdict(list)
    invalid: dict[str, dict[str, list[str]]] = defaultdict(dict)

    for identifier in core:
        expected_unit = catalog.get(identifier, {}).get("unit")
        for municipality in municipalities:
            row = indexed.get((municipality, identifier))
            if row is None:
                missing[identifier].append(municipality)
                continue
            if row["status"].strip() != "Dato validato":
                unvalidated[identifier].append(municipality)
            value = row["value"].strip()
            if not value:
                empty[identifier].append(municipality)
            if row["status"].strip() != "Dato validato":
                continue

            problems = []
            if not row["year"].strip():
                problems.append("missing reference year")
            if not row["quality"].strip():
                problems.append("missing quality description")
            if not row["limitations"].strip():
                problems.append("missing limitations")
            if not _valid_url(row["source_url"].strip()):
                problems.append("missing or invalid source URL")
            if not expected_unit or row["unit"].strip() not in UNIT_ALIASES.get(
                expected_unit, {expected_unit}
            ):
                problems.append("unit does not match catalog")
            issue = _value_problem(identifier, value, expected_unit or "")
            if issue and issue != "empty value":
                problems.append(issue)
            if problems:
                invalid[identifier][municipality] = problems

    data_blockers = {
        "configuration": config_errors,
        "duplicates": [list(key) for key in sorted(duplicates)],
        "unexpected_municipalities": sorted(unexpected_municipalities),
        "unexpected_indicators": sorted(unexpected_indicators),
        "missing_core": dict(missing),
        "unvalidated_core": dict(unvalidated),
        "empty_core_values": dict(empty),
        "invalid_validated_rows": dict(invalid),
    }
    data_ready = not any(data_blockers.values())
    review_blockers = _methodology_reviews(core, catalog, reviews_file)
    methodology_approved = not bool(review_blockers)
    inputs_ready = data_ready and methodology_approved
    artifact_blockers = (
        _artifact_problems(release.get("required_artifacts", []), output_dir)
        if phase == "release" else []
    )
    artifacts_ready = (not artifact_blockers) if phase == "release" else None
    release_ready = (inputs_ready and artifacts_ready) if phase == "release" else False

    extension_status = []
    for extension in extensions:
        identifier = extension["id"]
        ids = AFFORDABILITY_SUBINDICATORS if identifier == "local_energy_affordability" else {identifier}
        matching = [
            row for row in rows
            if row["indicator_id"].strip() in ids and row["municipality"].strip() in expected
        ]
        counts: dict[str, int] = defaultdict(int)
        for row in matching:
            counts[row["status"].strip()] += 1
        extension_status.append({
            "id": identifier,
            "stage": extension["stage"],
            "blocking": bool(extension["blocking"]),
            "dependency": extension["dependency"],
            "rows_present": len(matching),
            "status_counts": dict(sorted(counts.items())),
        })

    return {
        "release": release["release"],
        "phase": phase,
        "ready": inputs_ready if phase == "inputs" else release_ready,
        "data_ready": data_ready,
        "methodology_approved": methodology_approved,
        "inputs_ready": inputs_ready,
        "artifacts_ready": artifacts_ready,
        "release_ready": release_ready,
        "municipalities": len(municipalities),
        "core_indicators": len(core),
        "core_checks_expected": len(municipalities) * len(core),
        "blockers": data_blockers,
        "review_blockers": review_blockers,
        "artifact_blockers": artifact_blockers,
        "extensions": extension_status,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline v0.1 readiness assessment")
    parser.add_argument("--phase", choices=("inputs", "release"), default="release")
    parser.add_argument("--report-only", action="store_true",
                        help="Report blockers without failing an otherwise healthy CI")
    parser.add_argument("--json-out", type=Path, help="Write a machine-readable report")
    args = parser.parse_args()
    result = evaluate(phase=args.phase)
    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    print(f"EPAH Diagnosis v{result['release']} — {args.phase} readiness")
    print(
        f"{result['municipalities']} municipalities x {result['core_indicators']} "
        f"core indicators = {result['core_checks_expected']} expected observations"
    )
    for key in ("data_ready", "methodology_approved", "inputs_ready", "artifacts_ready", "release_ready"):
        print(f"{key}: {result[key]}")
    for category in ("blockers", "review_blockers", "artifact_blockers"):
        value = result[category]
        if not value:
            continue
        for key, details in (value.items() if isinstance(value, dict) else [("artifacts", value)]):
            if details:
                print(f"- {category}/{key}: {len(details)} issue(s)")
    if not result["ready"] and not args.report_only:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
