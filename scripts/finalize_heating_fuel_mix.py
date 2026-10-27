from __future__ import annotations

import csv
import statistics
from pathlib import Path

from epah_diagnosis.heating_fuel_mix import (
    FUEL_FIELDS,
    filter_municipalities,
    parse_heating_fuel_mix_csv,
)


ROOT = Path(__file__).resolve().parents[1]
INPUT_FILE = ROOT / "data" / "raw" / "istat_heating_fuel_mix_2011.csv"
MUNICIPALITIES_FILE = ROOT / "data" / "municipalities.csv"
MATRIX_FILE = ROOT / "data" / "verification_matrix.csv"
OUTPUT_FILE = ROOT / "data" / "indicators" / "heating_fuel_mix_2011.csv"
SUMMARY_FILE = ROOT / "data" / "indicators" / "heating_fuel_mix_summary_2011.csv"

INDICATOR_ID = "non_natural_gas_heating_share"
INDICATOR_NAME = "Abitazioni riscaldate con vettori diversi dal gas naturale"
SOURCE_PAGE = (
    "https://www.istat.it/statistiche-per-temi/censimenti/"
    "censimenti-storici/popolazione-e-abitazioni/popolazione-2011/"
)
YEAR = 2011


def read_target_municipalities() -> set[str]:
    with MUNICIPALITIES_FILE.open(encoding="utf-8", newline="") as handle:
        return {
            row["municipality"].strip()
            for row in csv.DictReader(handle)
            if row["municipality"].strip()
        }


def _read_input(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("Unable to decode ISTAT heating fuel-mix export.")


def main() -> None:
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Missing official ISTAT municipal export: {INPUT_FILE}. "
            "Export the 2011 census table on occupied dwellings with heating "
            "system by fuel/energy type at municipality level and save it "
            "there before running this finalizer."
        )

    targets = read_target_municipalities()
    records = parse_heating_fuel_mix_csv(_read_input(INPUT_FILE))
    selected = filter_municipalities(records, targets)

    if len(selected) != 27:
        raise ValueError(
            f"Expected 27 municipality fuel-mix records, found {len(selected)}."
        )

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = [
            "municipality",
            "heated_dwellings_total",
            *FUEL_FIELDS,
            "non_natural_gas_share_pct",
            "reference_year",
            "source_url",
            "limitations",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()

        for item in selected:
            writer.writerow(
                {
                    "municipality": item.municipality,
                    "heated_dwellings_total": item.heated_dwellings_total,
                    **{
                        field: getattr(item, field)
                        for field in FUEL_FIELDS
                    },
                    "non_natural_gas_share_pct": (
                        f"{item.non_natural_gas_share_pct:.2f}"
                    ),
                    "reference_year": YEAR,
                    "source_url": SOURCE_PAGE,
                    "limitations": (
                        "Census 2011 structural baseline. Fuel categories describe "
                        "the energy feeding the heating system, but do not measure "
                        "current prices, efficiency, actual consumption or household "
                        "ability to afford adequate heating."
                    ),
                }
            )

    total_heated = sum(item.heated_dwellings_total for item in selected)
    aggregate = {
        field: sum(getattr(item, field) for item in selected)
        for field in FUEL_FIELDS
    }
    weighted_non_gas = (
        (total_heated - aggregate["natural_gas"]) / total_heated * 100
        if total_heated else 0.0
    )

    with SUMMARY_FILE.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = [
            "territory",
            "heated_dwellings_total",
            *[f"{field}_share_pct" for field in FUEL_FIELDS],
            "non_natural_gas_share_pct",
            "method",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()

        row = {
            "territory": "Green Community Sinergie in Canavese",
            "heated_dwellings_total": total_heated,
            "non_natural_gas_share_pct": f"{weighted_non_gas:.2f}",
            "method": (
                "Weighted shares across the 27 municipalities using number of "
                "heated occupied dwellings as denominator."
            ),
        }
        for field in FUEL_FIELDS:
            row[f"{field}_share_pct"] = (
                f"{aggregate[field] / total_heated * 100:.2f}"
                if total_heated else "0.00"
            )
        writer.writerow(row)

    with MATRIX_FILE.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
        fieldnames = list(rows[0].keys())

    existing = {
        (row["municipality"].casefold(), row["indicator_id"])
        for row in rows
    }

    for item in selected:
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
                "source_priority": "ISTAT",
                "year": str(YEAR),
                "territorial_level": "Comune",
                "unit": "%",
                "source_url": SOURCE_PAGE,
                "value": f"{item.non_natural_gas_share_pct:.2f}",
                "quality": (
                    "Official 2011 census municipality table on occupied "
                    "dwellings with heating system by fuel/energy type."
                ),
                "limitations": (
                    "Structural baseline from 2011; the local heating mix may "
                    "have changed materially since the census."
                ),
                "notes": (
                    "Descriptive fuel-mix indicator. A high non-gas share is not "
                    "automatically energy poverty and must be cross-read with "
                    "income, climate, building efficiency and current fuel costs."
                ),
            }
        )

    with MATRIX_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    municipal_values = [item.non_natural_gas_share_pct for item in selected]
    print("Validated 27 municipal heating fuel-mix records.")
    print(
        f"Green Community weighted non-natural-gas share: "
        f"{weighted_non_gas:.2f}%."
    )
    print(
        f"Municipal median: {statistics.median(municipal_values):.2f}%."
    )
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
