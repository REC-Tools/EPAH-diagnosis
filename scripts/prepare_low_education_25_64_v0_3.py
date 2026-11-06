"""Create a technical-only EPAH H50 municipal education preview (ISTAT 2024).

Requires a normalized, complete age x qualification table plus an original export.
It does not assert that normalization from the ISTAT export has been reviewed.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data" / "municipalities.csv"
FLOW_ID = "DF_DCSS_ISTR_LAV_PEN_2_TV_1"
SOURCE_URL = (
    "https://esploradati.istat.it/databrowser/#/it/censpop/categories/"
    "CPA_POP/DCSS_ISTR_LAV_PEN_2_TV/IT1,DF_DCSS_ISTR_LAV_PEN_2_TV_1,1.0"
)
STATUS = "technical_draft_do_not_publish"
YEAR = "2024"
AGE_BANDS = tuple(f"{a}-{a + 4}" for a in range(25, 65, 5))
SINGLE_AGE_BAND = ("25-64",)
QUALIFICATIONS = (
    "none", "primary", "lower_secondary", "upper_or_tertiary", "unknown", "total"
)
DETAIL_CATEGORIES = QUALIFICATIONS[:-1]
REQUIRED = (
    "municipality_code", "municipality", "reference_year", "age_band",
    "sex", "education_group", "persons"
)
COLUMNS_OUT = (
    "municipality_code", "municipality", "reference_year",
    "residents_25_64_total", "residents_below_lower_secondary_25_64",
    "residents_with_unknown_education_25_64", "share_below_lower_secondary_25_64_pct",
    "source_flow", "status"
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def normalized_name(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.casefold())
    return "".join(c for c in s if c.isalnum() and not unicodedata.combining(c))


def read_registry(path: Path) -> dict[str, str]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or not {"istat_code", "municipality"} <= set(reader.fieldnames):
            raise ValueError("Registry requires istat_code and municipality")
        result: dict[str, str] = {}
        names: set[str] = set()
        for row in reader:
            code, name = (row["istat_code"] or "").strip(), (row["municipality"] or "").strip()
            if not re.fullmatch(r"\d{6}", code) or not name or code in result:
                raise ValueError("Duplicate/invalid registry ISTAT code or name")
            if normalized_name(name) in names:
                raise ValueError("Duplicate registry municipality name")
            result[code] = name
            names.add(normalized_name(name))
    if len(result) != 27:
        raise ValueError(f"Expected 27 municipalities, found {len(result)}")
    return result


def parse_nonnegative_int(s: str, location: str) -> int:
    if not re.fullmatch(r"\d+", s):
        raise ValueError(f"{location}: resident count must be a non-negative integer, not {s!r}")
    return int(s)


def aggregate(source_csv: Path, registry: dict[str, str]) -> tuple[list[dict[str, str]], dict[str, object]]:
    by_code: dict[str, dict[str, dict[str, int]]] = defaultdict(lambda: defaultdict(dict))
    with source_csv.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        headers = reader.fieldnames or []
        if len(headers) != len(set(headers)) or not set(REQUIRED) <= set(headers):
            raise ValueError(f"Normalized export needs unique columns {REQUIRED}")
        source_rows = 0
        for pos, row in enumerate(reader, 2):
            loc = f"row {pos}"
            if None in row or any(row.get(key) is None for key in REQUIRED):
                raise ValueError(f"{loc}: malformed CSV row")
            code = row["municipality_code"].strip()
            name = row["municipality"].strip()
            year = row["reference_year"].strip()
            sex = row["sex"].strip().casefold()
            age = row["age_band"].strip()
            grade = row["education_group"].strip()
            if code not in registry or not re.fullmatch(r"\d{6}", code):
                raise ValueError(f"{loc}: unexpected ISTAT code {code!r}")
            if normalized_name(name) != normalized_name(registry[code]):
                raise ValueError(f"{loc}: municipality mismatch for {code}")
            if year != YEAR:
                raise ValueError(f"{loc}: required census reference year {YEAR}, found {year}")
            if sex != "total":
                raise ValueError(f"{loc}: sex must be the population total (no male/female duplication)")
            if age not in AGE_BANDS + SINGLE_AGE_BAND:
                raise ValueError(f"{loc}: unsupported age band {age!r}; do not include minors")
            if grade not in QUALIFICATIONS:
                raise ValueError(f"{loc}: unknown education group {grade!r}; mapping must be explicit")
            n = parse_nonnegative_int(row["persons"].strip(), loc)
            if grade in by_code[code][age]:
                raise ValueError(f"{loc}: duplicate code/age/education record")
            by_code[code][age][grade] = n
            source_rows += 1
    if not source_rows:
        raise ValueError("Empty normalized export")

    result: list[dict[str, str]] = []
    groupings: set[str] = set()
    all_total = all_below = all_unknown = 0
    for code, name in sorted(registry.items()):
        ages = by_code.get(code, {})
        age_keys = set(ages)
        if age_keys == set(AGE_BANDS):
            grouping = "eight_5_year_age_bands"
        elif age_keys == set(SINGLE_AGE_BAND):
            grouping = "single_25_64_age_band"
        else:
            missing = sorted(set(AGE_BANDS) - age_keys)
            raise ValueError(f"{code}: incomplete or mixed 25-64 age bands, missing={missing}")
        groupings.add(grouping)
        denominator = low = unknown = 0
        for age, counts in sorted(ages.items()):
            if set(counts) != set(QUALIFICATIONS):
                raise ValueError(f"{code}/{age}: missing/extra education categories: "
                                 f"{sorted(set(QUALIFICATIONS) - set(counts))}")
            parts = sum(counts[q] for q in DETAIL_CATEGORIES)
            if parts != counts["total"]:
                raise ValueError(f"{code}/{age}: total category does not equal sum of exclusive levels")
            denominator += counts["total"]
            low += counts["none"] + counts["primary"]
            unknown += counts["unknown"]
        if not denominator:
            raise ValueError(f"{code}: zero denominator; do not impute")
        all_total += denominator
        all_below += low
        all_unknown += unknown
        result.append({
            "municipality_code": code,
            "municipality": name,
            "reference_year": YEAR,
            "residents_25_64_total": str(denominator),
            "residents_below_lower_secondary_25_64": str(low),
            "residents_with_unknown_education_25_64": str(unknown),
            "share_below_lower_secondary_25_64_pct": f"{100 * low / denominator:.2f}",
            "source_flow": FLOW_ID,
            "status": STATUS,
        })
    if len(groupings) != 1:
        raise ValueError("Inconsistent age aggregation across municipalities")
    return result, {
        "municipality_count": len(result), "coverage": "27/27",
        "age_band_mode": next(iter(groupings)),
        "normalized_source_rows": source_rows,
        "residents_25_64_total": all_total,
        "residents_below_lower_secondary_25_64": all_below,
        "residents_with_unknown_education_25_64": all_unknown,
        "green_community_weighted_share_pct": f"{100 * all_below / all_total:.2f}",
        "unknown_education_share_pct": f"{100 * all_unknown / all_total:.2f}",
    }


def write_preview(output: Path, values: list[dict[str, str]], qa: dict[str, object],
                  source: Path, original: Path, registry: Path) -> None:
    if output.exists():
        raise FileExistsError(f"Preserve previous review files; choose a new --out-dir: {output}")
    output.mkdir(parents=True)
    csv_out = output / "low_education_25_64_preview.csv"
    with csv_out.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=COLUMNS_OUT, lineterminator="\n")
        writer.writeheader()
        writer.writerows(values)
    qa_out = output / "qa.json"
    qa_out.write_text(json.dumps({
        "status": STATUS,
        "epah_inventory_id": "H50",
        "candidate_indicator_id": "low_education_below_lower_secondary_25_64",
        "reference_date": "2024-12-31",
        "source": FLOW_ID,
        "formula": "100*(no_qualification+primary)/all_residents_25_to_64",
        "education_groups_counted_in_numerator": ["none", "primary"],
        "education_groups_not_in_numerator": ["lower_secondary", "upper_or_tertiary", "unknown"],
        "denominator_includes_unknown_education": True,
        "note": "Proxy territorial; normalized ISTAT category mapping and real source review pending. Not household energy poverty.",
        "qa": qa,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest = {
        "status": STATUS,
        "census_source_url": SOURCE_URL,
        "source_flow_id": FLOW_ID,
        "original_export_sha256": sha256(original),
        "normalized_source_csv_sha256": sha256(source),
        "municipality_registry_sha256": sha256(registry),
        "outputs_sha256": {p.name: sha256(p) for p in (csv_out, qa_out)},
        "normalized_export_mapping_verified": False,
        "scientific_approval": False,
        "canonical_data_modified": False,
    }
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--normalized-csv", type=Path, required=True,
                        help="Explicitly normalized 2024 municipal age×education CSV")
    parser.add_argument("--original-export", type=Path, required=True,
                        help="Unmodified IstatData export retained for subsequent comparison")
    parser.add_argument("--registry", type=Path, default=REGISTRY)
    parser.add_argument("--out-dir", type=Path, required=True,
                        help="Fresh outputs/quality review directory; never overwrite")
    parser.add_argument("--expected-original-sha256", type=str,
                        help="Independent SHA-256 checksum of original source export, if available")
    args = parser.parse_args(argv)
    if args.out_dir.exists():
        parser.error("Output directory exists; choose a new review folder")
    if not args.original_export.is_file() or not args.normalized_csv.is_file():
        parser.error("Normalized CSV and original ISTAT export must be present")
    if args.expected_original_sha256:
        expected = args.expected_original_sha256.lower()
        if not re.fullmatch(r"[a-f0-9]{64}", expected):
            parser.error("Invalid expected original SHA-256")
        if sha256(args.original_export) != expected:
            parser.error("Original export SHA-256 mismatch")
    registry = read_registry(args.registry)
    values, qa = aggregate(args.normalized_csv, registry)
    write_preview(args.out_dir, values, qa, args.normalized_csv, args.original_export, args.registry)
    print(f"H50: {len(values)} municipal previews; weighted share {qa['green_community_weighted_share_pct']}%")
    print("Status: technical_draft_do_not_publish; normalization mapping requires review")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
