from __future__ import annotations

import csv
from pathlib import Path


NUMERIC_DIMENSIONS = (
    ("population_65_plus_pct", "rank_population_65_plus"),
    ("income_vulnerability_pct", "rank_income_vulnerability"),
    ("old_building_stock_pct", "rank_old_building_stock"),
    ("heating_degree_days", "rank_heating_degree_days"),
    ("mean_altitude_m", "rank_mean_altitude"),
    ("dea_access_minutes", "rank_dea_access"),
    ("upper_secondary_access_minutes", "rank_upper_secondary_access"),
    ("rail_access_minutes", "rank_rail_access"),
)


def _rank_descending(rows: list[dict[str, str]], field: str) -> dict[str, int]:
    ordered = sorted(
        rows,
        key=lambda row: (-float(row[field]), row["municipality"]),
    )
    return {
        row["municipality"]: index + 1
        for index, row in enumerate(ordered)
    }


def build_comparison_rows(
    profiles: list[dict[str, str]],
) -> list[dict[str, str | int]]:
    if len(profiles) != 27:
        raise ValueError(
            f"Expected 27 municipality profiles, found {len(profiles)}."
        )

    required = {
        "municipality",
        "snai_class",
        *(field for field, _ in NUMERIC_DIMENSIONS),
    }
    missing = sorted(required - set(profiles[0]))
    if missing:
        raise ValueError(
            "Integrated municipality profile is missing columns: "
            + ", ".join(missing)
        )

    rankings = {
        field: _rank_descending(profiles, field)
        for field, _ in NUMERIC_DIMENSIONS
    }

    output: list[dict[str, str | int]] = []
    for profile in sorted(profiles, key=lambda row: row["municipality"]):
        row: dict[str, str | int] = {
            "municipality": profile["municipality"],
            "snai_class": profile["snai_class"],
        }

        for field, rank_field in NUMERIC_DIMENSIONS:
            row[field] = profile[field]
            row[rank_field] = rankings[field][profile["municipality"]]

        output.append(row)

    return output


def load_profiles(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))
