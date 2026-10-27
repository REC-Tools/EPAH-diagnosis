from __future__ import annotations

from pathlib import Path

from epah_diagnosis.cooling import bounding_box_from_geojson


ROOT = Path(__file__).resolve().parents[1]
GEOJSON = ROOT / "data" / "geography" / "municipalities_2026.geojson"
OUTPUT = ROOT / "data" / "raw" / "era5_heat_utci_2025.nc"

YEAR = 2025
DATASET = "derived-utci-historical"


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

    north, west, south, east = bounding_box_from_geojson(GEOJSON, padding=0.3)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    request = {
        "variable": ["universal_thermal_climate_index"],
        "version": ["1_1"],
        "product_type": ["consolidated_dataset"],
        "year": [str(YEAR)],
        "month": [f"{month:02d}" for month in range(1, 13)],
        "day": [f"{day:02d}" for day in range(1, 32)],
        "area": [
            round(north, 3),
            round(west, 3),
            round(south, 3),
            round(east, 3),
        ],
        "data_format": "netcdf",
    }

    print("Downloading Copernicus ERA5-HEAT UTCI for 2025...")
    print(
        "This requires a CDS account, accepted dataset terms, and a configured "
        "~/.cdsapirc personal access token."
    )
    print(
        "If CDS rejects the request schema, open the dataset Download tab and "
        "compare the generated API request with this script; CDS occasionally "
        "changes catalogue parameter names."
    )

    client = cdsapi.Client()
    client.retrieve(DATASET, request, str(OUTPUT))

    print(f"Downloaded: {OUTPUT}")


if __name__ == "__main__":
    main()
