from __future__ import annotations

import csv
import json
from pathlib import Path


INDICATORS = (
    "population_65_plus_pct",
    "income_vulnerability_pct",
    "old_building_stock_pct",
)


def load_profiles(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
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
        for field in INDICATORS:
            props[field] = float(profile[field])

        props["population_65_plus_year"] = profile["population_65_plus_year"]
        props["income_vulnerability_year"] = profile["income_vulnerability_year"]
        props["old_building_stock_year"] = profile["old_building_stock_year"]
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
