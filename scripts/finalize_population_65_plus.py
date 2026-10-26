from __future__ import annotations

import csv
from pathlib import Path

from epah_diagnosis.istat_posas import download_posas, filter_municipalities


ROOT = Path(__file__).resolve().parents[1]
MUNICIPALITIES_FILE = ROOT / "data" / "municipalities.csv"
MATRIX_FILE = ROOT / "data" / "verification_matrix.csv"
OUTPUT_FILE = ROOT / "data" / "indicators" / "population_65_plus_2026.csv"
BENCHMARK_FILE = ROOT / "data" / "indicators" / "population_65_plus_benchmarks_2026.csv"

SOURCE_URL = "https://demo.istat.it/data/posas/POSAS_2026_it_Comuni.zip"
SOURCE_PAGE = "https://demo.istat.it/app/?i=POS"
YEAR = "2026"
INDICATOR_ID = "population_65_plus"

# Province codes belonging to Piemonte.
PIEMONTE_PROVINCE_CODES = {
    "001",  # Torino
    "002",  # Vercelli
    "003",  # Novara
    "004",  # Cuneo
    "005",  # Asti
    "006",  # Alessandria
    "096",  # Biella
    "103",  # Verbano-Cusio-Ossola
}


def read_target_municipalities() -> set[str]:
    with MUNICIPALITIES_FILE.open(encoding="utf-8", newline="") as handle:
        return {
            row["municipality"].strip()
            for row in csv.DictReader(handle)
            if row["municipality"].strip()
        }


def weighted_share(items) -> float:
    total_population = sum(item.population_total for item in items)
    total_65_plus = sum(item.population_65_plus for item in items)
    if total_population == 0:
        raise ZeroDivisionError("Benchmark population is zero.")
    return round(total_65_plus / total_population * 100, 2)


def classify_relative(value: float, benchmark: float) -> str:
    """Simple descriptive comparison; not a poverty score."""
    delta = value - benchmark
    if delta >= 5:
        return "Molto sopra media GC"
    if delta >= 2:
        return "Sopra media GC"
    if delta <= -5:
        return "Molto sotto media GC"
    if delta <= -2:
        return "Sotto media GC"
    return "In linea con media GC"


def write_indicator_file(selected, gc_share: float, piemonte_share: float, italy_share: float) -> None:
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", encoding="utf-8", newline="") as handle:
        fields = [
            "municipality_code",
            "municipality",
            "year",
            "population_total",
            "population_65_plus",
            "share_65_plus_pct",
            "green_community_share_pct",
            "piemonte_share_pct",
            "italy_share_pct",
            "delta_vs_green_community_pp",
            "relative_class",
            "source",
            "source_url",
            "quality",
            "limitations",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()

        for item in sorted(selected, key=lambda x: x.municipality):
            value = item.share_65_plus
            writer.writerow(
                {
                    "municipality_code": item.municipality_code,
                    "municipality": item.municipality,
                    "year": YEAR,
                    "population_total": item.population_total,
                    "population_65_plus": item.population_65_plus,
                    "share_65_plus_pct": f"{value:.2f}",
                    "green_community_share_pct": f"{gc_share:.2f}",
                    "piemonte_share_pct": f"{piemonte_share:.2f}",
                    "italy_share_pct": f"{italy_share:.2f}",
                    "delta_vs_green_community_pp": f"{value - gc_share:.2f}",
                    "relative_class": classify_relative(value, gc_share),
                    "source": "ISTAT POSAS",
                    "source_url": SOURCE_URL,
                    "quality": "Fonte ufficiale ISTAT; dato comunale disponibile per singola età.",
                    "limitations": (
                        "La popolazione al 1 gennaio 2026 per età e sesso è una stima ISTAT "
                        "coerente con le risultanze censuarie e il bilancio provvisorio 2025. "
                        "La classe relativa è descrittiva e non costituisce un indice di povertà energetica."
                    ),
                }
            )


def write_benchmarks(gc_share: float, piemonte_share: float, italy_share: float) -> None:
    with BENCHMARK_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["territory", "year", "share_65_plus_pct", "method", "source_url"],
        )
        writer.writeheader()
        writer.writerows(
            [
                {
                    "territory": "Green Community Sinergie in Canavese",
                    "year": YEAR,
                    "share_65_plus_pct": f"{gc_share:.2f}",
                    "method": "Somma residenti 65+ dei 27 Comuni / somma popolazione dei 27 Comuni",
                    "source_url": SOURCE_URL,
                },
                {
                    "territory": "Piemonte",
                    "year": YEAR,
                    "share_65_plus_pct": f"{piemonte_share:.2f}",
                    "method": "Aggregazione comunale POSAS dei Comuni piemontesi",
                    "source_url": SOURCE_URL,
                },
                {
                    "territory": "Italia",
                    "year": YEAR,
                    "share_65_plus_pct": f"{italy_share:.2f}",
                    "method": "Aggregazione comunale POSAS nazionale",
                    "source_url": SOURCE_URL,
                },
            ]
        )


def update_verification_matrix(selected) -> None:
    with MATRIX_FILE.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
        fieldnames = list(rows[0].keys())

    values = {item.municipality: item for item in selected}
    updated = 0

    for row in rows:
        if row["indicator_id"] != INDICATOR_ID:
            continue

        item = values.get(row["municipality"])
        if item is None:
            raise ValueError(f"Missing 65+ result for {row['municipality']}")

        row["status"] = "Dato validato"
        row["year"] = YEAR
        row["territorial_level"] = "Comune"
        row["unit"] = "%"
        row["source_url"] = SOURCE_PAGE
        row["value"] = f"{item.share_65_plus:.2f}"
        row["quality"] = "Fonte ufficiale ISTAT POSAS; calcolo replicabile da dati per singola età"
        row["limitations"] = "Dato 1 gennaio 2026 stimato/provvisorio; indicatore proxy di vulnerabilità"
        row["notes"] = (
            f"Residenti 65+: {item.population_65_plus}; "
            f"residenti totali: {item.population_total}"
        )
        updated += 1

    if updated != 27:
        raise ValueError(f"Expected to update 27 verification rows, updated {updated}")

    with MATRIX_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    target_names = read_target_municipalities()
    all_municipalities = download_posas(SOURCE_URL)
    selected = filter_municipalities(all_municipalities, target_names)

    if len(selected) != 27:
        raise ValueError(f"Expected 27 Green Community municipalities, found {len(selected)}")

    piemonte = [
        item
        for item in all_municipalities
        if item.municipality_code[:3] in PIEMONTE_PROVINCE_CODES
    ]

    gc_share = weighted_share(selected)
    piemonte_share = weighted_share(piemonte)
    italy_share = weighted_share(all_municipalities)

    write_indicator_file(selected, gc_share, piemonte_share, italy_share)
    write_benchmarks(gc_share, piemonte_share, italy_share)
    update_verification_matrix(selected)

    print(f"Validated {len(selected)} municipal 65+ checks.")
    print(f"Green Community 65+: {gc_share:.2f}%")
    print(f"Piemonte 65+: {piemonte_share:.2f}%")
    print(f"Italia 65+: {italy_share:.2f}%")


if __name__ == "__main__":
    main()
