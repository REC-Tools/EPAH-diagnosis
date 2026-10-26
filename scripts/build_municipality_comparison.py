from __future__ import annotations

import csv
from pathlib import Path

from epah_diagnosis.comparison import (
    NUMERIC_DIMENSIONS,
    build_comparison_rows,
    load_profiles,
)


ROOT = Path(__file__).resolve().parents[1]
PROFILE_FILE = ROOT / "data" / "derived" / "municipality_profile.csv"
OUTPUT_FILE = ROOT / "data" / "derived" / "municipality_comparison.csv"


def main() -> None:
    if not PROFILE_FILE.exists():
        raise FileNotFoundError(
            f"Missing {PROFILE_FILE}. Run build_municipality_profile.py first."
        )

    profiles = load_profiles(PROFILE_FILE)
    rows = build_comparison_rows(profiles)

    fieldnames = ["municipality", "snai_class"]
    for field, rank_field in NUMERIC_DIMENSIONS:
        fieldnames.extend([field, rank_field])

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Built comparative table for {len(rows)} municipalities.")
    print("Ranking convention: 1 = highest value for that dimension.")
    print("No overall composite score is calculated.")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
