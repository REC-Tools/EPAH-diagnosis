from __future__ import annotations

import csv
import statistics
from pathlib import Path

from epah_diagnosis.education_access import (
    SECONDARY_PATHWAYS_URL,
    SCHOOL_REGISTRY_URL,
    build_upper_secondary_poles,
    download_school_registry,
    download_secondary_pathways,
)
from epah_diagnosis.geography import download_boundaries, parse_boundaries_zip
from epah_diagnosis.service_access import (
    download_piemonte_matrix,
    nearest_services_from_zip,
)


ROOT = Path(__file__).resolve().parents[1]
MUNICIPALITIES_FILE = ROOT / "data" / "municipalities.csv"
MATRIX_FILE = ROOT / "data" / "verification_matrix.csv"
POLE_FILE = ROOT / "data" / "reference" / "upper_secondary_poles_2024_25.csv"
OUTPUT_FILE = ROOT / "data" / "indicators" / "upper_secondary_accessibility_minutes.csv"
SUMMARY_FILE = ROOT / "data" / "indicators" / "upper_secondary_accessibility_summary.csv"

INDICATOR_ID = "upper_secondary_accessibility"
INDICATOR_NAME = "Tempo stradale al polo scolastico superiore piu vicino"
MIM_SOURCE_PAGE = "https://dati.istruzione.it/opendata/"
ISTAT_SOURCE_PAGE = (
    "https://www.istat.it/notizia/matrici-di-contiguita-distanza-e-pendolarismo/"
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

    print("Downloading official MIM school datasets...")
    registry = download_school_registry()
    pathways = download_secondary_pathways()

    poles = build_upper_secondary_poles(registry, pathways, "Piemonte")
    pole_names = {pole.municipality for pole in poles}

    POLE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with POLE_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "municipality",
                "has_classical_or_scientific_lyceum",
                "has_technical_or_professional",
                "school_year",
                "source_registry",
                "source_pathways",
            ],
        )
        writer.writeheader()
        for pole in poles:
            writer.writerow(
                {
                    "municipality": pole.municipality,
                    "has_classical_or_scientific_lyceum": "yes",
                    "has_technical_or_professional": "yes",
                    "school_year": "2024/25",
                    "source_registry": SCHOOL_REGISTRY_URL,
                    "source_pathways": SECONDARY_PATHWAYS_URL,
                }
            )

    print(f"Identified {len(poles)} complete upper-secondary poles in Piemonte.")
    print("Resolving official ISTAT municipality codes...")
    codes = municipality_code_map(targets | pole_names)

    target_codes = {
        code: name for code, name in codes.items() if name in targets
    }
    pole_codes = {
        code: name for code, name in codes.items() if name in pole_names
    }

    if len(target_codes) != 27:
        raise ValueError(
            f"Expected 27 target municipality codes, found {len(target_codes)}."
        )
    if not pole_codes:
        raise ValueError("No upper-secondary pole municipality codes resolved.")

    print("Downloading official ISTAT Piemonte road-time matrix...")
    payload = download_piemonte_matrix()
    results = nearest_services_from_zip(payload, target_codes, pole_codes)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "municipality",
                "nearest_upper_secondary_pole",
                "travel_time_minutes",
                "distance_km",
                "school_year",
                "road_matrix_geography",
                "road_graph_year",
                "source_url_mim",
                "source_url_istat",
                "limitations",
            ],
        )
        writer.writeheader()
        for result in results:
            writer.writerow(
                {
                    "municipality": result.municipality,
                    "nearest_upper_secondary_pole": result.service_municipality,
                    "travel_time_minutes": f"{result.travel_time_minutes:.2f}",
                    "distance_km": (
                        "" if result.distance_km is None
                        else f"{result.distance_km:.2f}"
                    ),
                    "school_year": "2024/25",
                    "road_matrix_geography": "1 January 2021",
                    "road_graph_year": "2020",
                    "source_url_mim": MIM_SOURCE_PAGE,
                    "source_url_istat": ISTAT_SOURCE_PAGE,
                    "limitations": (
                        "SNAI-compatible service definition using current MIM "
                        "2024/25 school offer, but ISTAT road-time matrix reflects "
                        "2020 road graph and 2021 municipal geography."
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
                    "Minimum ISTAT TEP_TOT effective road travel time to a "
                    "municipality offering both classical/scientific lyceum and "
                    "technical/professional upper-secondary pathways."
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
            raise ValueError(
                f"Missing school accessibility result for {municipality}"
            )

        rows.append(
            {
                "municipality": municipality,
                "indicator_id": INDICATOR_ID,
                "indicator_name": INDICATOR_NAME,
                "macro_area": "Territory/Mobility",
                "status": "Dato validato",
                "source_priority": "MIM + ISTAT",
                "year": "2024/25 + 2021",
                "territorial_level": "Comune",
                "unit": "minuti",
                "source_url": MIM_SOURCE_PAGE,
                "value": f"{result.travel_time_minutes:.2f}",
                "quality": (
                    "MIM school offer + ISTAT TEP_TOT road travel time; "
                    "SNAI-compatible complete upper-secondary definition"
                ),
                "limitations": (
                    "Municipal modelled time; does not represent public-transport "
                    "timetables or individual student travel."
                ),
                "notes": (
                    "Polo scolastico superiore piu vicino: "
                    f"{result.service_municipality}"
                ),
            }
        )

    with MATRIX_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print("Validated 27 municipal upper-secondary-accessibility records.")
    print(
        f"Mean: {statistics.mean(values):.2f} min; "
        f"median: {statistics.median(values):.2f} min; "
        f"range: {min(values):.2f}-{max(values):.2f} min"
    )


if __name__ == "__main__":
    main()
