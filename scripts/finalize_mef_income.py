from __future__ import annotations

import csv
from pathlib import Path

from epah_diagnosis.mef_income import (
    MEF_IRPEF_2024_URL,
    download_mef,
    filter_municipalities,
)


ROOT = Path(__file__).resolve().parents[1]
MUNICIPALITIES_FILE = ROOT / "data" / "municipalities.csv"
MATRIX_FILE = ROOT / "data" / "verification_matrix.csv"
OUTPUT_FILE = ROOT / "data" / "indicators" / "income_vulnerability_2024.csv"
BENCHMARK_FILE = ROOT / "data" / "indicators" / "income_vulnerability_benchmarks_2024.csv"

SOURCE_PAGE = (
    "https://www1.finanze.gov.it/finanze/analisi_stat/public/"
    "index.php?opendata=yes&search_class%5B0%5D=cCOMUNE"
)
TAX_YEAR = "2024"
DECLARATION_YEAR = "2025"
PUBLICATION_DATE = "2026-04-23"
INDICATOR_ID = "income_vulnerability"


def read_target_municipalities() -> set[str]:
    with MUNICIPALITIES_FILE.open(encoding="utf-8", newline="") as handle:
        return {
            row["municipality"].strip()
            for row in csv.DictReader(handle)
            if row["municipality"].strip()
        }


def weighted_share(items) -> float:
    total_taxpayers = sum(item.taxpayers_total for item in items)
    low_income = sum(item.taxpayers_income_le_15000 for item in items)
    if total_taxpayers == 0:
        raise ZeroDivisionError("Benchmark taxpayer total is zero.")
    return round(low_income / total_taxpayers * 100, 2)


def weighted_mean_income(items) -> float | None:
    freq = sum(item.total_income_frequency or 0 for item in items)
    amount = sum(item.total_income_amount_eur or 0 for item in items)
    if freq <= 0 or amount <= 0:
        return None
    return round(amount / freq, 2)


def write_indicator_file(selected, gc_share, piemonte_share, italy_share) -> None:
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", encoding="utf-8", newline="") as handle:
        fields = [
            "municipality_code",
            "municipality",
            "tax_year",
            "declaration_year",
            "publication_date",
            "taxpayers_total",
            "taxpayers_income_le_15000",
            "share_income_le_15000_pct",
            "mean_total_income_eur",
            "green_community_share_pct",
            "piemonte_share_pct",
            "italy_share_pct",
            "delta_vs_green_community_pp",
            "source",
            "source_url",
            "quality",
            "limitations",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()

        for item in sorted(selected, key=lambda x: x.municipality):
            value = item.share_income_le_15000
            writer.writerow(
                {
                    "municipality_code": item.municipality_code,
                    "municipality": item.municipality,
                    "tax_year": TAX_YEAR,
                    "declaration_year": DECLARATION_YEAR,
                    "publication_date": PUBLICATION_DATE,
                    "taxpayers_total": item.taxpayers_total,
                    "taxpayers_income_le_15000": item.taxpayers_income_le_15000,
                    "share_income_le_15000_pct": f"{value:.2f}",
                    "mean_total_income_eur": (
                        f"{item.mean_total_income_eur:.2f}"
                        if item.mean_total_income_eur is not None
                        else ""
                    ),
                    "green_community_share_pct": f"{gc_share:.2f}",
                    "piemonte_share_pct": f"{piemonte_share:.2f}",
                    "italy_share_pct": f"{italy_share:.2f}",
                    "delta_vs_green_community_pp": f"{value - gc_share:.2f}",
                    "source": "MEF - Open Data Dichiarazioni",
                    "source_url": SOURCE_PAGE,
                    "quality": (
                        "Fonte ufficiale MEF; dato comunale; classi di reddito "
                        "pubblicate direttamente nella fonte."
                    ),
                    "limitations": (
                        "Proxy fiscale riferito ai contribuenti, non alle famiglie; "
                        "non equivale a una soglia ufficiale di povertà o povertà energetica."
                    ),
                }
            )


def write_benchmarks(gc_items, piemonte_items, italy_items) -> None:
    rows = [
        ("Green Community Sinergie in Canavese", gc_items),
        ("Piemonte", piemonte_items),
        ("Italia", italy_items),
    ]

    with BENCHMARK_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "territory",
                "tax_year",
                "share_income_le_15000_pct",
                "mean_total_income_eur",
                "taxpayers_total",
                "method",
                "source_url",
            ],
        )
        writer.writeheader()
        for territory, items in rows:
            mean_income = weighted_mean_income(items)
            writer.writerow(
                {
                    "territory": territory,
                    "tax_year": TAX_YEAR,
                    "share_income_le_15000_pct": f"{weighted_share(items):.2f}",
                    "mean_total_income_eur": (
                        f"{mean_income:.2f}" if mean_income is not None else ""
                    ),
                    "taxpayers_total": sum(item.taxpayers_total for item in items),
                    "method": (
                        "Somma contribuenti nelle classi <=15.000 euro / "
                        "somma numero contribuenti"
                    ),
                    "source_url": SOURCE_PAGE,
                }
            )


def update_verification_matrix(selected) -> None:
    with MATRIX_FILE.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
        fieldnames = list(rows[0].keys())

    values = {item.municipality.casefold(): item for item in selected}
    updated = 0

    for row in rows:
        if row["indicator_id"] != INDICATOR_ID:
            continue

        item = values.get(row["municipality"].casefold())
        if item is None:
            # Fallback for accent/apostrophe differences is already handled before
            # this stage; a mismatch here should fail visibly.
            raise ValueError(f"Missing MEF result for {row['municipality']}")

        value = item.share_income_le_15000
        if not 0 <= value <= 100:
            raise ValueError(f"Invalid MEF share for {item.municipality}: {value}")

        row["status"] = "Dato validato"
        row["year"] = TAX_YEAR
        row["territorial_level"] = "Comune"
        row["unit"] = "%"
        row["source_url"] = SOURCE_PAGE
        row["value"] = f"{value:.2f}"
        row["quality"] = (
            "Fonte ufficiale MEF; frequenze comunali per classi di reddito"
        )
        row["limitations"] = (
            "Proxy riferito ai contribuenti; non misura reddito familiare equivalente "
            "né identifica direttamente povertà energetica"
        )
        row["notes"] = (
            f"Contribuenti <=15.000 euro: {item.taxpayers_income_le_15000}; "
            f"contribuenti totali: {item.taxpayers_total}; "
            f"anno imposta {TAX_YEAR}, dichiarazioni {DECLARATION_YEAR}"
        )
        updated += 1

    if updated != 27:
        raise ValueError(f"Expected to update 27 MEF rows, updated {updated}")

    with MATRIX_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    target_names = read_target_municipalities()
    all_municipalities = download_mef(MEF_IRPEF_2024_URL)
    selected = filter_municipalities(all_municipalities, target_names)

    piemonte = [
        item
        for item in all_municipalities
        if item.region.strip().casefold() == "piemonte"
    ]
    if not piemonte:
        raise ValueError("No Piemonte rows found in MEF dataset.")

    gc_share = weighted_share(selected)
    piemonte_share = weighted_share(piemonte)
    italy_share = weighted_share(all_municipalities)

    write_indicator_file(selected, gc_share, piemonte_share, italy_share)
    write_benchmarks(selected, piemonte, all_municipalities)
    update_verification_matrix(selected)

    print(f"Validated {len(selected)} municipal MEF income checks.")
    print(f"Green Community <=15,000 EUR: {gc_share:.2f}%")
    print(f"Piemonte <=15,000 EUR: {piemonte_share:.2f}%")
    print(f"Italia <=15,000 EUR: {italy_share:.2f}%")


if __name__ == "__main__":
    main()
