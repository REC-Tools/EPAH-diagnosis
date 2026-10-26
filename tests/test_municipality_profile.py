from epah_diagnosis.municipality_profile import build_profiles


def _row(municipality, indicator_id, value, year, status="Dato validato"):
    return {
        "municipality": municipality,
        "indicator_id": indicator_id,
        "status": status,
        "value": str(value),
        "year": str(year),
    }


def test_build_profiles_requires_three_validated_indicators():
    all_rows = []
    for index in range(27):
        municipality = f"Comune {index:02d}"
        all_rows.extend(
            [
                _row(municipality, "population_65_plus", 30.0, 2026),
                _row(municipality, "income_vulnerability", 25.0, 2024),
                _row(municipality, "old_building_stock", 70.0, 2011),
            ]
        )

    profiles = build_profiles(all_rows)

    assert len(profiles) == 27
    assert profiles[0]["population_65_plus_pct"] == 30.0
    assert profiles[0]["income_vulnerability_pct"] == 25.0
    assert profiles[0]["old_building_stock_pct"] == 70.0
