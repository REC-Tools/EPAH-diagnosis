from __future__ import annotations

import csv
import statistics
from pathlib import Path

from epah_diagnosis.altitude import (
    ALTITUDE_XLSX_URL,
    download_altitude,
    filter_municipalities,
)


ROOT = Path(__file__).resolve().parents[1]
MUNICIPALITIES_FILE = ROOT / "data" / "municipalities.csv"
MATRIX_FILE = ROOT / "data" / "verification_matrix.csv"
OUTPUT_FILE = ROOT / "data" / "indicators" / "mean_altitude_2021.csv"
SUMMARY_FILE = ROOT / "data" / "indicators" / "mean_altitude_summary_2021.csv"

INDICATOR_ID = "mean_altitude"
INDICATOR_NAME = "Altitudine media comunale"
SOURCE_PAGE = "https://www.istat.it/classificazione/principali-statistiche-geografiche-sui-comuni/"


def read_target_municipalities() -> set[str]:
    with MUNICIPALITIES_FILE.open(encoding="utf-8", newline="") as handle:
        return {
            row["municipality"].strip()
            for row in csv.DictReader(handle)
            if row["municipality"].strip()
        }


def main() -> None:
    targets = read_target_municipalities()

    print("Downloading official ISTAT municipal altitude indicators...")
    records = filter_municipalities(download_altitude(), targets)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "municipality",
                "mean_altitude_m",
                "min_altitude_m",
                "max_altitude_m",
                "reference_geography",
                "source",
                "source_url",
                "limitations",
            ],
        )
        writer.writeheader()
        for record in sorted(records, key=lambda item: item.municipality):
            writer.writerow(
                {
                    "municipality": record.municipality,
                    "mean_altitude_m": f"{record.mean_altitude_m:.2f}",
                    "min_altitude_m": (
                        "" if record.min_altitude_m is None
                        else f"{record.min_altitude_m:.2f}"
                    ),
                    "max_altitude_m": (
                        "" if record.max_altitude_m is None
                        else f"{record.max_altitude_m:.2f}"
                    ),
                    "reference_geography": "Comuni al 31 dicembre 2021",
                    "source": "ISTAT - Indicatori relativi all'altimetria dei Comuni",
                    "source_url": ALTITUDE_XLSX_URL,
                    "limitations": (
                        "Indicatore morfologico territoriale; non misura direttamente "
                        "accessibilità, isolamento sociale o povertà energetica."
                    ),
                }
            )

    values = [record.mean_altitude_m for record in records]
    with SUMMARY_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "territory",
                "municipality_count",
                "mean_of_municipal_mean_altitude_m",
                "median_municipal_mean_altitude_m",
                "min_municipal_mean_altitude_m",
                "max_municipal_mean_altitude_m",
                "method",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "territory": "Green Community Sinergie in Canavese",
                "municipality_count": len(records),
                "mean_of_municipal_mean_altitude_m": f"{statistics.mean(values):.2f}",
                "median_municipal_mean_altitude_m": f"{statistics.median(values):.2f}",
                "min_municipal_mean_altitude_m": f"{min(values):.2f}",
                "max_municipal_mean_altitude_m": f"{max(values):.2f}",
                "method": (
                    "Descriptive unweighted summary of ISTAT municipal mean altitude."
                ),
            }
        )

    by_name = {record.municipality.casefold(): record for record in records}

    with MATRIX_FILE.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
        fieldnames = list(rows[0].keys())

    existing = {
        row["municipality"].casefold()
        for row in rows
        if row["indicator_id"] == INDICATOR_ID
    }

    for municipality in sorted(targets):
        key = municipality.casefold()
        if key in existing:
            continue
        record = by_name.get(key)
        if record is None:
            raise ValueError(f"Missing altitude result for {municipality}")

        rows.append(
            {
                "municipality": municipality,
                "indicator_id": INDICATOR_ID,
                "indicator_name": INDICATOR_NAME,
                "macro_area": "Territory/Mobility",
                "status": "Dato validato",
                "source_priority": "ISTAT",
                "year": "2021",
                "territorial_level": "Comune",
                "unit": "m s.l.m.",
                "source_url": SOURCE_PAGE,
                "value": f"{record.mean_altitude_m:.2f}",
                "quality": (
                    "Fonte ufficiale ISTAT; indicatore altimetrico comunale "
                    "derivato da NASADEM e Basi Territoriali 2021"
                ),
                "limitations": (
                    "Proxy morfologico; non misura da solo tempi di accesso "
                    "ai servizi o disponibilità di trasporto"
                ),
                "notes": "Altitudine media del territorio comunale",
            }
        )

    with MATRIX_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print("Validated 27 municipal mean-altitude records.")
    print(
        "Green Community municipal mean altitude: "
        f"mean {statistics.mean(values):.2f} m; "
        f"median {statistics.median(values):.2f} m"
    )


if __name__ == "__main__":
    main()
