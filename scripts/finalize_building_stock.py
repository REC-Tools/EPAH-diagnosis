from __future__ import annotations

import csv
from pathlib import Path

from epah_diagnosis.istat_building_stock import (
    CPA_2011_URL,
    download_cpa_2011,
    filter_by_codes,
    is_piemonte,
    weighted_share_pre_1981,
)
from epah_diagnosis.istat_posas import download_posas, filter_municipalities


ROOT = Path(__file__).resolve().parents[1]
MUNICIPALITIES_FILE = ROOT / "data" / "municipalities.csv"
MATRIX_FILE = ROOT / "data" / "verification_matrix.csv"
OUTPUT_FILE = ROOT / "data" / "indicators" / "building_stock_2011.csv"
BENCHMARK_FILE = ROOT / "data" / "indicators" / "building_stock_benchmarks_2011.csv"

SOURCE_PAGE = (
    "https://www.istat.it/notizia/basi-territoriali-e-variabili-censuarie/"
)
YEAR = "2011"
INDICATOR_ID = "old_building_stock"


def read_target_municipalities() -> set[str]:
    with MUNICIPALITIES_FILE.open(encoding="utf-8", newline="") as handle:
        return {
            row["municipality"].strip()
            for row in csv.DictReader(handle)
            if row["municipality"].strip()
        }


def main() -> None:
    target_names = read_target_municipalities()

    # POSAS provides a current official municipality name -> ISTAT code mapping.
    posas = download_posas()
    target_posas = filter_municipalities(posas, target_names)
    name_by_code = {
        item.municipality_code.zfill(6): item.municipality
        for item in target_posas
    }

    print("Downloading official ISTAT 2011 census-section variables...")
    all_municipalities = download_cpa_2011()
    records = filter_by_codes(all_municipalities, set(name_by_code))

    piemonte = [
        item for item in all_municipalities
        if is_piemonte(item.municipality_code)
    ]
    if not piemonte:
        raise ValueError("No Piemonte municipalities found in CPA 2011 dataset.")

    gc_share = weighted_share_pre_1981(records)
    piemonte_share = weighted_share_pre_1981(piemonte)
    italy_share = weighted_share_pre_1981(all_municipalities)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", encoding="utf-8", newline="") as handle:
        fields = [
            "municipality_code",
            "municipality",
            "year",
            "residential_buildings_total",
            "buildings_pre_1981",
            "share_pre_1981_pct",
            "buildings_pre_1919",
            "buildings_1919_1945",
            "buildings_1946_1960",
            "buildings_1961_1970",
            "buildings_1971_1980",
            "buildings_1981_1990",
            "buildings_1991_2000",
            "buildings_2001_2005",
            "buildings_after_2005",
            "green_community_share_pre_1981_pct",
            "piemonte_share_pre_1981_pct",
            "italy_share_pre_1981_pct",
            "source",
            "source_url",
            "quality",
            "limitations",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()

        for item in sorted(records, key=lambda x: name_by_code[x.municipality_code]):
            writer.writerow(
                {
                    "municipality_code": item.municipality_code,
                    "municipality": name_by_code[item.municipality_code],
                    "year": YEAR,
                    "residential_buildings_total": item.residential_buildings_total,
                    "buildings_pre_1981": item.buildings_pre_1981,
                    "share_pre_1981_pct": f"{item.share_pre_1981:.2f}",
                    "buildings_pre_1919": item.buildings_pre_1919,
                    "buildings_1919_1945": item.buildings_1919_1945,
                    "buildings_1946_1960": item.buildings_1946_1960,
                    "buildings_1961_1970": item.buildings_1961_1970,
                    "buildings_1971_1980": item.buildings_1971_1980,
                    "buildings_1981_1990": item.buildings_1981_1990,
                    "buildings_1991_2000": item.buildings_1991_2000,
                    "buildings_2001_2005": item.buildings_2001_2005,
                    "buildings_after_2005": item.buildings_after_2005,
                    "green_community_share_pre_1981_pct": f"{gc_share:.2f}",
                    "piemonte_share_pre_1981_pct": f"{piemonte_share:.2f}",
                    "italy_share_pre_1981_pct": f"{italy_share:.2f}",
                    "source": "ISTAT - Variabili censuarie CPA 2011",
                    "source_url": CPA_2011_URL,
                    "quality": (
                        "Fonte ufficiale ISTAT; valori assoluti per sezione di "
                        "censimento aggregati per codice Comune."
                    ),
                    "limitations": (
                        "Baseline 2011. L'epoca di costruzione è un proxy della "
                        "probabile inefficienza energetica e non misura riqualificazioni "
                        "successive o la classe energetica effettiva."
                    ),
                }
            )

    with BENCHMARK_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "territory",
                "year",
                "residential_buildings_total",
                "buildings_pre_1981",
                "share_pre_1981_pct",
                "method",
                "source_url",
            ],
        )
        writer.writeheader()
        for territory, items in (
            ("Green Community Sinergie in Canavese", records),
            ("Piemonte", piemonte),
            ("Italia", all_municipalities),
        ):
            writer.writerow(
                {
                    "territory": territory,
                    "year": YEAR,
                    "residential_buildings_total": sum(
                        item.residential_buildings_total for item in items
                    ),
                    "buildings_pre_1981": sum(
                        item.buildings_pre_1981 for item in items
                    ),
                    "share_pre_1981_pct": f"{weighted_share_pre_1981(items):.2f}",
                    "method": (
                        "Somma E8:E12 / somma E3; aggregazione ponderata "
                        "dei valori assoluti censuari."
                    ),
                    "source_url": CPA_2011_URL,
                }
            )

    by_name = {
        name_by_code[item.municipality_code].casefold(): item
        for item in records
    }

    with MATRIX_FILE.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
        fieldnames = list(rows[0].keys())

    updated = 0
    for row in rows:
        if row["indicator_id"] != INDICATOR_ID:
            continue

        item = by_name.get(row["municipality"].casefold())
        if item is None:
            raise ValueError(
                f"Missing building-stock result for {row['municipality']}"
            )

        row["status"] = "Dato validato"
        row["year"] = YEAR
        row["territorial_level"] = "Comune"
        row["unit"] = "%"
        row["source_url"] = SOURCE_PAGE
        row["value"] = f"{item.share_pre_1981:.2f}"
        row["quality"] = (
            "Fonte ufficiale ISTAT; dati 2011 per sezione aggregati a Comune"
        )
        row["limitations"] = (
            "Baseline 2011; quota edifici residenziali pre-1981 come proxy, "
            "non prestazione energetica osservata"
        )
        row["notes"] = (
            f"Edifici pre-1981: {item.buildings_pre_1981}; "
            f"edifici residenziali totali: {item.residential_buildings_total}; "
            "formula=(E8+E9+E10+E11+E12)/E3"
        )
        updated += 1

    if updated != 27:
        raise ValueError(f"Expected 27 updates, got {updated}.")

    with MATRIX_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print("Validated 27 municipal building-stock checks.")
    print(f"Green Community residential buildings pre-1981: {gc_share:.2f}%")
    print(f"Piemonte residential buildings pre-1981: {piemonte_share:.2f}%")
    print(f"Italia residential buildings pre-1981: {italy_share:.2f}%")


if __name__ == "__main__":
    main()
