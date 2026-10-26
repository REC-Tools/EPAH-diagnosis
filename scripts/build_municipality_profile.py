from __future__ import annotations

import csv
from pathlib import Path

from epah_diagnosis.municipality_profile import build_profiles


ROOT = Path(__file__).resolve().parents[1]
MATRIX_FILE = ROOT / "data" / "verification_matrix.csv"
OUTPUT_FILE = ROOT / "data" / "derived" / "municipality_profile.csv"


def main() -> None:
    with MATRIX_FILE.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    profiles = build_profiles(rows)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "municipality",
        "population_65_plus_pct",
        "population_65_plus_year",
        "income_vulnerability_pct",
        "income_vulnerability_year",
        "old_building_stock_pct",
        "old_building_stock_year",
    ]

    with OUTPUT_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(profiles)

    print(f"Built {len(profiles)} complete municipality profiles.")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
