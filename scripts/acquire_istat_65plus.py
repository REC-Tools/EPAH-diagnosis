from __future__ import annotations

import csv
from pathlib import Path

from epah_diagnosis.istat_posas import download_posas, filter_municipalities, write_indicator_csv


ROOT = Path(__file__).resolve().parents[1]
MUNICIPALITIES = ROOT / "data" / "municipalities.csv"
OUTPUT = ROOT / "data" / "indicators" / "population_65_plus_2026.csv"


def main() -> None:
    with MUNICIPALITIES.open(encoding="utf-8", newline="") as handle:
        names = {row["municipality"].strip() for row in csv.DictReader(handle)}

    data = download_posas()
    selected = filter_municipalities(data, names)
    write_indicator_csv(selected, OUTPUT, year=2026)

    print(f"Wrote {len(selected)} municipalities to {OUTPUT}")


if __name__ == "__main__":
    main()
