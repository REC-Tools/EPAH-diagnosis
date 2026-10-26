from __future__ import annotations

import csv
import statistics
from pathlib import Path

from epah_diagnosis.geography import download_boundaries, parse_boundaries_zip
from epah_diagnosis.heating_facilities import (
    CPA_2011_URL,
    download_heating_facilities,
    filter_by_codes,
)


ROOT = Path(__file__).resolve().parents[1]
MUNICIPALITIES_FILE = ROOT / "data" / "municipalities.csv"
MATRIX_FILE = ROOT / "data" / "verification_matrix.csv"
OUTPUT_FILE = ROOT / "data" / "indicators" / "heating_facilities_gap_2011.csv"
SUMMARY_FILE = ROOT / "data" / "indicators" / "heating_facilities_gap_summary_2011.csv"

INDICATOR_ID = "heating_facilities_gap"
INDICATOR_NAME = "Abitazioni occupate senza impianto di riscaldamento"
SOURCE_PAGE = (
    "https://www.istat.it/notizia/basi-territoriali-e-variabili-censuarie/"
)


def read_target_municipalities() -> set[str]:
    with MUNICIPALITIES_FILE.open(encoding="utf-8", newline="") as handle:
        return {
            row["municipality"].strip()
            for row in csv.DictReader(handle)
            if row["municipality"].strip()
        }


def municipality_code_map(names: set[str]) -> dict[str, str]:
    boundaries = parse_boundaries_zip(download_boundaries(), names)
    return {
        feature["properties"]["municipality_code"]:
        feature["properties"]["municipality"]
        for feature in boundaries["features"]
    }


def main() -> None:
    targets = read_target_municipalities()

    print("Resolving official ISTAT municipality codes...")
    codes = municipality_code_map(targets)
    if len(codes) != 27:
        raise ValueError(
            f"Expected 27 target municipality codes, found {len(codes)}."
        )

    print("Downloading official ISTAT 2011 census-section variables...")
    records = filter_by_codes(download_heating_facilities(), set(codes))

    by_code = {record.municipality_code: record for record in records}

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "municipality",
                "occupied_dwellings",
                "occupied_dwellings_with_heating",
                "occupied_dwellings_without_heating",
                "heating_facilities_gap_pct",
                "reference_year",
                "source_url",
                "limitations",
            ],
        )
        writer.writeheader()

        for code, municipality in sorted(codes.items(), key=lambda item: item[1]):
            record = by_code[code]
            writer.writerow(
                {
                    "municipality": municipality,
                    "occupied_dwellings": record.occupied_dwellings,
                    "occupied_dwellings_with_heating": (
                        record.occupied_dwellings_with_heating
                    ),
                    "occupied_dwellings_without_heating": (
                        record.occupied_dwellings
                        - record.occupied_dwellings_with_heating
                    ),
                    "heating_facilities_gap_pct": f"{record.heating_gap_pct:.2f}",
                    "reference_year": "2011",
                    "source_url": CPA_2011_URL,
                    "limitations": (
                        "Census 2011 dwelling-level proxy. It measures presence "
                        "of a heating system, not whether households can afford "
                        "to use it or whether it is efficient or adequate."
                    ),
                }
            )

    values = [record.heating_gap_pct for record in records]
    with SUMMARY_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "territory",
                "municipality_count",
                "mean_municipal_pct",
                "median_municipal_pct",
                "min_municipal_pct",
                "max_municipal_pct",
                "method",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "territory": "Green Community Sinergie in Canavese",
                "municipality_count": len(records),
                "mean_municipal_pct": f"{statistics.mean(values):.2f}",
                "median_municipal_pct": f"{statistics.median(values):.2f}",
                "min_municipal_pct": f"{min(values):.2f}",
                "max_municipal_pct": f"{max(values):.2f}",
                "method": (
                    "100 * (A2 - A24) / A2, where A2 is occupied dwellings "
                    "with resident population and A24 is occupied dwellings "
                    "provided with a heating system."
                ),
            }
        )

    with MATRIX_FILE.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
        fieldnames = list(rows[0].keys())

    existing = {
        row["municipality"].casefold()
        for row in rows
        if row["indicator_id"] == INDICATOR_ID
    }

    for code, municipality in sorted(codes.items(), key=lambda item: item[1]):
        if municipality.casefold() in existing:
            continue

        record = by_code[code]
        rows.append(
            {
                "municipality": municipality,
                "indicator_id": INDICATOR_ID,
                "indicator_name": INDICATOR_NAME,
                "macro_area": "Facilities/Housing",
                "status": "Dato validato",
                "source_priority": "ISTAT",
                "year": "2011",
                "territorial_level": "Comune",
                "unit": "%",
                "source_url": SOURCE_PAGE,
                "value": f"{record.heating_gap_pct:.2f}",
                "quality": (
                    "Official ISTAT census variables A2 and A24 aggregated "
                    "from census sections to municipality."
                ),
                "limitations": (
                    "Old census reference year; presence of equipment does not "
                    "measure affordability, use, efficiency or thermal comfort."
                ),
                "notes": (
                    "EPAH-aligned inverse proxy of dwellings equipped with "
                    "heating facilities."
                ),
            }
        )

    with MATRIX_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print("Validated 27 municipal heating-facilities-gap records.")
    print(
        f"Mean municipal gap: {statistics.mean(values):.2f}%; "
        f"median: {statistics.median(values):.2f}%; "
        f"range: {min(values):.2f}-{max(values):.2f}%"
    )


if __name__ == "__main__":
    main()
