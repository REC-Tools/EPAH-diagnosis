from __future__ import annotations


NUMERIC_INDICATORS = {
    "population_65_plus": ("population_65_plus_pct", "population_65_plus_year"),
    "income_vulnerability": ("income_vulnerability_pct", "income_vulnerability_year"),
    "old_building_stock": ("old_building_stock_pct", "old_building_stock_year"),
    "heating_degree_days": ("heating_degree_days", "heating_degree_days_year"),
    "mean_altitude": ("mean_altitude_m", "mean_altitude_year"),
    "dea_accessibility": ("dea_access_minutes", "dea_access_year"),
    "upper_secondary_accessibility": (
        "upper_secondary_access_minutes",
        "upper_secondary_access_year",
    ),
    "rail_accessibility": ("rail_access_minutes", "rail_access_year"),
}

CATEGORICAL_INDICATORS = {
    "snai_classification": ("snai_class", "snai_year"),
}

REQUIRED_INDICATORS = tuple(NUMERIC_INDICATORS) + tuple(CATEGORICAL_INDICATORS)


def _to_float(value: str, municipality: str, indicator_id: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Invalid numeric value for {municipality}/{indicator_id}: {value!r}"
        ) from exc


def build_profiles(rows: list[dict[str, str]]) -> list[dict[str, str | float]]:
    by_municipality: dict[str, dict[str, dict[str, str]]] = {}

    for row in rows:
        municipality = row["municipality"].strip()
        indicator_id = row["indicator_id"].strip()
        if indicator_id not in REQUIRED_INDICATORS:
            continue
        by_municipality.setdefault(municipality, {})[indicator_id] = row

    profiles: list[dict[str, str | float]] = []
    errors: list[str] = []

    for municipality in sorted(by_municipality):
        indicator_rows = by_municipality[municipality]

        missing = [
            indicator_id
            for indicator_id in REQUIRED_INDICATORS
            if indicator_id not in indicator_rows
        ]
        if missing:
            errors.append(
                f"{municipality}: missing indicators {', '.join(missing)}"
            )
            continue

        not_validated = [
            indicator_id
            for indicator_id in REQUIRED_INDICATORS
            if indicator_rows[indicator_id]["status"].strip() != "Dato validato"
        ]
        if not_validated:
            errors.append(
                f"{municipality}: not validated {', '.join(not_validated)}"
            )
            continue

        profile: dict[str, str | float] = {"municipality": municipality}

        for indicator_id, (value_field, year_field) in NUMERIC_INDICATORS.items():
            row = indicator_rows[indicator_id]
            profile[value_field] = _to_float(
                row["value"], municipality, indicator_id
            )
            profile[year_field] = row["year"]

        for indicator_id, (value_field, year_field) in CATEGORICAL_INDICATORS.items():
            row = indicator_rows[indicator_id]
            profile[value_field] = row["value"].strip()
            profile[year_field] = row["year"]

        profiles.append(profile)

    if errors:
        preview = "\n".join(f"- {error}" for error in errors[:20])
        remainder = len(errors) - 20
        if remainder > 0:
            preview += f"\n- ... and {remainder} more"
        raise ValueError(
            "Integrated municipality profile cannot be built until all required "
            f"indicators are validated for every municipality:\n{preview}"
        )

    if len(profiles) != 27:
        raise ValueError(
            f"Expected 27 complete municipality profiles, found {len(profiles)}."
        )

    return profiles
