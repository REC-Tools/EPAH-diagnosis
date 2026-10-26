from __future__ import annotations


REQUIRED_INDICATORS = (
    "population_65_plus",
    "income_vulnerability",
    "old_building_stock",
)


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

        population = indicator_rows["population_65_plus"]
        income = indicator_rows["income_vulnerability"]
        buildings = indicator_rows["old_building_stock"]

        profiles.append(
            {
                "municipality": municipality,
                "population_65_plus_pct": _to_float(
                    population["value"], municipality, "population_65_plus"
                ),
                "population_65_plus_year": population["year"],
                "income_vulnerability_pct": _to_float(
                    income["value"], municipality, "income_vulnerability"
                ),
                "income_vulnerability_year": income["year"],
                "old_building_stock_pct": _to_float(
                    buildings["value"], municipality, "old_building_stock"
                ),
                "old_building_stock_year": buildings["year"],
            }
        )

    if errors:
        preview = "\n".join(f"- {error}" for error in errors[:20])
        remainder = len(errors) - 20
        if remainder > 0:
            preview += f"\n- ... and {remainder} more"
        raise ValueError(
            "Municipality profile cannot be built until all three indicators "
            f"are validated for every municipality:\n{preview}"
        )

    if len(profiles) != 27:
        raise ValueError(
            f"Expected 27 complete municipality profiles, found {len(profiles)}."
        )

    return profiles
