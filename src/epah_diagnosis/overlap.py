from __future__ import annotations

import csv
from pathlib import Path


INDICATORS = {
    "population_65_plus_pct": {
        "benchmark_file": "population_65_plus_benchmarks_2026.csv",
        "label": "ageing",
    },
    "income_vulnerability_pct": {
        "benchmark_file": "income_vulnerability_benchmarks_2024.csv",
        "label": "income",
    },
    "old_building_stock_pct": {
        "benchmark_file": "building_stock_benchmarks_2011.csv",
        "label": "building_stock",
    },
}


def read_green_community_benchmark(path: Path) -> float:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    for row in rows:
        territory = (row.get("territory") or "").casefold()
        if "green community" not in territory:
            continue

        for candidate in (
            "share_65_plus_pct",
            "share_income_le_15000_pct",
            "share_pre_1981_pct",
            "value",
        ):
            value = row.get(candidate)
            if value not in (None, ""):
                return float(value)

        numeric = [
            value
            for key, value in row.items()
            if key.endswith("_pct") and value not in (None, "")
        ]
        if len(numeric) == 1:
            return float(numeric[0])

        raise ValueError(f"Cannot identify benchmark percentage in {path}")

    raise ValueError(f"Green Community benchmark row not found in {path}")


def classify_feature(properties: dict, benchmarks: dict[str, float]) -> dict:
    signals: list[str] = []

    for indicator, metadata in INDICATORS.items():
        value = float(properties[indicator])
        benchmark = float(benchmarks[indicator])
        delta = round(value - benchmark, 2)
        above = value > benchmark

        properties[f"{indicator}_gc_benchmark"] = round(benchmark, 2)
        properties[f"{indicator}_delta_gc_pp"] = delta
        properties[f"{indicator}_above_gc"] = above

        if above:
            signals.append(metadata["label"])

    properties["vulnerability_overlap_count"] = len(signals)
    properties["vulnerability_overlap_dimensions"] = ",".join(signals)
    properties["vulnerability_overlap_method"] = (
        "Count of baseline indicators above their weighted Green Community benchmark"
    )
    properties["vulnerability_overlap_is_energy_poverty_score"] = False

    return properties


def add_overlap_classification(
    geojson: dict,
    benchmarks: dict[str, float],
) -> dict:
    features = geojson.get("features", [])
    if len(features) != 27:
        raise ValueError(f"Expected 27 features, found {len(features)}.")

    for feature in features:
        props = feature.get("properties", {})
        classify_feature(props, benchmarks)

    return geojson
