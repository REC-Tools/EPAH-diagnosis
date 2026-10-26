from __future__ import annotations

import csv
from pathlib import Path

from epah_diagnosis.istat_building_stock import (
    HISTORIC_LABEL,
    POOR_CONDITION_LABEL,
    download_building_stock,
    municipality_url,
)
from epah_diagnosis.istat_posas import download_posas, filter_municipalities


ROOT = Path(__file__).resolve().parents[1]
MUNICIPALITIES_FILE = ROOT / "data" / "municipalities.csv"
MATRIX_FILE = ROOT / "data" / "verification_matrix.csv"
OUTPUT_FILE = ROOT / "data" / "indicators" / "building_stock_2011.csv"
BENCHMARK_FILE = ROOT / "data" / "indicators" / "building_stock_benchmarks_2011.csv"

SOURCE_PAGE = "https://ottomilacensus.istat.it/"
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


def consistent_benchmark(values: list[float | None], name: str) -> float:
    available = [round(value, 2) for value in values if value is not None]
    if not available:
        raise ValueError(f"No {name} benchmark found in ISTAT pages.")
    unique = sorted(set(available))
    if len(unique) != 1:
        raise ValueError(f"Inconsistent {name} benchmark values: {unique}")
    return unique[0]


def main() -> None:
    target_names = read_target_municipalities()

    # Reuse official POSAS data only to obtain current six-digit ISTAT codes.
    posas = download_posas()
    selected_posas = filter_municipalities(posas, target_names)

    records = []
    for index, item in enumerate(sorted(selected_posas, key=lambda x: x.municipality), start=1):
        print(f"[{index:02d}/27] ISTAT 8milaCensus: {item.municipality}")
        records.append(
            download_building_stock(item.municipality_code, item.municipality)
        )

    if len(records) != 27:
        raise ValueError(f"Expected 27 municipalities, found {len(records)}")

    gc_historic_mean = mean([r.historic_occupied_dwellings_pct for r in records])
    gc_poor_mean = mean([r.poor_condition_buildings_pct for r in records])

    piemonte_historic = consistent_benchmark(
        [r.region_historic_pct for r in records], "Piemonte historic"
    )
    italy_historic = consistent_benchmark(
        [r.italy_historic_pct for r in records], "Italy historic"
    )
    piemonte_poor = consistent_benchmark(
        [r.region_poor_condition_pct for r in records], "Piemonte poor condition"
    )
    italy_poor = consistent_benchmark(
        [r.italy_poor_condition_pct for r in records], "Italy poor condition"
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
            "piemonte_historic_pct",
            "italy_historic_pct",
            "green_community_poor_condition_mean_pct",
            "piemonte_poor_condition_pct",
            "italy_poor_condition_pct",
            "source",
            "source_url",
            "quality",
            "limitations",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for record in records:
            writer.writerow(
                {
                    "municipality_code": record.municipality_code,
                    "municipality": record.municipality,
                    "year": YEAR,
                    "historic_occupied_dwellings_pct": f"{record.historic_occupied_dwellings_pct:.2f}",
                    "poor_condition_buildings_pct": f"{record.poor_condition_buildings_pct:.2f}",
                    "green_community_historic_mean_pct": f"{gc_historic_mean:.2f}",
                    "piemonte_historic_pct": f"{piemonte_historic:.2f}",
                    "italy_historic_pct": f"{italy_historic:.2f}",
                    "green_community_poor_condition_mean_pct": f"{gc_poor_mean:.2f}",
                    "piemonte_poor_condition_pct": f"{piemonte_poor:.2f}",
                    "italy_poor_condition_pct": f"{italy_poor:.2f}",
                    "source": "ISTAT 8milaCensus - Censimento 2011",
                    "source_url": municipality_url(record.municipality_code),
                    "quality": "Fonte ufficiale ISTAT; dettaglio comunale; Censimento 2011.",
                    "limitations": (
                        "Dato non recente. La vetustà e lo stato di conservazione sono proxy "
                        "del rischio di inefficienza energetica e non equivalgono alla classe energetica."
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
                "source",
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
                    "method": "Media semplice dei 27 valori comunali; denominatori assoluti non disponibili nella fonte 8milaCensus.",
                    "source": "ISTAT 8milaCensus",
                },
                {
                    "territory": "Piemonte",
                    "year": YEAR,
                    "historic_occupied_dwellings_pct": f"{piemonte_historic:.2f}",
                    "poor_condition_buildings_pct": f"{piemonte_poor:.2f}",
                    "method": "Benchmark territoriale pubblicato da ISTAT 8milaCensus.",
                    "source": "ISTAT 8milaCensus",
                },
                {
                    "territory": "Italia",
                    "year": YEAR,
                    "historic_occupied_dwellings_pct": f"{italy_historic:.2f}",
                    "poor_condition_buildings_pct": f"{italy_poor:.2f}",
                    "method": "Benchmark territoriale pubblicato da ISTAT 8milaCensus.",
                    "source": "ISTAT 8milaCensus",
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
        row["source_url"] = municipality_url(record.municipality_code)
        row["value"] = f"{record.historic_occupied_dwellings_pct:.2f}"
        row["quality"] = "Fonte ufficiale ISTAT 8milaCensus; dettaglio comunale Censimento 2011"
        row["limitations"] = (
            "Baseline 2011; misura abitazioni occupate pre-1919, non prestazione energetica"
        )
        row["notes"] = (
            f"{HISTORIC_LABEL}: {record.historic_occupied_dwellings_pct:.2f}%; "
            f"{POOR_CONDITION_LABEL}: {record.poor_condition_buildings_pct:.2f}%"
        )
        updated += 1

    if updated != 27:
        raise ValueError(f"Expected to update 27 building-stock rows, updated {updated}")

    with MATRIX_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print("Validated 27 municipal building-stock checks.")
    print(f"Green Community historic occupied dwellings (municipal mean): {gc_historic_mean:.2f}%")
    print(f"Piemonte historic occupied dwellings: {piemonte_historic:.2f}%")
    print(f"Italia historic occupied dwellings: {italy_historic:.2f}%")
    print(f"Green Community poor-condition buildings (municipal mean): {gc_poor_mean:.2f}%")
    print(f"Piemonte poor-condition buildings: {piemonte_poor:.2f}%")
    print(f"Italia poor-condition buildings: {italy_poor:.2f}%")


if __name__ == "__main__":
    main()
