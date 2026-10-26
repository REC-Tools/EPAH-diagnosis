from __future__ import annotations

import csv
from pathlib import Path

from epah_diagnosis.geography import (
    BOUNDARIES_2026_URL,
    download_boundaries,
    parse_boundaries_zip,
    write_geojson,
)


ROOT = Path(__file__).resolve().parents[1]
MUNICIPALITIES_FILE = ROOT / "data" / "municipalities.csv"
OUTPUT_FILE = ROOT / "data" / "geography" / "municipalities_2026.geojson"


def read_target_municipalities() -> set[str]:
    with MUNICIPALITIES_FILE.open(encoding="utf-8", newline="") as handle:
        return {
            row["municipality"].strip()
            for row in csv.DictReader(handle)
            if row["municipality"].strip()
        }


def main() -> None:
    municipalities = read_target_municipalities()

    print("Downloading official ISTAT 2026 generalized municipal boundaries...")
    payload = download_boundaries()
    geojson = parse_boundaries_zip(payload, municipalities)
    write_geojson(geojson, OUTPUT_FILE)

    print(f"Validated {len(geojson['features'])} municipality boundaries.")
    print(f"Source: {BOUNDARIES_2026_URL}")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
