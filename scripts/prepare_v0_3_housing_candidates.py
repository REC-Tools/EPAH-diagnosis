"""Strict technical previews for v0.3 H05 and non-resident-occupied dwelling context.

Inputs MUST be explicitly normalized from an archived primary export. No attempt
is made to infer residential status from an all-uses APE aggregate or to infer
vacancy/second homes from the census category 'not occupied by residents'.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import unicodedata
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data/municipalities.csv"
STATUS = "technical_draft_do_not_publish"
SOURCES = {
    "h05_ape_fg": {
        "scope": "valid_residential_ape",
        "groups": ("A4", "A3", "A2", "A1", "B", "C", "D", "E", "F", "G", "total"),
        "numerator": ("F", "G"),
        "source": "Piemonte SICEE / ENEA SIAPE, residential subset to be demonstrated",
        "unit": "valid residential EPC certificates",
    },
    "dwellings_not_occupied_by_residents": {
        "scope": "all_census_dwellings",
        "groups": ("occupied_by_residents", "not_occupied_by_residents", "total"),
        "numerator": ("not_occupied_by_residents",),
        "source": "ISTAT Census 2023 section variables, mapping to be demonstrated",
        "unit": "dwellings",
    },
}
FIELDS = ("municipality_code", "municipality", "reference_date", "data_scope", "group", "count")
OUT = ("municipality_code", "municipality", "reference_date", "indicator_id", "numerator",
       "denominator", "value_pct", "numerator_unit", "source", "status")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canon(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.casefold())
    return "".join(c for c in s if c.isalnum() and not unicodedata.combining(c))


def read_registry(path: Path) -> dict[str, str]:
    result = {}
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or not {"municipality", "istat_code"} <= set(reader.fieldnames):
            raise ValueError("Registry requires municipality and istat_code")
        for r in reader:
            code, name = r["istat_code"].strip(), r["municipality"].strip()
            if not re.fullmatch(r"\d{6}", code) or not name or code in result:
                raise ValueError("Invalid/duplicate registry entry")
            result[code] = name
    if len(result) != 27:
        raise ValueError("Exactly 27 registered municipalities required")
    return result


def aggregate(path: Path, registry: dict[str, str], indicator: str):
    spec = SOURCES[indicator]
    rows: dict[str, dict[str, int]] = {}
    reference_dates: set[str] = set()
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)) or not set(FIELDS) <= set(reader.fieldnames):
            raise ValueError(f"Normalized CSV must have unique columns: {FIELDS}")
        for n, row in enumerate(reader, 2):
            if None in row or any(row.get(f) is None for f in FIELDS):
                raise ValueError(f"row {n}: malformed CSV")
            code, name = row["municipality_code"].strip(), row["municipality"].strip()
            if code not in registry or canon(name) != canon(registry[code]):
                raise ValueError(f"row {n}: municipality code/name mismatch")
            if row["data_scope"].strip() != spec["scope"]:
                raise ValueError(f"row {n}: wrong scope; do not mix all-use and residential APE")
            d = row["reference_date"].strip()
            try:
                parsed = date.fromisoformat(d)
            except ValueError as e:
                raise ValueError(f"row {n}: invalid reference date") from e
            if parsed.isoformat() != d:
                raise ValueError(f"row {n}: noncanonical reference date")
            if indicator == "dwellings_not_occupied_by_residents" and d != "2023-12-31":
                raise ValueError("Census candidate requires 2023-12-31")
            reference_dates.add(d)
            group = row["group"].strip()
            if group not in spec["groups"]:
                raise ValueError(f"row {n}: unknown group {group}")
            raw = row["count"].strip()
            if not re.fullmatch(r"\d+", raw):
                raise ValueError(f"row {n}: count must be an integer >= 0")
            bucket = rows.setdefault(code, {})
            if group in bucket:
                raise ValueError(f"row {n}: duplicate municipality/group")
            bucket[group] = int(raw)
    if len(reference_dates) != 1:
        raise ValueError("Exactly one reference date required")
    output = []
    total_num = total_den = 0
    for code, name in sorted(registry.items()):
        groups = rows.get(code, {})
        if set(groups) != set(spec["groups"]):
            raise ValueError(f"{code}: incomplete categories")
        denominator = groups["total"]
        if denominator <= 0 or denominator != sum(v for k, v in groups.items() if k != "total"):
            raise ValueError(f"{code}: zero or unreconciled denominator")
        numerator = sum(groups[k] for k in spec["numerator"])
        total_num += numerator
        total_den += denominator
        output.append({
            "municipality_code": code, "municipality": name,
            "reference_date": next(iter(reference_dates)), "indicator_id": indicator,
            "numerator": str(numerator), "denominator": str(denominator),
            "value_pct": f"{100 * numerator / denominator:.2f}",
            "numerator_unit": spec["unit"], "source": spec["source"], "status": STATUS,
        })
    return output, {
        "indicator_id": indicator, "coverage": "27/27", "reference_date": next(iter(reference_dates)),
        "source_mapping_verified": False, "residential_filter_verified": False if indicator == "h05_ape_fg" else None,
        "total_numerator": total_num, "total_denominator": total_den,
        "weighted_share_pct": f"{100 * total_num / total_den:.2f}",
        "warning": "Technical arithmetic check only; raw-to-normalized category mapping requires independent review.",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--indicator", choices=sorted(SOURCES), required=True)
    parser.add_argument("--normalized-csv", type=Path, required=True)
    parser.add_argument("--original-export", type=Path, required=True)
    parser.add_argument("--registry", type=Path, default=REGISTRY)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--expected-original-sha256")
    args = parser.parse_args(argv)
    if args.out_dir.exists():
        parser.error("Review directory already exists; preserve historical QA")
    if not args.normalized_csv.is_file() or not args.original_export.is_file():
        parser.error("Original export and normalized CSV must exist")
    if args.expected_original_sha256:
        expected = args.expected_original_sha256.lower()
        if not re.fullmatch(r"[a-f0-9]{64}", expected) or sha256(args.original_export) != expected:
            parser.error("Original export SHA-256 mismatch")
    registry = read_registry(args.registry)
    values, qa = aggregate(args.normalized_csv, registry, args.indicator)
    args.out_dir.mkdir(parents=True)
    csv_path = args.out_dir / f"{args.indicator}_preview.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=OUT, lineterminator="\n")
        writer.writeheader()
        writer.writerows(values)
    qa_path = args.out_dir / "qa.json"
    qa_path.write_text(json.dumps({"status": STATUS, "qa": qa}, indent=2) + "\n", encoding="utf-8")
    manifest = {
        "status": STATUS, "indicator_id": args.indicator,
        "original_export_sha256": sha256(args.original_export),
        "normalized_csv_sha256": sha256(args.normalized_csv),
        "municipality_registry_sha256": sha256(args.registry),
        "outputs_sha256": {p.name: sha256(p) for p in (csv_path, qa_path)},
        "source_mapping_verified": False, "scientific_approval": False,
        "canonical_data_modified": False,
    }
    (args.out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"{args.indicator}: 27 technical previews; weighted share {qa['weighted_share_pct']}%; NOT APPROVED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
