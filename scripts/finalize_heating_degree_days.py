from __future__ import annotations

import csv
from pathlib import Path

from epah_diagnosis.climate import load_reference, summarize


ROOT = Path(__file__).resolve().parents[1]
REFERENCE_FILE = ROOT / "data" / "reference" / "climate_dpr412_green_community.csv"
MATRIX_FILE = ROOT / "data" / "verification_matrix.csv"
OUTPUT_FILE = ROOT / "data" / "indicators" / "heating_degree_days.csv"
BENCHMARK_FILE = ROOT / "data" / "indicators" / "heating_degree_days_summary.csv"

INDICATOR_ID = "heating_degree_days"
INDICATOR_NAME = "Gradi-giorno di riscaldamento"
SOURCE_URL = (
    "https://def.giustiziatributaria.gov.it/DocTribFrontend/"
    "getAttoNormativoDetail.do?ACTION=getArticolo&articolo=Allegato+A"
    "&codiceOrdinamento=60A+++++0000000"
    "&id=%7B0E4DC3BD-3B00-45E2-9CA6-B4DECB631C36%7D"
)


def main() -> None:
    records = load_reference(REFERENCE_FILE)
    summary = summarize(records)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "municipality",
                "climate_zone",
                "heating_degree_days",
                "municipal_seat_altitude_m",
                "source",
                "source_url",
                "quality",
                "limitations",
            ],
        )
        writer.writeheader()
        for record in sorted(records, key=lambda item: item.municipality):
            writer.writerow(
                {
                    "municipality": record.municipality,
                    "climate_zone": record.climate_zone,
                    "heating_degree_days": record.heating_degree_days,
                    "municipal_seat_altitude_m": record.municipal_seat_altitude_m,
                    "source": "DPR 412/1993 - Allegato A",
                    "source_url": SOURCE_URL,
                    "quality": (
                        "Classificazione normativa nazionale per Comune; "
                        "valore statico di riferimento."
                    ),
                    "limitations": (
                        "I gradi-giorno normativi sono un indicatore climatico "
                        "convenzionale e non rappresentano il consumo energetico "
                        "reale né la temperatura osservata nell'anno corrente."
                    ),
                }
            )

    with BENCHMARK_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "territory",
                "municipality_count",
                "zone_f_count",
                "zone_e_count",
                "mean_heating_degree_days",
                "median_heating_degree_days",
                "min_heating_degree_days",
                "max_heating_degree_days",
                "method",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "territory": "Green Community Sinergie in Canavese",
                **summary,
                "method": (
                    "Unweighted descriptive summary of municipal DPR 412/1993 "
                    "heating degree days; no population weighting."
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

    for record in records:
        key = record.municipality.casefold()
        if key in existing:
            continue
        rows.append(
            {
                "municipality": record.municipality,
                "indicator_id": INDICATOR_ID,
                "indicator_name": INDICATOR_NAME,
                "macro_area": "Climate",
                "status": "Dato validato",
                "source_priority": "DPR 412/1993 - Allegato A",
                "year": "normativo",
                "territorial_level": "Comune",
                "unit": "GG",
                "source_url": SOURCE_URL,
                "value": str(record.heating_degree_days),
                "quality": (
                    "Classificazione normativa nazionale per Comune; "
                    f"zona climatica {record.climate_zone}"
                ),
                "limitations": (
                    "Indicatore climatico convenzionale; non misura consumi "
                    "energetici reali o condizioni meteorologiche annuali"
                ),
                "notes": (
                    f"Zona climatica {record.climate_zone}; "
                    f"quota casa comunale {record.municipal_seat_altitude_m} m"
                ),
            }
        )

    with MATRIX_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print("Validated 27 municipal heating-degree-day records.")
    print(
        f"Zone F: {summary['zone_f_count']} / 27; "
        f"Zone E: {summary['zone_e_count']} / 27"
    )
    print(
        "Green Community heating degree days: "
        f"mean {summary['mean_heating_degree_days']:.2f}; "
        f"median {summary['median_heating_degree_days']:.2f}; "
        f"range {summary['min_heating_degree_days']}-"
        f"{summary['max_heating_degree_days']}"
    )


if __name__ == "__main__":
    main()
