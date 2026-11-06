"""Technical H04 estimated CDD using the same checked daily NWIOI input as H03.

The H03 validator is reused for 27 x calendar coverage, shared cells, coordinates,
Tmin/Tmax physical checks and provenance. H04 is NOT outdoor thermal comfort or
measured electricity consumption. No canonical records are updated.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
H03_PATH = ROOT / "scripts/prepare_hdd_eurostat_2025_v0_3.py"
spec = importlib.util.spec_from_file_location("epah_h03_daily_validator", H03_PATH)
assert spec and spec.loader
h03 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h03)

STATUS = "technical_draft_do_not_publish"
TRIGGER_C = Decimal("24")
REFERENCE_C = Decimal("21")
HEADERS = ("municipality_code", "municipality", "reference_year",
           "cdd_eurostat_estimated_c_days", "temperature_days", "grid_cell_id",
           "grid_latitude", "grid_longitude", "status")


def cdd_day_from_minmax(tmin: Decimal, tmax: Decimal) -> Decimal:
    if not Decimal("-65") <= tmin <= tmax <= Decimal("65"):
        raise ValueError("Unphysical or inverted daily temperatures")
    mean = (tmin + tmax) / Decimal(2)
    # Eurostat: CDD = Tmean - 21 if Tmean >= 24 C, otherwise 0.
    return mean - REFERENCE_C if mean >= TRIGGER_C else Decimal(0)


def aggregate(path: Path, registry: dict[str, str], year: int = 2025):
    # Do not bypass the existing strict H03 validator: it also enforces one
    # consistent source grid cell per municipality and shared-cell consistency.
    h03_output, h03_qa = h03.aggregate(path, registry, year)
    daily_cdd = defaultdict(Decimal)
    with path.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            code = row["municipality_code"].strip()
            if code not in registry:
                raise ValueError(f"Unexpected municipality: {code}")
            low = h03.parse_decimal(row["tmin_c"].strip(), "tmin_c")
            high = h03.parse_decimal(row["tmax_c"].strip(), "tmax_c")
            daily_cdd[code] += cdd_day_from_minmax(low, high)
    values = []
    for row in h03_output:
        code = row["municipality_code"]
        values.append({
            "municipality_code": code,
            "municipality": row["municipality"],
            "reference_year": str(year),
            "cdd_eurostat_estimated_c_days": f"{daily_cdd[code]:.2f}",
            "temperature_days": row["temperature_days"],
            "grid_cell_id": row["grid_cell_id"],
            "grid_latitude": row["grid_latitude"],
            "grid_longitude": row["grid_longitude"],
            "status": STATUS,
        })
    return values, {
        "coverage": "27/27",
        "reference_year": year,
        "temperature_days_per_municipality": len(h03.dates_in_year(year)),
        "daily_input_qa": h03_qa,
        "unweighted_municipal_mean_c_days": f"{sum(daily_cdd.values(), Decimal(0)) / len(values):.2f}",
        "source_to_municipality_mapping_verified": False,
        "source_netcdf_extraction_verified": False,
        "note": "Tmean is estimated as (Tmin+Tmax)/2. This is not an areal or population-weighted municipality temperature.",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--normalized-daily-csv", type=Path, required=True)
    parser.add_argument("--original-tmin-netcdf", type=Path, required=True)
    parser.add_argument("--original-tmax-netcdf", type=Path, required=True)
    parser.add_argument("--registry", type=Path, default=h03.REGISTRY)
    parser.add_argument("--reference-year", type=int, default=2025)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.out_dir.exists():
        parser.error("Output directory already exists; preserve QA")
    for p in (args.normalized_daily_csv, args.original_tmin_netcdf, args.original_tmax_netcdf):
        if not p.is_file():
            parser.error(f"Required original/normalized input missing: {p}")
    registry = h03.read_registry(args.registry)
    values, qa = aggregate(args.normalized_daily_csv, registry, args.reference_year)
    args.out_dir.mkdir(parents=True)
    output = args.out_dir / "cdd_eurostat_annual_preview.csv"
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=HEADERS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(values)
    qa_path = args.out_dir / "qa.json"
    qa_path.write_text(json.dumps({
        "status": STATUS,
        "epah_inventory_id": "H04",
        "source_inventory_id": "F08",
        "formula": "Tmean=(Tmin+Tmax)/2; if Tmean>=24: CDD_day=Tmean-21; else: 0",
        "qa": qa,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest = {
        "status": STATUS, "indicator_id": "H04", "source_id": "F08",
        "original_tmin_netcdf_sha256": h03.digest(args.original_tmin_netcdf),
        "original_tmax_netcdf_sha256": h03.digest(args.original_tmax_netcdf),
        "normalized_daily_csv_sha256": h03.digest(args.normalized_daily_csv),
        "municipality_registry_sha256": h03.digest(args.registry),
        "outputs_sha256": {p.name: h03.digest(p) for p in (output, qa_path)},
        "source_to_municipality_mapping_verified": False,
        "scientific_approval": False, "canonical_data_modified": False,
    }
    (args.out_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("H04: 27 technical municipal CDD previews; do not publish")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
