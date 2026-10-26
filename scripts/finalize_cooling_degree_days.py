from __future__ import annotations

import csv
import statistics
from pathlib import Path

from epah_diagnosis.cooling import compute_municipal_cdd_from_netcdf


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "raw" / "era5_land_daily_mean_temperature_2025.nc"
GEOJSON = ROOT / "data" / "geography" / "municipalities_2026.geojson"
MATRIX_FILE = ROOT / "data" / "verification_matrix.csv"
OUTPUT_FILE = ROOT / "data" / "indicators" / "cooling_degree_days_2025.csv"
SUMMARY_FILE = ROOT / "data" / "indicators" / "cooling_degree_days_summary_2025.csv"

INDICATOR_ID = "cooling_degree_days"
INDICATOR_NAME = "Cooling Degree Days"
SOURCE_PAGE = (
    "https://cds.climate.copernicus.eu/datasets/"
    "derived-era5-land-daily-statistics"
)
YEAR = 2025


def main() -> None:
    if not INPUT.exists():
        raise FileNotFoundError(
            f"Missing {INPUT}. Run "
            "python scripts/download_era5_land_daily_temperature.py first."
        )
    if not GEOJSON.exists():
        raise FileNotFoundError(
            f"Missing {GEOJSON}. Run acquire_municipality_boundaries.py first."
        )

    print("Calculating EPAH/Eurostat-style Cooling Degree Days...")
    results = compute_municipal_cdd_from_netcdf(INPUT, GEOJSON, YEAR)

    if len(results) != 27:
        raise ValueError(
            f"Expected 27 municipality CDD results, found {len(results)}."
        )

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "municipality",
                "cooling_degree_days",
                "era5_land_grid_cells",
                "reference_year",
                "method",
                "source_url",
                "limitations",
            ],
        )
        writer.writeheader()

        for result in results:
            writer.writerow(
                {
                    "municipality": result.municipality,
                    "cooling_degree_days": f"{result.cdd:.2f}",
                    "era5_land_grid_cells": result.grid_cells,
                    "reference_year": result.reference_year,
                    "method": (
                        "Eurostat/JRC CDD convention: daily contribution is "
                        "Tmean-21 C when Tmean >=24 C, otherwise 0."
                    ),
                    "source_url": SOURCE_PAGE,
                    "limitations": (
                        "ERA5-Land gridded climate indicator. Municipal value "
                        "is the mean of grid-cell daily temperatures whose "
                        "centres fall inside the ISTAT municipality polygon; "
                        "small municipalities use nearest-cell fallback. "
                        "It measures climate-driven cooling need, not household "
                        "affordability, building efficiency or actual cooling use."
                    ),
                }
            )

    values = [item.cdd for item in results]
    with SUMMARY_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "territory",
                "municipality_count",
                "mean_cdd",
                "median_cdd",
                "min_cdd",
                "max_cdd",
                "reference_year",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "territory": "Green Community Sinergie in Canavese",
                "municipality_count": len(results),
                "mean_cdd": f"{statistics.mean(values):.2f}",
                "median_cdd": f"{statistics.median(values):.2f}",
                "min_cdd": f"{min(values):.2f}",
                "max_cdd": f"{max(values):.2f}",
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
                "source_priority": "Copernicus C3S / ERA5-Land",
                "year": str(YEAR),
                "territorial_level": "Comune",
                "unit": "C degree-days",
                "source_url": SOURCE_PAGE,
                "value": f"{result.cdd:.2f}",
                "quality": (
                    f"Official ERA5-Land daily mean temperature; "
                    f"{result.grid_cells} grid cell(s) used."
                ),
                "limitations": (
                    "Climate-demand proxy only; does not measure actual cooling "
                    "equipment, electricity expenditure, thermal comfort or "
                    "ability to afford cooling."
                ),
                "notes": (
                    "EPAH/Eurostat-style CDD. Cross-read with 65+, building "
                    "efficiency and future summer thermal-comfort indicators."
                ),
            }
        )

    with MATRIX_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print("Validated 27 municipal Cooling Degree Days records.")
    print(
        f"Green Community 2025: mean {statistics.mean(values):.2f}, "
        f"median {statistics.median(values):.2f}, "
        f"range {min(values):.2f}-{max(values):.2f} C degree-days."
    )
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
