from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path
from epah_diagnosis.matrix_update import upsert_indicator_rows

from epah_diagnosis.snai import (
    SNAI_2020_URL,
    download_snai,
    filter_municipalities,
    normalize_text,
)


ROOT = Path(__file__).resolve().parents[1]
MUNICIPALITIES_FILE = ROOT / "data" / "municipalities.csv"
MATRIX_FILE = ROOT / "data" / "verification_matrix.csv"
OUTPUT_FILE = ROOT / "data" / "indicators" / "snai_classification_2020.csv"
SUMMARY_FILE = ROOT / "data" / "indicators" / "snai_classification_summary_2020.csv"

INDICATOR_ID = "snai_classification"
INDICATOR_NAME = "Classificazione SNAI di perifericita"
SOURCE_PAGE = (
    "https://politichecoesione.governo.it/it/politica-di-coesione/"
    "strategie-tematiche-e-territoriali/strategie-territoriali/"
    "strategia-nazionale-aree-interne-snai/le-aree-interne-2021-2027/"
    "mappa-aree-interne-2020/"
)


def read_target_municipalities() -> set[str]:
    with MUNICIPALITIES_FILE.open(encoding="utf-8", newline="") as handle:
        return {
            row["municipality"].strip()
            for row in csv.DictReader(handle)
            if row["municipality"].strip()
        }


def main() -> None:
    targets = read_target_municipalities()

    print("Downloading official SNAI 2020 municipality classification...")
    records = filter_municipalities(download_snai(), targets)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "municipality",
                "snai_class",
                "snai_label",
                "reference_year",
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
                    "snai_class": record.snai_class,
                    "snai_label": record.snai_label,
                    "reference_year": "2020",
                    "source": "Mappa Aree Interne 2020 - SNAI",
                    "source_url": SNAI_2020_URL,
                    "limitations": (
                        "Classificazione di policy basata su accessibilita ai poli "
                        "di servizi con dati di offerta aggiornati a fine 2019; "
                        "non sostituisce i tempi correnti verso singoli servizi."
                    ),
                }
            )

    counts = Counter(record.snai_class for record in records)
    with SUMMARY_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "territory",
                "class_A",
                "class_B",
                "class_C",
                "class_D",
                "class_E",
                "class_F",
                "inner_area_municipalities_D_E_F",
                "method",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "territory": "Green Community Sinergie in Canavese",
                "class_A": counts.get("A", 0),
                "class_B": counts.get("B", 0),
                "class_C": counts.get("C", 0),
                "class_D": counts.get("D", 0),
                "class_E": counts.get("E", 0),
                "class_F": counts.get("F", 0),
                "inner_area_municipalities_D_E_F": sum(
                    counts.get(letter, 0) for letter in ("D", "E", "F")
                ),
                "method": (
                    "Official SNAI 2020 municipality classification; "
                    "D/E/F are Inner Areas."
                ),
            }
        )

    by_name = {normalize_text(record.municipality): record for record in records}

    with MATRIX_FILE.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    original_count = len(rows)


    for municipality in sorted(targets):
        key = normalize_text(municipality)

        record = by_name.get(key)
        if record is None:
            raise ValueError(f"Missing SNAI result for {municipality}")

        rows.append(
            {
                "municipality": municipality,
                "indicator_id": INDICATOR_ID,
                "indicator_name": INDICATOR_NAME,
                "macro_area": "Territory/Mobility",
                "status": "Dato validato",
                "source_priority": "SNAI / ISTAT / DPCoe",
                "year": "2020",
                "territorial_level": "Comune",
                "unit": "classe A-F",
                "source_url": SOURCE_PAGE,
                "value": record.snai_class,
                "quality": (
                    "Classificazione ufficiale Aree Interne 2020; "
                    "accessibilita congiunta a salute, istruzione e mobilita"
                ),
                "limitations": (
                    "Dati di localizzazione dei servizi aggiornati a fine 2019; "
                    "indicatore sintetico di policy, non tempo corrente a singolo servizio"
                ),
                "notes": record.snai_label,
            }
        )

    upsert_indicator_rows(MATRIX_FILE, INDICATOR_ID, rows[original_count:])

    inner = sum(counts.get(letter, 0) for letter in ("D", "E", "F"))
    print("Validated 27 municipal SNAI classification records.")
    print(f"Inner Areas (D/E/F): {inner} / 27")
    print(
        "Class distribution: "
        + ", ".join(f"{letter}={counts.get(letter, 0)}" for letter in "ABCDEF")
    )


if __name__ == "__main__":
    main()
