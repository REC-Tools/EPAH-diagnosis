from __future__ import annotations

import argparse
import csv
from pathlib import Path

from epah_diagnosis.http_download import validate_shapefile_zip

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
    parser = argparse.ArgumentParser(description="Acquire ISTAT 2026 municipal boundaries")
    parser.add_argument(
        "--source-zip", type=Path,
        help="Use a complete official ISTAT ZIP downloaded manually (offline fallback)",
    )
    args = parser.parse_args()
    municipalities = read_target_municipalities()

    if args.source_zip is not None:
        print(f"Reading local ISTAT boundaries archive: {args.source_zip}")
        payload = args.source_zip.read_bytes()
        validate_shapefile_zip(payload)
    else:
        print("Downloading official ISTAT 2026 generalized municipal boundaries...")
        payload = download_boundaries()

    # Parsing and canonical ISTAT municipality checks remain unchanged.
    geojson = parse_boundaries_zip(payload, municipalities)
    write_geojson(geojson, OUTPUT_FILE)

    print(f"Validated {len(geojson['features'])} municipality boundaries.")
    print(f"Source: {args.source_zip if args.source_zip else BOUNDARIES_2026_URL}")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
