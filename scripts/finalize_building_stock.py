from __future__ import annotations

import argparse
import csv
from pathlib import Path

from epah_diagnosis.istat_building_stock import (
    HISTORIC_CODE,
    PIEMONTE_CSV_URL,
    POOR_CONDITION_CODE,
    download_regional_csv,
    filter_municipalities,
    read_regional_file,
)


ROOT = Path(__file__).resolve().parents[1]
MUNICIPALITIES_FILE = ROOT / "data" / "municipalities.csv"
MATRIX_FILE = ROOT / "data" / "verification_matrix.csv"
OUTPUT_FILE = ROOT / "data" / "indicators" / "building_stock_2011.csv"
BENCHMARK_FILE = ROOT / "data" / "indicators" / "building_stock_benchmarks_2011.csv"

SOURCE_PAGE = "https://ottomilacensus.istat.it/download-dati/"
YEAR = "2011"
INDICATOR_ID = "old_building_stock"


def read_target_municipalities() -> set[str]:
    with MUNICIPALITIES_FILE.open(encoding="utf-8", newline="") as handle:
        return {
            row["municipality"].strip()
            for row in csv.DictReader(handle)
            if row["municipality"].strip()
        }


def mean(values: list[float]) -> float:
    if not values:
        raise ValueError("Cannot calculate an empty mean.")
    return round(sum(values) / len(values), 2)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        type=Path,
        help="Optional manually downloaded Piemonte 8milaCensus CSV.",
    )
    args = parser.parse_args()

    target_names = read_target_municipalities()

    if args.input:
        print(f"Using local ISTAT file: {args.input}")
        all_piemonte = read_regional_file(args.input)
    else:
        print("Downloading official ISTAT 8milaCensus Piemonte CSV...")
        all_piemonte = download_regional_csv()

    records = filter_municipalities(all_piemonte, target_names)

    gc_historic_mean = mean([r.historic_occupied_dwellings_pct for r in records])
    gc_poor_mean = mean([r.poor_condition_buildings_pct for r in records])

    piemonte_historic_mean = mean(
        [r.historic_occupied_dwellings_pct for r in all_piemonte]
    )
    piemonte_poor_mean = mean(
        [r.poor_condition_buildings_pct for r in all_piemonte]
    )

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", encoding="utf-8", newline="") as handle:
        fields = [
            "municipality_code",
            "municipality",
            "year",
            "historic_occupied_dwellings_pct",
            "poor_condition_buildings_pct",
            "green_community_historic_mean_pct",
            "piemonte_historic_mean_pct",
            "green_community_poor_condition_mean_pct",
            "piemonte_poor_condition_mean_pct",
            "source",
            "source_url",
            "quality",
            "limitations",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for record in sorted(records, key=lambda x: x.municipality):
            writer.writerow(
                {
                    "municipality_code": record.municipality_code,
                    "municipality": record.municipality,
                    "year": YEAR,
                    "historic_occupied_dwellings_pct": f"{record.historic_occupied_dwellings_pct:.2f}",
                    "poor_condition_buildings_pct": f"{record.poor_condition_buildings_pct:.2f}",
                    "green_community_historic_mean_pct": f"{gc_historic_mean:.2f}",
                    "piemonte_historic_mean_pct": f"{piemonte_historic_mean:.2f}",
                    "green_community_poor_condition_mean_pct": f"{gc_poor_mean:.2f}",
                    "piemonte_poor_condition_mean_pct": f"{piemonte_poor_mean:.2f}",
                    "source": "ISTAT 8milaCensus - indicatori comunali ai confini 2011",
                    "source_url": PIEMONTE_CSV_URL,
                    "quality": "Fonte ufficiale ISTAT; CSV regionale; dettaglio comunale Censimento 2011.",
                    "limitations": (
                        "Dato 2011; A10 e A9 sono proxy del rischio di inefficienza "
                        "energetica e non equivalgono alla classe energetica."
                    ),
                }
            )

    with BENCHMARK_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "territory",
                "year",
                "historic_occupied_dwellings_pct",
                "poor_condition_buildings_pct",
                "method",
                "source_url",
            ],
        )
        writer.writeheader()
        writer.writerows(
            [
                {
                    "territory": "Green Community Sinergie in Canavese",
                    "year": YEAR,
                    "historic_occupied_dwellings_pct": f"{gc_historic_mean:.2f}",
                    "poor_condition_buildings_pct": f"{gc_poor_mean:.2f}",
                    "method": "Media semplice dei 27 valori comunali.",
                    "source_url": SOURCE_PAGE,
                },
                {
                    "territory": "Piemonte",
                    "year": YEAR,
                    "historic_occupied_dwellings_pct": f"{piemonte_historic_mean:.2f}",
                    "poor_condition_buildings_pct": f"{piemonte_poor_mean:.2f}",
                    "method": "Media semplice dei Comuni piemontesi nel CSV 8milaCensus.",
                    "source_url": SOURCE_PAGE,
                },
            ]
        )

    with MATRIX_FILE.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
        fieldnames = list(rows[0].keys())

    by_name = {r.municipality.casefold(): r for r in records}
    updated = 0
    for row in rows:
        if row["indicator_id"] != INDICATOR_ID:
            continue

        record = by_name.get(row["municipality"].casefold())
        if record is None:
            raise ValueError(f"Missing building stock result for {row['municipality']}")

        row["status"] = "Dato validato"
        row["year"] = YEAR
        row["territorial_level"] = "Comune"
        row["unit"] = "%"
        row["source_url"] = SOURCE_PAGE
        row["value"] = f"{record.historic_occupied_dwellings_pct:.2f}"
        row["quality"] = "Fonte ufficiale ISTAT 8milaCensus; CSV regionale 2011"
        row["limitations"] = (
            "Baseline 2011; A10 misura abitazioni occupate pre-1919, non prestazione energetica"
        )
        row["notes"] = (
            f"{HISTORIC_CODE} abitazioni storiche: "
            f"{record.historic_occupied_dwellings_pct:.2f}%; "
            f"{POOR_CONDITION_CODE} edifici in pessimo stato: "
            f"{record.poor_condition_buildings_pct:.2f}%"
        )
        updated += 1

    if updated != 27:
        raise ValueError(f"Expected to update 27 building-stock rows, updated {updated}")

    with MATRIX_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print("Validated 27 municipal building-stock checks.")
    print(f"Green Community A10 historic occupied dwellings: {gc_historic_mean:.2f}%")
    print(f"Piemonte A10 municipal mean: {piemonte_historic_mean:.2f}%")
    print(f"Green Community A9 poor-condition buildings: {gc_poor_mean:.2f}%")
    print(f"Piemonte A9 municipal mean: {piemonte_poor_mean:.2f}%")


if __name__ == "__main__":
    main()
