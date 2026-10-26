from __future__ import annotations

import csv
import statistics
from pathlib import Path

from epah_diagnosis.geography import download_boundaries, parse_boundaries_zip
from epah_diagnosis.service_access import (
    download_piemonte_matrix,
    nearest_services_from_zip,
    read_service_municipalities,
)


ROOT = Path(__file__).resolve().parents[1]
MUNICIPALITIES_FILE = ROOT / "data" / "municipalities.csv"
DEA_REFERENCE = ROOT / "data" / "reference" / "piemonte_dea_hospitals.csv"
MATRIX_FILE = ROOT / "data" / "verification_matrix.csv"
OUTPUT_FILE = ROOT / "data" / "indicators" / "dea_accessibility_minutes.csv"
SUMMARY_FILE = ROOT / "data" / "indicators" / "dea_accessibility_summary.csv"

INDICATOR_ID = "dea_access_minutes"
INDICATOR_NAME = "Tempo stradale al DEA I/II piu vicino"
ISTAT_SOURCE_PAGE = (
    "https://www.istat.it/notizia/matrici-di-contiguita-distanza-e-pendolarismo/"
)
HEALTH_SOURCE_PAGE = (
    "https://www.salute.gov.it/new/it/banche-dati/"
    "elenco-strutture-della-rete-dellemergenza-ospedaliera/"
)


def read_target_municipalities() -> set[str]:
    with MUNICIPALITIES_FILE.open(encoding="utf-8", newline="") as handle:
        return {
            row["municipality"].strip()
            for row in csv.DictReader(handle)
            if row["municipality"].strip()
        }


def municipality_code_map(names: set[str]) -> dict[str, str]:
    print("Resolving official ISTAT municipality codes...")
    boundaries = parse_boundaries_zip(download_boundaries(), names)
    return {
        feature["properties"]["municipality_code"]:
        feature["properties"]["municipality"]
        for feature in boundaries["features"]
    }


def main() -> None:
    targets = read_target_municipalities()
    dea_municipalities = read_service_municipalities(DEA_REFERENCE)

    all_names = targets | dea_municipalities
    codes = municipality_code_map(all_names)

    target_codes = {
        code: name for code, name in codes.items() if name in targets
    }
    dea_codes = {
        code: name for code, name in codes.items() if name in dea_municipalities
    }

    if len(target_codes) != 27:
        raise ValueError(
            f"Expected 27 target municipality codes, found {len(target_codes)}."
        )

    print("Downloading official ISTAT Piemonte road-time matrix...")
    payload = download_piemonte_matrix()
    results = nearest_services_from_zip(payload, target_codes, dea_codes)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "municipality",
                "nearest_dea_municipality",
                "travel_time_minutes",
                "distance_km",
                "road_matrix_geography",
                "road_graph_year",
                "health_reference",
                "source_url_istat",
                "source_url_health",
                "limitations",
            ],
        )
        writer.writeheader()
        for result in results:
            writer.writerow(
                {
                    "municipality": result.municipality,
                    "nearest_dea_municipality": result.service_municipality,
                    "travel_time_minutes": f"{result.travel_time_minutes:.2f}",
                    "distance_km": (
                        "" if result.distance_km is None
                        else f"{result.distance_km:.2f}"
                    ),
                    "road_matrix_geography": "1 January 2021",
                    "road_graph_year": "2020",
                    "health_reference": "Piemonte DEA I/II reference snapshot",
                    "source_url_istat": ISTAT_SOURCE_PAGE,
                    "source_url_health": HEALTH_SOURCE_PAGE,
                    "limitations": (
                        "TEP_TOT is ISTAT modelled effective road time from the "
                        "municipal reference point, not door-to-door time for "
                        "individual residents."
                    ),
                }
            )

    values = [result.travel_time_minutes for result in results]
    with SUMMARY_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "territory",
                "municipality_count",
                "mean_minutes",
                "median_minutes",
                "min_minutes",
                "max_minutes",
                "municipalities_over_30_min",
                "municipalities_over_40_min",
                "method",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "territory": "Green Community Sinergie in Canavese",
                "municipality_count": len(results),
                "mean_minutes": f"{statistics.mean(values):.2f}",
                "median_minutes": f"{statistics.median(values):.2f}",
                "min_minutes": f"{min(values):.2f}",
                "max_minutes": f"{max(values):.2f}",
                "municipalities_over_30_min": sum(v > 30 for v in values),
                "municipalities_over_40_min": sum(v > 40 for v in values),
                "method": (
                    "Minimum ISTAT TEP_TOT effective road travel time from each "
                    "municipality to a municipality hosting a DEA I/II hospital."
                ),
            }
        )

    by_name = {result.municipality.casefold(): result for result in results}

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

        result = by_name.get(key)
        if result is None:
            raise ValueError(f"Missing DEA accessibility result for {municipality}")

        rows.append(
            {
                "municipality": municipality,
                "indicator_id": INDICATOR_ID,
                "indicator_name": INDICATOR_NAME,
                "macro_area": "Territory/Mobility",
                "status": "Dato validato",
                "source_priority": "ISTAT + Ministero Salute / Regione Piemonte",
                "year": "2021/2025",
                "territorial_level": "Comune",
                "unit": "minuti",
                "source_url": ISTAT_SOURCE_PAGE,
                "value": f"{result.travel_time_minutes:.2f}",
                "quality": (
                    "ISTAT TEP_TOT effective road travel time; DEA destinations "
                    "matched by official six-digit municipality codes"
                ),
                "limitations": (
                    "Municipal modelled time, not individual accessibility; "
                    "road graph 2020 and municipal geography 2021"
                ),
                "notes": f"DEA piu vicino: {result.service_municipality}",
            }
        )

    with MATRIX_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print("Validated 27 municipal DEA-accessibility records.")
    print(
        f"Mean: {statistics.mean(values):.2f} min; "
        f"median: {statistics.median(values):.2f} min; "
        f"range: {min(values):.2f}-{max(values):.2f} min"
    )


if __name__ == "__main__":
    main()
