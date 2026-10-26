from __future__ import annotations

import csv
import statistics
from collections import defaultdict
from pathlib import Path

from epah_diagnosis.geography import download_boundaries, parse_boundaries_zip
from epah_diagnosis.rail_access import (
    RFI_STATIONS_URL,
    download_rfi_stations,
    station_municipalities,
)
from epah_diagnosis.service_access import (
    download_piemonte_matrix,
    nearest_services_from_zip,
)


ROOT = Path(__file__).resolve().parents[1]
MUNICIPALITIES_FILE = ROOT / "data" / "municipalities.csv"
MATRIX_FILE = ROOT / "data" / "verification_matrix.csv"
REFERENCE_FILE = ROOT / "data" / "reference" / "rfi_piemonte_stations_current.csv"
OUTPUT_FILE = ROOT / "data" / "indicators" / "rail_accessibility_minutes.csv"
SUMMARY_FILE = ROOT / "data" / "indicators" / "rail_accessibility_summary.csv"

INDICATOR_ID = "rail_access_minutes"
INDICATOR_NAME = "Tempo stradale alla stazione ferroviaria RFI piu vicina"
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

    print("Downloading current official RFI station catalogue...")
    stations = download_rfi_stations()
    rail_municipalities = station_municipalities(stations)

    REFERENCE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with REFERENCE_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "station_name",
                "municipality",
                "province",
                "rfi_classification",
                "source_url",
            ],
        )
        writer.writeheader()
        for station in sorted(
            stations,
            key=lambda item: (item.municipality, item.station_name),
        ):
            writer.writerow(
                {
                    "station_name": station.station_name,
                    "municipality": station.municipality,
                    "province": station.province,
                    "rfi_classification": station.classification,
                    "source_url": RFI_STATIONS_URL,
                }
            )

    print(
        f"Identified {len(stations)} RFI stations in "
        f"{len(rail_municipalities)} Piemonte municipalities."
    )

    print("Resolving official ISTAT municipality codes...")
    codes = municipality_code_map(targets | rail_municipalities)
    target_codes = {
        code: name for code, name in codes.items() if name in targets
    }
    rail_codes = {
        code: name for code, name in codes.items() if name in rail_municipalities
    }

    if len(target_codes) != 27:
        raise ValueError(
            f"Expected 27 target municipality codes, found {len(target_codes)}."
        )
    if not rail_codes:
        raise ValueError("No RFI station municipality codes resolved.")

    print("Downloading official ISTAT Piemonte road-time matrix...")
    payload = download_piemonte_matrix()
    results = nearest_services_from_zip(payload, target_codes, rail_codes)

    station_classes: dict[str, set[str]] = defaultdict(set)
    station_names: dict[str, list[str]] = defaultdict(list)
    for station in stations:
        station_classes[station.municipality].add(station.classification)
        station_names[station.municipality].append(station.station_name)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "municipality",
                "nearest_station_municipality",
                "stations_in_destination",
                "rfi_classes",
                "travel_time_minutes",
                "distance_km",
                "road_matrix_geography",
                "road_graph_year",
                "source_url_rfi",
                "source_url_istat",
                "limitations",
            ],
        )
        writer.writeheader()

        for result in results:
            destination = result.service_municipality
            writer.writerow(
                {
                    "municipality": result.municipality,
                    "nearest_station_municipality": destination,
                    "stations_in_destination": " | ".join(
                        sorted(station_names[destination])
                    ),
                    "rfi_classes": " | ".join(
                        sorted(station_classes[destination])
                    ),
                    "travel_time_minutes": f"{result.travel_time_minutes:.2f}",
                    "distance_km": (
                        "" if result.distance_km is None
                        else f"{result.distance_km:.2f}"
                    ),
                    "road_matrix_geography": "1 January 2021",
                    "road_graph_year": "2020",
                    "source_url_rfi": RFI_STATIONS_URL,
                    "source_url_istat": ISTAT_SOURCE_PAGE,
                    "limitations": (
                        "Access time is modelled between municipal reference "
                        "points. It does not include rail timetable frequency, "
                        "service disruptions or public-transport access to station."
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
                    "municipality listed in the current RFI station catalogue."
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
                f"Missing rail accessibility result for {municipality}"
            )

        rows.append(
            {
                "municipality": municipality,
                "indicator_id": INDICATOR_ID,
                "indicator_name": INDICATOR_NAME,
                "macro_area": "Territory/Mobility",
                "status": "Dato validato",
                "source_priority": "RFI + ISTAT",
                "year": "current + 2021",
                "territorial_level": "Comune",
                "unit": "minuti",
                "source_url": RFI_STATIONS_URL,
                "value": f"{result.travel_time_minutes:.2f}",
                "quality": (
                    "Current RFI station catalogue + ISTAT TEP_TOT "
                    "effective road travel time"
                ),
                "limitations": (
                    "Municipal road-access proxy; does not measure train frequency, "
                    "timetable quality or current disruptions."
                ),
                "notes": (
                    "Comune con stazione RFI piu vicino: "
                    f"{result.service_municipality}"
                ),
            }
        )

    with MATRIX_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print("Validated 27 municipal rail-accessibility records.")
    print(
        f"Mean: {statistics.mean(values):.2f} min; "
        f"median: {statistics.median(values):.2f} min; "
        f"range: {min(values):.2f}-{max(values):.2f} min"
    )


if __name__ == "__main__":
    main()
