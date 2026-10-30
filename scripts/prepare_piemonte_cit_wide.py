"""Parse Regione Piemonte CIT's two verified *wide* CSV schemas.

Fuel: key_classe;gas_naturale;gasolio;gpl;...
Age: istat_comune;numero_fino_1950;...;numero_dal_2021

The source files must be supplied locally. Never infer a household denominator
or pretend that a 5-year installation bin is an exact installation date.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import unicodedata
from datetime import date
from collections import defaultdict
from pathlib import Path

from prepare_piemonte_cit import read_registry, sha256, SOURCE_FUEL, SOURCE_AGE

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data/municipalities.csv"
EXPECTED_SOURCE_HASHES = {
    "fuel": "7659242c31a4dd47d24e4d65b9075f90845a8f81829eff27cf485c24027793b4",
    "age": "4b506567cb3ea3aeb355eed021a30aa83f4c55d6729e9ae99bb825e71484712a",
}
FUEL_COLUMNS = (
    "gas_naturale", "gasolio", "gpl", "pellet_tronchetti_cippato",
    "olio_combustibile", "biomassa", "carbone", "policombustibile", "termica", "altro",
)
AGE_BINS = (
    ("numero_fino_1950", 1900, 1950),
    ("numero_1951_1960", 1951, 1960),
    ("numero_1961_1970", 1961, 1970),
    ("numero_1971_1980", 1971, 1980),
    ("numero_1981_1985", 1981, 1985),
    ("numero_1986_1990", 1986, 1990),
    ("numero_1991_1995", 1991, 1995),
    ("numero_1996_2000", 1996, 2000),
    ("numero_2001_2005", 2001, 2005),
    ("numero_2006_2010", 2006, 2010),
    ("numero_2011_2015", 2011, 2015),
    ("numero_2016_2020", 2016, 2020),
    ("numero_dal_2021", 2021, 3000),
)
AGE_COLUMNS = tuple(b[0] for b in AGE_BINS)
FUEL_HEADERS = ("key_classe", *FUEL_COLUMNS)
AGE_HEADERS = ("denominazione_provincia", "istat_comune", "denominazione_comune", *AGE_COLUMNS)


def normalize(value: str) -> str:
    text = unicodedata.normalize("NFKD", value).casefold()
    return re.sub(r"[^a-z0-9]", "", "".join(c for c in text if not unicodedata.combining(c)))


def load_csv(path: Path, required_fields: tuple[str, ...]) -> list[dict]:
    # The user verified both downloads are semicolon-delimited UTF-8 with BOM.
    with path.open(encoding="utf-8-sig", errors="strict", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        actual = tuple(reader.fieldnames or ())
        if actual != required_fields:
            raise ValueError(f"Unexpected CIT wide schema. Expected {required_fields}; got {actual}")
        rows = list(reader)
    if not rows:
        raise ValueError("Empty CIT source")
    if any(None in row for row in rows):
        raise ValueError("CIT CSV contains malformed extra columns")
    return rows


def count(value: str, *, label: str) -> int:
    s = str(value or "").strip()
    if not re.fullmatch(r"[0-9]+", s):
        raise ValueError(f"{label}: invalid/blank count {value!r}; unknown is not zero")
    return int(s)


def municipality_code(value: str, name_to_code: dict[str, str]) -> str | None:
    s = str(value or "").strip()
    if s.isdigit() and len(s) <= 6:
        return s.zfill(6)
    # Only exact, unique municipality names as an alternative; do not guess
    # compound or undocumented key_classe mappings.
    return name_to_code.get(normalize(s))


def inspect_selected_duplicates(
    raw_rows: list[dict], registry: dict[str, str], mode: str
) -> list[dict]:
    """Diagnose repeated municipality rows without assuming they are additive.

    Identical numeric vectors with consistent municipal identity are duplicate
    *measurements*, hence keep-once candidates. Any differing count or
    contradictory municipality name must block extraction. Always identify
    the original source line numbers for human-readable debugging.
    """
    if mode not in {"fuel", "age"}:
        raise ValueError("Expected fuel or age")
    by_name = {normalize(name): code for code, name in registry.items()}
    key_name = "key_classe" if mode == "fuel" else "istat_comune"
    count_fields = FUEL_COLUMNS if mode == "fuel" else AGE_COLUMNS
    matched: dict[str, list[tuple[int, dict, tuple[int, ...]]]] = defaultdict(list)
    for lineno, row in enumerate(raw_rows, 2):
        code = municipality_code(row[key_name], by_name)
        if code not in registry:
            continue
        # Validate counts in every matched record, including duplicates.
        vector = tuple(count(row[field], label=f"source row {lineno}/{field}")
                       for field in count_fields)
        matched[code].append((lineno, row, vector))
    duplicates = []
    for code, records in sorted(matched.items()):
        if len(records) < 2:
            continue
        difference_fields = [
            field for idx, field in enumerate(count_fields)
            if len({vector[idx] for _, _, vector in records}) != 1
        ]
        mismatched_names = []
        if mode == "age":
            for lineno, row, _ in records:
                observed = str(row["denominazione_comune"] or "").strip()
                if normalize(observed) != normalize(registry[code]):
                    mismatched_names.append({"line": lineno, "name": observed})
        status = (
            "conflicting_counts" if difference_fields else
            "conflicting_identity" if mismatched_names else "identical_counts"
        )
        duplicates.append({
            "istat_code": code,
            "municipality": registry[code],
            "status": status,
            "source_lines": [line for line, _, _ in records],
            "observed_keys": [str(row[key_name]).strip() for _, row, _ in records],
            "row_totals": [sum(vector) for _, _, vector in records],
            "differing_count_fields": difference_fields,
            "mismatched_municipality_names": mismatched_names,
            "source_records": [
                {
                    "line": lineno,
                    "observed_key": str(row[key_name]).strip(),
                    "observed_name": (
                        str(row["denominazione_comune"]).strip()
                        if mode == "age" else str(row[key_name]).strip()
                    ),
                    "province": (
                        str(row["denominazione_provincia"]).strip()
                        if mode == "age" else None
                    ),
                    "counts": {
                        field: value
                        for field, value in zip(count_fields, vector)
                    },
                    "row_total": sum(vector),
                }
                for lineno, row, vector in records
            ],
        })
    return duplicates


def extract_wide(path: Path, registry_path: Path, mode: str,
                 as_of: date, *,
                 quarantine_conflicts: bool = False) -> tuple[list[dict], dict]:
    if mode not in {"fuel", "age"}:
        raise ValueError("Expected fuel or age")
    if as_of.year < 2021 or as_of > date.today():
        raise ValueError("Analysis/reference date outside reasonable range")
    registry = read_registry(registry_path)
    by_name = {normalize(name): code for code, name in registry.items()}
    if len(by_name) != 27:
        raise ValueError("Ambiguous municipality names")
    raw_rows = load_csv(path, FUEL_HEADERS if mode == "fuel" else AGE_HEADERS)
    duplicate_rows = inspect_selected_duplicates(raw_rows, registry, mode)
    conflicts = [item for item in duplicate_rows if item["status"] != "identical_counts"]
    if conflicts and not quarantine_conflicts:
        raise ValueError(
            "Conflicting CIT rows for selected ISTAT municipality; cannot deduplicate "
            "or sum different observations. Run inspect_piemonte_cit.py to inspect "
            "the source lines and different fields: " +
            json.dumps(conflicts, ensure_ascii=False)
        )
    quarantined_codes = {item["istat_code"] for item in conflicts} if quarantine_conflicts else set()
    output = {}
    unmatched_samples = []
    for i, src in enumerate(raw_rows, 2):
        key = src["key_classe"] if mode == "fuel" else src["istat_comune"]
        code = municipality_code(key, by_name)
        if code is None:
            if len(unmatched_samples) < 8:
                unmatched_samples.append(str(key))
            continue
        if code not in registry or code in quarantined_codes:
            # Conflicting values are withheld, never selected or summed.
            continue
        if code in output:
            # Preflight proved that every selected duplicate has the same
            # complete numeric vector and consistent municipality identity.
            # Never count an identical snapshot twice.
            continue
        if mode == "fuel":
            quantities = {col: count(src[col], label=f"source row {i}/{col}")
                          for col in FUEL_COLUMNS}
            total = sum(quantities.values())
            classified = total  # all ten native source categories are retained
            solid = sum(quantities[x] for x in
                        ("pellet_tronchetti_cippato", "biomassa", "carbone"))
            other = sum(quantities[x] for x in
                        ("olio_combustibile", "policombustibile", "termica", "altro"))
            numerator = quantities["gasolio"] + quantities["gpl"]
            data = {
                "classified_groups": classified,
                "unclassified_groups": 0,
                "natural_gas_groups": quantities["gas_naturale"],
                "diesel_groups": quantities["gasolio"],
                "lpg_groups": quantities["gpl"],
                "solid_fuels_groups": solid,
                "electricity_groups": 0,  # NOT an enumerated source category
                "other_groups": other,
                "diesel_lpg_share_pct": f"{100 * numerator / classified:.2f}" if classified else "",
                "denominator": "classified_generator_groups",
            }
        else:
            quantities = {col: count(src[col], label=f"source row {i}/{col}")
                          for col in AGE_COLUMNS}
            threshold_year = as_of.year - 20
            guaranteed_old = 0
            uncertain = 0
            for col, first, last in AGE_BINS:
                quantity = quantities[col]
                if last < threshold_year:
                    guaranteed_old += quantity
                elif first <= threshold_year <= last:
                    uncertain += quantity
            classified = sum(quantities.values())
            data = {
                "groups_with_known_year": classified,
                "groups_with_unknown_year": 0,  # no unknown-year column in this source
                "groups_aged_20_or_more": guaranteed_old,  # conservative lower bound
                "groups_ambiguous_age": uncertain,
                "older_generator_share_pct": f"{100 * guaranteed_old / classified:.2f}" if classified else "",
                "older_upper_bound_share_pct": f"{100 * (guaranteed_old + uncertain) / classified:.2f}" if classified else "",
                "denominator": "generator_groups_with_known_installation_year",
                "age_metric": "conservative_lower_bound_for_20_years",
            }
        output[code] = {
            "municipality": registry[code], "istat_code": code,
            "generator_groups_total": total if mode == "fuel" else classified,
            **data, "snapshot_date": as_of.isoformat(),
        }
    missing = [{
        "istat_code": code,
        "municipality": registry[code],
        "reason": (
            "conflicting_source_rows_quarantined" if code in quarantined_codes
            else "not_found_or_unusable"
        ),
    } for code in registry if code not in output]
    zero = [{"istat_code": code, "municipality": output[code]["municipality"],
             "reason": "zero_denominator"}
            for code in output if output[code]["generator_groups_total"] == 0]
    missing.extend(zero)
    for code in registry:
        if code not in output:
            # No measured zero: all counts and shares are blank when data
            # are absent, including unresolved source duplicate conflicts.
            missing_fuel = {
                "classified_groups": "", "unclassified_groups": "",
                "natural_gas_groups": "", "diesel_groups": "", "lpg_groups": "",
                "solid_fuels_groups": "", "electricity_groups": "",
                "other_groups": "", "diesel_lpg_share_pct": "",
            }
            missing_age = {
                "groups_with_known_year": "", "groups_with_unknown_year": "",
                "groups_aged_20_or_more": "", "groups_ambiguous_age": "",
                "older_generator_share_pct": "", "older_upper_bound_share_pct": "",
                "age_metric": "conservative_lower_bound_for_20_years",
            }
            output[code] = {
                "municipality": registry[code], "istat_code": code,
                "generator_groups_total": "",
                "denominator": "classified_generator_groups" if mode == "fuel"
                               else "generator_groups_with_known_installation_year",
                "snapshot_date": as_of.isoformat(),
                **(missing_fuel if mode == "fuel" else missing_age),
            }
    for code, row in output.items():
        row["observation_status"] = (
            "source_conflict_quarantined" if code in quarantined_codes
            else "unavailable" if any(item["istat_code"] == code for item in missing)
            else "technical_observation"
        )
    results = [output[code] for code in sorted(registry, key=lambda c: registry[c])]
    snapshot_hash = sha256(path)
    qa = {
        "indicator_id": "cit_diesel_lpg_generator_share" if mode == "fuel"
                        else "cit_older_generator_share",
        "qa_status": "technical_incomplete_do_not_publish" if missing
                     else "technical_extraction_only",
        "validated_for_release": False,
        "source_url": SOURCE_FUEL if mode == "fuel" else SOURCE_AGE,
        "source_csv_sha256": snapshot_hash,
        "source_matches_user_inspection_hash": snapshot_hash == EXPECTED_SOURCE_HASHES[mode],
        "registry_csv_sha256": sha256(registry_path),
        "licence_catalogue": "CC BY 4.0 (verify downloaded resource)",
        "snapshot_date_operator_reported": as_of.isoformat(),
        "snapshot_date_semantics": "local_analysis_reference_date_not_verified_source_update_date",
        "source_schema": {
            "layout": "wide", "source_rows_parsed": len(raw_rows),
            "source_fields": list(FUEL_HEADERS if mode == "fuel" else AGE_HEADERS),
            "unmatched_key_samples": unmatched_samples,
            "duplicate_selected_rows": duplicate_rows,
            "quarantined_duplicate_conflicts": conflicts if quarantine_conflicts else [],
            "conflict_policy": (
                "quarantine_without_resolving" if quarantine_conflicts else
                "reject_all_conflicting_rows"
            ),
            "identical_source_rows_skipped": sum(
                len(item["source_lines"]) - 1 for item in duplicate_rows
            ),
            "duplicate_policy": "keep_once_only_when_all_counts_identical",
        },
        "municipalities_expected": 27,
        "municipalities_with_generator_data": 27 - len(missing),
        "quarantined_municipalities": sorted(quarantined_codes),
        "missing": missing, "unclassified_fuel_labels": {},
        "older_years_threshold": 20 if mode == "age" else None,
        "age_metric": "conservative_lower_bound_for_20_years" if mode == "age" else None,
        "age_interval_uncertainty_groups": (
            sum(r["groups_ambiguous_age"] for r in results) if mode == "age" else None),
        "meaning": ("gasolio + GPL / all recorded generator groups by fuel; not households"
                    if mode == "fuel" else
                    "certainly >=20 years / all dated generator groups, conservative minimum"),
        "limitations": [
            "Generator groups are neither buildings nor households.",
            "Source does not prove whether groups are currently operating.",
            "Local analysis date is not evidence of publication/update date.",
            "Installation years in 5-year bins prevent exact 20-year threshold.",
            "Fuel source lacks a dedicated electricity column; zero means NOT REPORTED in schema.",
        ],
    }
    return results, qa


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract 27-town CIT wide-format grouped sources")
    parser.add_argument("--mode", choices=("fuel", "age"), required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--registry", type=Path, default=REGISTRY)
    parser.add_argument("--as-of", type=date.fromisoformat, required=True,
                        help="Local analysis reference date YYYY-MM-DD; not official update timestamp")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument(
        "--quarantine-conflicts", action="store_true",
        help="Internal QA ONLY: exclude conflicted towns from measured values "
             "and write incomplete 27-row staging, never a release-ready dataset",
    )
    args = parser.parse_args()
    if args.quarantine_conflicts and args.strict:
        parser.error("--quarantine-conflicts and --strict cannot be combined: "
                     "quarantined data are not complete and cannot pass strict QA")
    if args.out_dir.exists():
        raise FileExistsError("Output exists. Choose a new directory to preserve provenance.")
    rows, qa = extract_wide(
        args.input, args.registry, args.mode, args.as_of,
        quarantine_conflicts=args.quarantine_conflicts,
    )
    if args.strict and (qa["missing"] or not qa["source_matches_user_inspection_hash"]):
        raise ValueError("Strict CIT source check failed. Details: " +
                         json.dumps({"missing": qa["missing"],
                                     "source_sha_match": qa["source_matches_user_inspection_hash"],
                                     "unmatched_examples": qa["source_schema"]["unmatched_key_samples"]},
                                    ensure_ascii=False))
    args.out_dir.mkdir(parents=True, exist_ok=False)
    csvfile = args.out_dir / (
        "cit_fuel_27.csv" if args.mode == "fuel" else "cit_generator_age_27.csv"
    )
    with csvfile.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    qa["output_csv_sha256"] = sha256(csvfile)
    (args.out_dir / "cit_qa.json").write_text(
        json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    if qa["quarantined_municipalities"]:
        evidence = {
            "status": "human_source_review_required",
            "mode": args.mode,
            "source_csv_sha256": qa["source_csv_sha256"],
            "quarantined_municipalities": qa["quarantined_municipalities"],
            "conflicts": qa["source_schema"]["quarantined_duplicate_conflicts"],
            "policy": "no_sum_no_selection_no_automatic_release",
        }
        (args.out_dir / "cit_conflicts_for_review.json").write_text(
            json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print("Quarantined conflicts:", qa["quarantined_municipalities"])
        print("CIT PREVIEW BLOCKED: no valid 27/27 map or PDF can be generated.")
    print(args.mode.upper(), qa["qa_status"],
          f"{qa['municipalities_with_generator_data']}/27",
          "verified source SHA:", qa["source_matches_user_inspection_hash"])
    if args.mode == "age":
        print("Age share is CONSERVATIVE LOWER BOUND; unresolved groups:",
              qa["age_interval_uncertainty_groups"])
    print("Output:", args.out_dir)


if __name__ == "__main__":
    main()
