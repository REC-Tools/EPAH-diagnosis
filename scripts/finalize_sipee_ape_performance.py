from __future__ import annotations

import csv
from pathlib import Path

from epah_diagnosis.sipee_ape import (
    ENERGY_CLASSES,
    aggregate_by_municipality,
    read_csv_file,
)


ROOT = Path(__file__).resolve().parents[1]
INPUT_FILE = ROOT / "data" / "raw" / "sipee_ape_export.csv"
MUNICIPALITIES_FILE = ROOT / "data" / "municipalities.csv"
MATRIX_FILE = ROOT / "data" / "verification_matrix.csv"
OUTPUT_FILE = ROOT / "data" / "indicators" / "sipee_ape_performance.csv"

INDICATOR_ID = "poor_energy_label_share"
INDICATOR_NAME = "APE in classi energetiche E-F-G"
SOURCE_PAGE = (
    "https://servizi.regione.piemonte.it/catalogo/"
    "sistema-informativo-per-prestazione-energetica-degli-edifici-sipee"
)


def read_target_municipalities() -> set[str]:
    with MUNICIPALITIES_FILE.open(encoding="utf-8", newline="") as handle:
        return {
            row["municipality"].strip()
            for row in csv.DictReader(handle)
            if row["municipality"].strip()
        }


def main() -> None:
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Missing official SIPEE export: {INPUT_FILE}. "
            "Obtain an official PA extraction from Regione Piemonte/SIPEE and "
            "save it there as CSV before running this finalizer."
        )

    targets = read_target_municipalities()
    print("Reading official SIPEE APE export...")
    records = read_csv_file(INPUT_FILE)
    summaries = aggregate_by_municipality(records, targets)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "municipality",
        "total_apes",
        *[f"class_{cls}" for cls in ENERGY_CLASSES],
        "poor_class_apes_E_F_G",
        "poor_class_share_pct",
        "epgl_nren_median",
        "source_url",
        "limitations",
    ]

    with OUTPUT_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()

        for item in summaries:
            row = {
                "municipality": item.municipality,
                "total_apes": item.total_apes,
                "poor_class_apes_E_F_G": item.poor_class_apes,
                "poor_class_share_pct": f"{item.poor_class_share_pct:.2f}",
                "epgl_nren_median": (
                    "" if item.epgl_nren_median is None
                    else f"{item.epgl_nren_median:.2f}"
                ),
                "source_url": SOURCE_PAGE,
                "limitations": (
                    "APE records are not a census of the whole building stock; "
                    "coverage and selection vary by municipality and over time. "
                    "Use as certified-stock signal, not population prevalence."
                ),
            }
            for cls in ENERGY_CLASSES:
                row[f"class_{cls}"] = item.class_counts[cls]
            writer.writerow(row)

    with MATRIX_FILE.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
        fieldnames_matrix = list(rows[0].keys())

    existing = {
        (row["municipality"].casefold(), row["indicator_id"])
        for row in rows
    }

    for item in summaries:
        key = (item.municipality.casefold(), INDICATOR_ID)
        if key in existing:
            continue

        rows.append(
            {
                "municipality": item.municipality,
                "indicator_id": INDICATOR_ID,
                "indicator_name": INDICATOR_NAME,
                "macro_area": "Facilities/Housing",
                "status": "Dato validato",
                "source_priority": "Regione Piemonte / SIPEE",
                "year": "export date",
                "territorial_level": "Comune",
                "unit": "%",
                "source_url": SOURCE_PAGE,
                "value": f"{item.poor_class_share_pct:.2f}",
                "quality": (
                    f"Official SIPEE extraction; {item.total_apes} APE records "
                    "available for municipality."
                ),
                "limitations": (
                    "APE stock is selective and not equivalent to all dwellings. "
                    "Municipal coverage should be reported with every comparison."
                ),
                "notes": (
                    "Share calculated as (APE E + F + G) / all usable APE. "
                    "EPgl,nren median retained when available."
                ),
            }
        )

    with MATRIX_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames_matrix)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Validated {len(summaries)} municipal SIPEE APE records.")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
