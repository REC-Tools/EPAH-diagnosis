from __future__ import annotations

import calendar
from pathlib import Path

from epah_diagnosis.cooling import bounding_box_from_geojson


ROOT = Path(__file__).resolve().parents[1]
GEOJSON = ROOT / "data" / "geography" / "municipalities_2026.geojson"
OUTPUT = ROOT / "data" / "raw" / "era5_land_daily_mean_temperature_2025.nc"

YEAR = 2025
DATASET = "derived-era5-land-daily-statistics"


def main() -> None:
    try:
        import cdsapi
    except ImportError as exc:
        raise RuntimeError(
            "cdsapi is required. Install project dependencies with: pip install -e ."
        ) from exc

    if not GEOJSON.exists():
        raise FileNotFoundError(
            f"Missing {GEOJSON}. Run acquire_municipality_boundaries.py first."
        )

    north, west, south, east = bounding_box_from_geojson(GEOJSON)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    days = [f"{day:02d}" for day in range(1, 32)]
    months = [f"{month:02d}" for month in range(1, 13)]

    request = {
        "variable": ["2m_temperature"],
        "year": str(YEAR),
        "month": months,
        "day": days,
        "daily_statistic": "daily_mean",
        "time_zone": "utc+01:00",
        "frequency": "1_hourly",
        "area": [
            round(north, 3),
            round(west, 3),
            round(south, 3),
            round(east, 3),
        ],
    }

    print("Downloading Copernicus ERA5-Land daily mean temperature for 2025...")
    print(
        "This requires a CDS account, accepted dataset terms, and a configured "
        "~/.cdsapirc personal access token."
    )

    client = cdsapi.Client()
    client.retrieve(DATASET, request, str(OUTPUT))

    print(f"Downloaded: {OUTPUT}")


if __name__ == "__main__":
    main()
