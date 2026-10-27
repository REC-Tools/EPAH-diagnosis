from __future__ import annotations

import csv
import statistics
from pathlib import Path

from epah_diagnosis.heat_stress import compute_municipal_heat_stress_from_netcdf


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "raw" / "era5_heat_utci_2025.nc"
GEOJSON = ROOT / "data" / "geography" / "municipalities_2026.geojson"
MATRIX_FILE = ROOT / "data" / "verification_matrix.csv"
OUTPUT_FILE = ROOT / "data" / "indicators" / "heat_stress_days_2025.csv"
SUMMARY_FILE = ROOT / "data" / "indicators" / "heat_stress_days_summary_2025.csv"

INDICATOR_ID = "heat_stress_days"
INDICATOR_NAME = "Giorni con almeno strong heat stress"
SOURCE_PAGE = (
    "https://cds.climate.copernicus.eu/datasets/derived-utci-historical"
)
YEAR = 2025


def main() -> None:
    if not INPUT.exists():
        raise FileNotFoundError(
            f"Missing {INPUT}. Run "
            "python scripts/download_era5_heat_utci.py first."
        )
    if not GEOJSON.exists():
        raise FileNotFoundError(
            f"Missing {GEOJSON}. Run acquire_municipality_boundaries.py first."
        )

    print("Calculating EPAH/Copernicus heat-stress days from daily maximum UTCI...")
    results = compute_municipal_heat_stress_from_netcdf(INPUT, GEOJSON, YEAR)

    if len(results) != 27:
        raise ValueError(
            f"Expected 27 municipality heat-stress results, found {len(results)}."
        )

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "municipality",
                "strong_heat_stress_days_utci_ge_32",
                "very_strong_heat_stress_days_utci_ge_38",
                "extreme_heat_stress_days_utci_gt_46",
                "maximum_daily_utci_c",
                "era5_heat_grid_cells",
                "reference_year",
                "source_url",
                "limitations",
            ],
        )
        writer.writeheader()

        for result in results:
            writer.writerow(
                {
                    "municipality": result.municipality,
                    "strong_heat_stress_days_utci_ge_32": result.strong_days,
                    "very_strong_heat_stress_days_utci_ge_38": (
                        result.very_strong_days
                    ),
                    "extreme_heat_stress_days_utci_gt_46": result.extreme_days,
                    "maximum_daily_utci_c": f"{result.max_utci_c:.2f}",
                    "era5_heat_grid_cells": result.grid_cells,
                    "reference_year": result.reference_year,
                    "source_url": SOURCE_PAGE,
                    "limitations": (
                        "Outdoor gridded thermal-stress indicator based on UTCI. "
                        "It does not represent indoor temperature, cooling access, "
                        "health outcome or affordability. Municipal aggregation "
                        "uses grid-cell centres inside ISTAT polygons, with "
                        "nearest-cell fallback for small municipalities."
                    ),
                }
            )

    strong_values = [item.strong_days for item in results]
    very_values = [item.very_strong_days for item in results]
    extreme_values = [item.extreme_days for item in results]

    with SUMMARY_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "territory",
                "municipality_count",
                "mean_strong_days",
                "median_strong_days",
                "max_strong_days",
                "mean_very_strong_days",
                "max_very_strong_days",
                "mean_extreme_days",
                "max_extreme_days",
                "reference_year",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "territory": "Green Community Sinergie in Canavese",
                "municipality_count": len(results),
                "mean_strong_days": f"{statistics.mean(strong_values):.2f}",
                "median_strong_days": f"{statistics.median(strong_values):.2f}",
                "max_strong_days": max(strong_values),
                "mean_very_strong_days": f"{statistics.mean(very_values):.2f}",
                "max_very_strong_days": max(very_values),
                "mean_extreme_days": f"{statistics.mean(extreme_values):.2f}",
                "max_extreme_days": max(extreme_values),
                "reference_year": YEAR,
            }
        )

    with MATRIX_FILE.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
        fieldnames = list(rows[0].keys())

    existing = {
        (row["municipality"].casefold(), row["indicator_id"])
        for row in rows
    }

    for result in results:
        key = (result.municipality.casefold(), INDICATOR_ID)
        if key in existing:
            continue

        rows.append(
            {
                "municipality": result.municipality,
                "indicator_id": INDICATOR_ID,
                "indicator_name": INDICATOR_NAME,
                "macro_area": "Climate",
                "status": "Dato validato",
                "source_priority": "Copernicus C3S / ERA5-HEAT",
                "year": str(YEAR),
                "territorial_level": "Comune",
                "unit": "days",
                "source_url": SOURCE_PAGE,
                "value": str(result.strong_days),
                "quality": (
                    "Official ERA5-HEAT UTCI; main indicator counts days whose "
                    "daily maximum UTCI reaches at least 32 C."
                ),
                "limitations": (
                    "Outdoor climate exposure only; does not measure indoor "
                    "thermal comfort, cooling equipment, affordability or "
                    "health impacts."
                ),
                "notes": (
                    f"Very strong >=38 C: {result.very_strong_days} days; "
                    f"extreme >46 C: {result.extreme_days} days; "
                    f"maximum daily UTCI {result.max_utci_c:.2f} C."
                ),
            }
        )

    with MATRIX_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print("Validated 27 municipal heat-stress records.")
    print(
        f"Strong heat stress: mean {statistics.mean(strong_values):.2f} days, "
        f"median {statistics.median(strong_values):.2f}, "
        f"maximum {max(strong_values)} days."
    )
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
