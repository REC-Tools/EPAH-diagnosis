from __future__ import annotations

import csv
import json
from pathlib import Path


NUMERIC_FIELDS = (
    "population_65_plus_pct",
    "income_vulnerability_pct",
    "old_building_stock_pct",
    "heating_degree_days",
    "mean_altitude_m",
    "dea_access_minutes",
    "upper_secondary_access_minutes",
    "rail_access_minutes",
)

TEXT_FIELDS = (
    "population_65_plus_year",
    "income_vulnerability_year",
    "old_building_stock_year",
    "heating_degree_days_year",
    "mean_altitude_year",
    "snai_class",
    "snai_year",
    "dea_access_year",
    "upper_secondary_access_year",
    "rail_access_year",
)


def load_profiles(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fieldnames = set(reader.fieldnames or [])

    required_fields = {"municipality", *NUMERIC_FIELDS, *TEXT_FIELDS}
    missing_fields = sorted(required_fields - fieldnames)
    if missing_fields:
        raise ValueError(
            "Municipality profile is stale or incomplete. Missing columns: "
            + ", ".join(missing_fields)
            + ". Re-run scripts/build_municipality_profile.py after all "
            "indicator finalizers succeed."
        )

    return {row["municipality"]: row for row in rows}


def enrich_geojson(
    geojson: dict,
    profiles: dict[str, dict[str, str]],
) -> dict:
    features = geojson.get("features", [])
    found: set[str] = set()

    for feature in features:
        props = feature.setdefault("properties", {})
        municipality = props.get("municipality")
        if municipality not in profiles:
            raise ValueError(
                f"Missing municipality profile for {municipality!r}"
            )

        profile = profiles[municipality]

        for field in NUMERIC_FIELDS:
            props[field] = float(profile[field])

        for field in TEXT_FIELDS:
            props[field] = profile[field]

        found.add(municipality)

    missing_geometries = sorted(set(profiles) - found)
    if missing_geometries:
        raise ValueError(
            "Profiles without geometry: " + ", ".join(missing_geometries)
        )

    if len(features) != 27:
        raise ValueError(f"Expected 27 geographic features, found {len(features)}.")

    return geojson


def write_enriched_geojson(
    boundaries_path: Path,
    profiles_path: Path,
    output_path: Path,
) -> dict:
    geojson = json.loads(boundaries_path.read_text(encoding="utf-8"))
    profiles = load_profiles(profiles_path)
    enriched = enrich_geojson(geojson, profiles)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(enriched, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return enriched
