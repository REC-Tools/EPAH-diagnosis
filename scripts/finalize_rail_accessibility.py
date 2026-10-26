from __future__ import annotations

import csv
import statistics
from collections import defaultdict
from pathlib import Path
from epah_diagnosis.matrix_update import upsert_indicator_rows

from epah_diagnosis.geography import download_boundaries, parse_boundaries_zip
from epah_diagnosis.rail_access import load_rail_gateways, station_municipalities
from epah_diagnosis.service_access import (
    download_piemonte_matrix,
    nearest_services_from_zip,
)


ROOT = Path(__file__).resolve().parents[1]
MUNICIPALITIES_FILE = ROOT / "data" / "municipalities.csv"
MATRIX_FILE = ROOT / "data" / "verification_matrix.csv"
REFERENCE_FILE = ROOT / "data" / "reference" / "canavese_active_rail_gateways.csv"
OUTPUT_FILE = ROOT / "data" / "indicators" / "rail_accessibility_minutes.csv"
SUMMARY_FILE = ROOT / "data" / "indicators" / "rail_accessibility_summary.csv"

INDICATOR_ID = "rail_accessibility"
INDICATOR_NAME = "Tempo stradale al gateway ferroviario passeggeri attivo piu vicino"
ISTAT_SOURCE_PAGE = (
    "https://www.istat.it/notizia/matrici-di-contiguita-distanza-e-pendolarismo/"
)
SFM_SOURCE_PAGE = "https://www.sfmtorino.it/le-linee-sfm/sfm1-pont-rivarolo-chieri/"


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

    print("Loading validated active rail-gateway reference snapshot...")
    gateways = load_rail_gateways(REFERENCE_FILE)
    rail_municipalities = station_municipalities(gateways)

    print(
        f"Loaded {len(gateways)} active rail gateways in "
        f"{len(rail_municipalities)} municipalities."
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
        raise ValueError("No rail gateway municipality codes resolved.")

    print("Downloading official ISTAT Piemonte road-time matrix...")
    payload = download_piemonte_matrix()
    results = nearest_services_from_zip(payload, target_codes, rail_codes)

    station_names: dict[str, list[str]] = defaultdict(list)
    source_notes: dict[str, list[str]] = defaultdict(list)
    for gateway in gateways:
        station_names[gateway.municipality].append(gateway.station_name)
        if gateway.notes:
            source_notes[gateway.municipality].append(gateway.notes)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "municipality",
                "nearest_active_rail_municipality",
                "stations_in_destination",
                "travel_time_minutes",
                "distance_km",
                "road_matrix_geography",
                "road_graph_year",
                "rail_reference",
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
                    "nearest_active_rail_municipality": destination,
                    "stations_in_destination": " | ".join(
                        sorted(station_names[destination])
                    ),
                    "travel_time_minutes": f"{result.travel_time_minutes:.2f}",
                    "distance_km": (
                        "" if result.distance_km is None
                        else f"{result.distance_km:.2f}"
                    ),
                    "road_matrix_geography": "1 January 2021",
                    "road_graph_year": "2020",
                    "rail_reference": (
                        "Versioned official-source snapshot of active nearby "
                        "passenger rail gateways"
                    ),
                    "source_url_istat": ISTAT_SOURCE_PAGE,
                    "limitations": (
                        "Municipal road-access proxy. Rail gateway list is a "
                        "versioned reference tailored to the Canavese study area; "
                        "service status should be reviewed when timetables change."
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
                    "validated active passenger rail gateway relevant to Canavese."
                ),
            }
        )

    by_name = {result.municipality.casefold(): result for result in results}

    with MATRIX_FILE.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    original_count = len(rows)


    for municipality in sorted(targets):
        key = municipality.casefold()
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
                "source_priority": "RFI / SFM Torino + ISTAT",
                "year": "2026 + 2021",
                "territorial_level": "Comune",
                "unit": "minuti",
                "source_url": SFM_SOURCE_PAGE,
                "value": f"{result.travel_time_minutes:.2f}",
                "quality": (
                    "Validated active rail-gateway snapshot + ISTAT TEP_TOT "
                    "effective road travel time"
                ),
                "limitations": (
                    "Municipal road-access proxy; does not measure train frequency, "
                    "timetable quality or individual access to stations."
                ),
                "notes": (
                    "Gateway ferroviario attivo piu vicino: "
                    f"{result.service_municipality}"
                ),
            }
        )

    upsert_indicator_rows(MATRIX_FILE, INDICATOR_ID, rows[original_count:])

    print("Validated 27 municipal rail-accessibility records.")
    print(
        f"Mean: {statistics.mean(values):.2f} min; "
        f"median: {statistics.median(values):.2f} min; "
        f"range: {min(values):.2f}-{max(values):.2f} min"
    )


if __name__ == "__main__":
    main()
