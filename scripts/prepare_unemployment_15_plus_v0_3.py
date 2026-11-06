"""Prepare technical-only EPAH H46 unemployment-rate candidates, census 2024.

Consumes an explicitly normalized municipal table and a separately preserved
original export. Does NOT assert the mapping of census categories is verified.
No writes to the canonical catalog, data matrix, or v0.1/v0.2 outputs.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import unicodedata
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data" / "municipalities.csv"
SOURCE_URL = "https://www.istat.it/statistiche-per-temi/censimenti/popolazione-e-abitazioni/risultati/"
SOURCE_ID = "F06"
STATUS = "technical_draft_do_not_publish"
YEAR = "2024"
AGE_UNIVERSE = "15_plus"
# ISTAT SDMX publishes estimated persons with decimal fractions. The tolerance
# absorbs representation noise only, not rounding of persons to integers.
RECONCILIATION_TOLERANCE = Decimal("0.000001")
RATE_PRECISION = Decimal("0.01")
CATEGORIES = (
    "employed", "unemployed", "inactive", "unknown", "labour_force", "population_total",
)
REQUIRED = (
    "municipality_code", "municipality", "reference_year", "age_universe",
    "sex", "labour_status", "persons",
)
OUTPUT = (
    "municipality_code", "municipality", "reference_year", "age_universe",
    "employed_15_plus", "unemployed_15_plus", "labour_force_15_plus",
    "inactive_15_plus", "unknown_labour_status_15_plus", "population_15_plus",
    "unemployment_rate_15_plus_pct", "source_id", "status",
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_name(s: str) -> str:
    normalized = unicodedata.normalize("NFKD", s.casefold())
    return "".join(c for c in normalized if c.isalnum() and not unicodedata.combining(c))


def read_registry(path: Path) -> dict[str, str]:
    names: set[str] = set()
    registry: dict[str, str] = {}
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        cols = reader.fieldnames or []
        if len(cols) != len(set(cols)) or not {"istat_code", "municipality"} <= set(cols):
            raise ValueError("Registry needs unique municipality and istat_code columns")
        for row in reader:
            if None in row:
                raise ValueError("Malformed municipality registry row")
            code = (row.get("istat_code") or "").strip()
            name = (row.get("municipality") or "").strip()
            standard = canonical_name(name)
            if not re.fullmatch(r"\d{6}", code) or not name or code in registry or standard in names:
                raise ValueError(f"Invalid/duplicate ISTAT municipality code/name: {code!r}/{name!r}")
            registry[code] = name
            names.add(standard)
    if len(registry) != 27:
        raise ValueError(f"Expected 27 municipalities in official registry, found {len(registry)}")
    return registry


def parse_count(value: str, location: str) -> Decimal:
    """Parse a non-negative, fixed-point estimate without floating-point loss."""
    if not re.fullmatch(r"\d+(?:\.\d+)?", value):
        raise ValueError(f"{location}: counts must be non-negative decimal numbers (dot separator); got {value!r}")
    return Decimal(value)


def aggregate(normalized_csv: Path, registry: dict[str, str]) -> tuple[list[dict[str, str]], dict[str, object]]:
    data: dict[str, dict[str, Decimal]] = {}
    rows_seen = 0
    with normalized_csv.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames or []
        if len(fields) != len(set(fields)) or not set(REQUIRED) <= set(fields):
            raise ValueError(f"Expected unique normalized CSV fields: {REQUIRED}")
        for number, row in enumerate(reader, 2):
            loc = f"row {number}"
            if None in row or any(row.get(col) is None for col in REQUIRED):
                raise ValueError(f"{loc}: malformed normalized CSV")
            code = row["municipality_code"].strip()
            name = row["municipality"].strip()
            if code not in registry or not re.fullmatch(r"\d{6}", code):
                raise ValueError(f"{loc}: unsupported ISTAT code {code!r}")
            if canonical_name(name) != canonical_name(registry[code]):
                raise ValueError(f"{loc}: municipality name does not match {code}")
            if row["reference_year"].strip() != YEAR:
                raise ValueError(f"{loc}: census reference year must be {YEAR}")
            if row["age_universe"].strip() != AGE_UNIVERSE:
                raise ValueError(f"{loc}: age universe must be exactly {AGE_UNIVERSE}")
            if row["sex"].strip() != "total":
                raise ValueError(f"{loc}: sex must be 'total', not separate sex rows")
            category = row["labour_status"].strip()
            if category not in CATEGORIES:
                raise ValueError(f"{loc}: unrecognized employment status {category!r}")
            n = parse_count(row["persons"].strip(), loc)
            values = data.setdefault(code, {})
            if category in values:
                raise ValueError(f"{loc}: duplicate municipality/status row {code}/{category}")
            values[category] = n
            rows_seen += 1
    if not rows_seen:
        raise ValueError("Empty normalized export")

    results: list[dict[str, str]] = []
    totals = {key: Decimal(0) for key in CATEGORIES}
    municipalities_zero_unemployed = 0
    maximum_force_residual = Decimal(0)
    maximum_population_residual = Decimal(0)
    for code, name in sorted(registry.items()):
        values = data.get(code)
        if values is None:
            raise ValueError(f"Missing municipality {code}/{name}")
        if set(values) != set(CATEGORIES):
            absent = sorted(set(CATEGORIES) - set(values))
            raise ValueError(f"{code}: missing labour-status categories: {absent}")
        force_residual = abs(values["employed"] + values["unemployed"] - values["labour_force"])
        population_residual = abs(
            values["labour_force"] + values["inactive"] + values["unknown"] - values["population_total"]
        )
        if force_residual > RECONCILIATION_TOLERANCE:
            raise ValueError(f"{code}: labour_force does not equal employed + unemployed within tolerance")
        if population_residual > RECONCILIATION_TOLERANCE:
            raise ValueError(f"{code}: population_total not reconciled to labour force + inactive + unknown within tolerance")
        maximum_force_residual = max(maximum_force_residual, force_residual)
        maximum_population_residual = max(maximum_population_residual, population_residual)
        if values["labour_force"] == 0:
            raise ValueError(f"{code}: zero labour-force denominator; cannot calculate rate")
        if values["unemployed"] == 0:
            municipalities_zero_unemployed += 1
        rate = Decimal(100) * values["unemployed"] / values["labour_force"]
        results.append({
            "municipality_code": code, "municipality": name,
            "reference_year": YEAR, "age_universe": AGE_UNIVERSE,
            "employed_15_plus": format(values["employed"], "f"),
            "unemployed_15_plus": format(values["unemployed"], "f"),
            "labour_force_15_plus": format(values["labour_force"], "f"),
            "inactive_15_plus": format(values["inactive"], "f"),
            "unknown_labour_status_15_plus": format(values["unknown"], "f"),
            "population_15_plus": format(values["population_total"], "f"),
            "unemployment_rate_15_plus_pct": format(rate.quantize(RATE_PRECISION, rounding=ROUND_HALF_UP), "f"),
            "source_id": SOURCE_ID, "status": STATUS,
        })
        for key in CATEGORIES:
            totals[key] += values[key]
    qa = {
        "municipality_count": len(results), "coverage": "27/27",
        "normalized_rows": rows_seen,
        "expected_rows": 27 * len(CATEGORIES),
        "age_universe": AGE_UNIVERSE,
        "reference_year": YEAR,
        "source_value_type": "non_negative_decimal_estimates",
        "reconciliation_tolerance_persons": format(RECONCILIATION_TOLERANCE, "f"),
        "max_labour_force_residual_persons": format(maximum_force_residual, "f"),
        "max_population_residual_persons": format(maximum_population_residual, "f"),
        # Strings preserve all source digits in JSON, avoiding float coercion.
        "sum_employed": format(totals["employed"], "f"),
        "sum_unemployed": format(totals["unemployed"], "f"),
        "sum_labour_force": format(totals["labour_force"], "f"),
        "sum_inactive": format(totals["inactive"], "f"),
        "sum_unknown": format(totals["unknown"], "f"),
        "sum_population_15_plus": format(totals["population_total"], "f"),
        "weighted_unemployment_rate_15_plus_pct": format(
            (Decimal(100) * totals["unemployed"] / totals["labour_force"]).quantize(
                RATE_PRECISION, rounding=ROUND_HALF_UP
            ), "f"
        ),
        "unknown_share_of_population_15_plus_pct": format(
            (Decimal(100) * totals["unknown"] / totals["population_total"]).quantize(
                RATE_PRECISION, rounding=ROUND_HALF_UP
            ), "f"
        ),
        "municipalities_with_zero_unemployed": municipalities_zero_unemployed,
    }
    return results, qa


def write_preview(out_dir: Path, results: list[dict[str, str]], qa: dict[str, object],
                  normalized_csv: Path, original_export: Path, registry: Path) -> None:
    if out_dir.exists():
        raise FileExistsError(f"QA preservation: output directory exists, choose a new --out-dir: {out_dir}")
    out_dir.mkdir(parents=True)
    values_file = out_dir / "unemployment_15_plus_preview.csv"
    with values_file.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=OUTPUT, lineterminator="\n")
        writer.writeheader()
        writer.writerows(results)
    qa_file = out_dir / "qa.json"
    qa_file.write_text(json.dumps({
        "status": STATUS,
        "epah_inventory_id": "H46",
        "candidate_indicator_id": "unemployment_rate_15_plus",
        "source_id": SOURCE_ID,
        "source_reference_url": SOURCE_URL,
        "reference_date": "2024-12-31",
        "formula": "100 * unemployed_15_plus / (employed_15_plus + unemployed_15_plus)",
        "inactives_excluded_from_denominator": True,
        "source_values_preserved_as_decimals": True,
        "normalized_status_mapping_verified": False,
        "note": "Socioeconomic vulnerability proxy, not observed household energy poverty; verify official ISTAT 2024 categories during final review.",
        "qa": qa,
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    manifest = {
        "status": STATUS,
        "original_source_url": SOURCE_URL,
        "source_id": SOURCE_ID,
        "original_export_sha256": sha256(original_export),
        "normalized_source_csv_sha256": sha256(normalized_csv),
        "municipality_registry_sha256": sha256(registry),
        "outputs_sha256": {p.name: sha256(p) for p in (values_file, qa_file)},
        "official_source_mapping_verified": False,
        "source_values_preserved_as_decimals": True,
        "scientific_approval": False,
        "canonical_data_modified": False,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--normalized-csv", type=Path, required=True,
                        help="2024 municipal, 15_plus, sex=total, complete and explicitly mapped")
    parser.add_argument("--original-export", type=Path, required=True,
                        help="Unmodified official ISTAT 2024 source export retained for provenance")
    parser.add_argument("--registry", type=Path, default=REGISTRY)
    parser.add_argument("--out-dir", type=Path, required=True,
                        help="New quality-review destination; cannot overwrite")
    parser.add_argument("--expected-original-sha256", type=str,
                        help="Independently recorded SHA-256 of official export")
    args = parser.parse_args(argv)
    if args.out_dir.exists():
        parser.error("Output directory already exists: never overwrite review files")
    if not args.normalized_csv.is_file() or not args.original_export.is_file():
        parser.error("Both normalized CSV and original export must exist")
    if args.expected_original_sha256:
        digest = args.expected_original_sha256.lower()
        if not re.fullmatch(r"[a-f0-9]{64}", digest):
            parser.error("Expected original SHA-256 must be 64 hex characters")
        if sha256(args.original_export) != digest:
            parser.error("Original export SHA-256 mismatch")
    registry = read_registry(args.registry)
    values, qa = aggregate(args.normalized_csv, registry)
    write_preview(args.out_dir, values, qa, args.normalized_csv, args.original_export, args.registry)
    print(f"H46: {len(values)} municipal previews; weighted unemployment {qa['weighted_unemployment_rate_15_plus_pct']}%")
    print("Status: technical_draft_do_not_publish; ISTAT official source mapping awaits final review")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
