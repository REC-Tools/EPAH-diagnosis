"""Prepare EPAH H03 estimated annual HDD from explicitly normalized ARPA NWIOI daily TX/TN.

Strict offline technical preview only. The source-to-municipality grid-cell mapping and
raw NetCDF decoding are NOT verified by this script; preserve originals for later audit.
Nothing here modifies canonical data, climate-zone GG, or v0.2 release artifacts.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import unicodedata
from calendar import isleap
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data/municipalities.csv"
STATUS = "technical_draft_do_not_publish"
SOURCE_ID = "F08"
INDICATOR_ID = "H03"
YEAR = 2025
ARPA_URL = "https://www.arpa.piemonte.it/scheda-informativa/dataset-griglia-nwioi"
TN_URL = "https://www.arpa.piemonte.it/static/data/NWIOItminDAY.nc"
TX_URL = "https://www.arpa.piemonte.it/static/data/NWIOItmaxDAY.nc"
TRIGGER_C = Decimal("15")
REFERENCE_C = Decimal("18")
REQUIRED = (
    "municipality_code", "municipality", "date", "grid_cell_id",
    "grid_latitude", "grid_longitude", "tmin_c", "tmax_c",
)
OUTPUT_HEADERS = (
    "municipality_code", "municipality", "reference_year", "hdd_eurostat_estimated_c_days",
    "temperature_days", "grid_cell_id", "grid_latitude", "grid_longitude",
    "temperature_mean_method", "source_id", "status",
)


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def normalize_name(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.casefold())
    return "".join(char for char in text if char.isalnum() and not unicodedata.combining(char))


def read_registry(path: Path) -> dict[str, str]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or not {"municipality", "istat_code"} <= set(reader.fieldnames):
            raise ValueError("Registry requires municipality and istat_code")
        entries: dict[str, str] = {}
        normalized_names: set[str] = set()
        for row in reader:
            code, name = (row.get("istat_code") or "").strip(), (row.get("municipality") or "").strip()
            if not re.fullmatch(r"\d{6}", code) or not name or code in entries:
                raise ValueError("Invalid/duplicate municipality ISTAT code")
            normal = normalize_name(name)
            if normal in normalized_names:
                raise ValueError("Duplicate municipality name")
            entries[code] = name
            normalized_names.add(normal)
    if len(entries) != 27:
        raise ValueError(f"Expected exactly 27 municipalities, found {len(entries)}")
    return entries


def parse_decimal(text: str, label: str) -> Decimal:
    # Reject comma decimal separators, NaN/inf, grouping and empty/suppressed cells.
    if not re.fullmatch(r"[+-]?(?:\d+(?:\.\d+)?|\.\d+)", text):
        raise ValueError(f"{label}: invalid decimal {text!r}")
    try:
        return Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"{label}: malformed decimal {text!r}") from exc


def hdd_day_from_minmax(tmin: Decimal, tmax: Decimal) -> Decimal:
    if not Decimal("-65") <= tmin <= tmax <= Decimal("65"):
        raise ValueError(f"Unphysical or inverted daily Tmin/Tmax: {tmin} / {tmax}")
    mean_estimate = (tmin + tmax) / 2
    # Eurostat convention: HDD = 18 - Tmean when Tmean <= 15; otherwise 0.
    return REFERENCE_C - mean_estimate if mean_estimate <= TRIGGER_C else Decimal(0)


def dates_in_year(year: int) -> list[str]:
    if not 1958 <= year <= 2100:
        raise ValueError("Reference year out of supported source period")
    start = date(year, 1, 1)
    return [(start + timedelta(days=n)).isoformat() for n in range(366 if isleap(year) else 365)]


def aggregate(path: Path, registry: dict[str, str], year: int = YEAR) -> tuple[list[dict[str, str]], dict[str, object]]:
    expected_dates = set(dates_in_year(year))
    daily: dict[str, dict[str, Decimal]] = defaultdict(dict)
    grid: dict[str, tuple[str, str, str]] = {}
    shared_cell: dict[tuple[str, str], tuple[Decimal, Decimal, str, str]] = {}
    count = 0
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        if len(fields) != len(set(fields)) or not set(REQUIRED) <= set(fields):
            raise ValueError(f"Daily normalized CSV requires unique headers {REQUIRED}")
        for rownum, row in enumerate(reader, 2):
            loc = f"row {rownum}"
            if None in row or any(row.get(field) is None for field in REQUIRED):
                raise ValueError(f"{loc}: malformed CSV")
            code, name = row["municipality_code"].strip(), row["municipality"].strip()
            if code not in registry or not re.fullmatch(r"\d{6}", code):
                raise ValueError(f"{loc}: unexpected municipality code {code!r}")
            if normalize_name(name) != normalize_name(registry[code]):
                raise ValueError(f"{loc}: municipality code/name mismatch for {code}")
            day = row["date"].strip()
            try:
                parsed = date.fromisoformat(day)
            except ValueError as exc:
                raise ValueError(f"{loc}: invalid ISO date {day!r}") from exc
            if day != parsed.isoformat() or day not in expected_dates:
                raise ValueError(f"{loc}: date outside full calendar year {year}: {day}")
            cell = row["grid_cell_id"].strip()
            if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,100}", cell):
                raise ValueError(f"{loc}: invalid grid_cell_id")
            lat = parse_decimal(row["grid_latitude"].strip(), f"{loc}/latitude")
            lon = parse_decimal(row["grid_longitude"].strip(), f"{loc}/longitude")
            if not Decimal("-90") <= lat <= Decimal("90") or not Decimal("-180") <= lon <= Decimal("180"):
                raise ValueError(f"{loc}: grid coordinates outside Earth range")
            # Piemonte study area, generous bounding box: not proof of correct spatial join.
            if not Decimal("43") <= lat <= Decimal("47.5") or not Decimal("6") <= lon <= Decimal("11"):
                raise ValueError(f"{loc}: grid cell outside Piemonte regional envelope")
            position = (cell, str(lat), str(lon))
            if code in grid and grid[code] != position:
                raise ValueError(f"{loc}: multiple grid cells for municipality {code}")
            grid[code] = position
            tmin = parse_decimal(row["tmin_c"].strip(), f"{loc}/tmin_c")
            tmax = parse_decimal(row["tmax_c"].strip(), f"{loc}/tmax_c")
            hdd = hdd_day_from_minmax(tmin, tmax)
            if day in daily[code]:
                raise ValueError(f"{loc}: duplicate municipality/date {code}/{day}")
            same_cell = (cell, day)
            observed = (tmin, tmax, str(lat), str(lon))
            if same_cell in shared_cell and shared_cell[same_cell] != observed:
                raise ValueError(f"{loc}: contradictory values/coordinates for shared grid cell {cell}/{day}")
            shared_cell[same_cell] = observed
            daily[code][day] = hdd
            count += 1
    if not count:
        raise ValueError("Empty normalized daily CSV")

    output: list[dict[str, str]] = []
    series_hdd = []
    for code, name in sorted(registry.items()):
        have = set(daily.get(code, {}))
        missing = expected_dates - have
        if missing:
            raise ValueError(f"{code}: missing {len(missing)} calendar dates (e.g. {sorted(missing)[:3]})")
        total = sum(daily[code].values(), Decimal(0))
        value = total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        series_hdd.append(total)
        cell, lat, lon = grid[code]
        output.append({
            "municipality_code": code,
            "municipality": name,
            "reference_year": str(year),
            "hdd_eurostat_estimated_c_days": f"{value:.2f}",
            "temperature_days": str(len(expected_dates)),
            "grid_cell_id": cell,
            "grid_latitude": lat,
            "grid_longitude": lon,
            "temperature_mean_method": "(tmin_c+tmax_c)/2_not_observed_daily_mean",
            "source_id": SOURCE_ID,
            "status": STATUS,
        })
    mean_unweighted = sum(series_hdd) / len(series_hdd)
    return output, {
        "coverage": "27/27", "municipality_count": len(output),
        "calendar_year": year, "days_required_per_municipality": len(expected_dates),
        "normalized_daily_rows": count,
        "unique_grid_cells": len({row["grid_cell_id"] for row in output}),
        "hdd_min_c_days": f"{min(series_hdd).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):.2f}",
        "hdd_max_c_days": f"{max(series_hdd).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):.2f}",
        "unweighted_municipal_mean_c_days": f"{mean_unweighted.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):.2f}",
        "method": "eurostat_hdd_trigger_15_reference_18_calendar_year",
        "temperature_mean_method": "(tmin_c+tmax_c)/2_not_observed_daily_mean",
        "spatial_support": "one_declared_NWIOI_grid_cell_per_municipality_not_area_average",
        "source_to_municipality_mapping_verified": False,
        "source_netcdf_extraction_verified": False,
    }


def write_outputs(out_dir: Path, rows: list[dict[str, str]], qa: dict[str, object],
                  normalized: Path, tmin_original: Path, tmax_original: Path, registry: Path) -> None:
    if out_dir.exists():
        raise FileExistsError(f"Output already exists: {out_dir}")
    out_dir.mkdir(parents=True)
    preview = out_dir / "hdd_eurostat_annual_preview.csv"
    with preview.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_HEADERS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    qa_file = out_dir / "qa.json"
    qa_file.write_text(json.dumps({
        "status": STATUS, "indicator_inventory_id": INDICATOR_ID, "source_inventory_id": SOURCE_ID,
        "reference_year": qa["calendar_year"],
        "formula": "daily: (tmin+tmax)/2 <= 15 ? 18-(tmin+tmax)/2 : 0; sum calendar year",
        "role": "climatic_heating_exposure_proxy_not_energy_poverty",
        "limitations": "NWIOI 0.125deg cell, Tmax/Tmin approximation; missing independent NetCDF-to-cell and municipality location verification; not DPR412 regulatory GG or ARPA rolling municipal estimates.",
        "qa": qa,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest = {
        "status": STATUS, "source_url": ARPA_URL, "source_tmin_url": TN_URL, "source_tmax_url": TX_URL,
        "source_license_reported": "CC-BY-2.5-IT; verify attribution at publication",
        "original_tmin_netcdf_sha256": digest(tmin_original),
        "original_tmax_netcdf_sha256": digest(tmax_original),
        "normalized_daily_csv_sha256": digest(normalized),
        "municipality_registry_sha256": digest(registry),
        "outputs_sha256": {p.name: digest(p) for p in (preview, qa_file)},
        "raw_netcdf_temporal_and_spatial_consistency_verified": False,
        "scientific_approval": False, "canonical_data_modified": False,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--normalized-daily-csv", type=Path, required=True)
    parser.add_argument("--original-tmin-netcdf", type=Path, required=True)
    parser.add_argument("--original-tmax-netcdf", type=Path, required=True)
    parser.add_argument("--registry", type=Path, default=REGISTRY)
    parser.add_argument("--reference-year", type=int, default=YEAR)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--expected-tmin-sha256", help="Optional independently verified original SHA-256")
    parser.add_argument("--expected-tmax-sha256", help="Optional independently verified original SHA-256")
    args = parser.parse_args(argv)
    if args.out_dir.exists():
        parser.error("Output already exists; choose a new review folder")
    sources = (args.normalized_daily_csv, args.original_tmin_netcdf, args.original_tmax_netcdf, args.registry)
    if not all(source.is_file() for source in sources):
        parser.error("Missing normalized daily CSV, original NetCDF(s), or registry")
    if len({path.resolve() for path in sources}) != len(sources):
        parser.error("CSV, registry and raw original files must be different")
    for label, path, expected in (
        ("Tmin", args.original_tmin_netcdf, args.expected_tmin_sha256),
        ("Tmax", args.original_tmax_netcdf, args.expected_tmax_sha256),
    ):
        if expected:
            if not re.fullmatch(r"[a-fA-F0-9]{64}", expected) or digest(path) != expected.lower():
                parser.error(f"{label} original SHA-256 invalid or mismatch")
    registry = read_registry(args.registry)
    values, qa = aggregate(args.normalized_daily_csv, registry, args.reference_year)
    write_outputs(args.out_dir, values, qa, args.normalized_daily_csv,
                  args.original_tmin_netcdf, args.original_tmax_netcdf, args.registry)
    print(f"H03: {len(values)} municipality technical estimates for {args.reference_year}")
    print("Status: technical_draft_do_not_publish; NetCDF decoding/spatial map unverified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
