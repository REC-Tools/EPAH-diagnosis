from epah_diagnosis.municipality_profile import build_profiles


def _row(municipality, indicator_id, value, year, status="Dato validato"):
    return {
        "municipality": municipality,
        "indicator_id": indicator_id,
        "status": status,
        "value": str(value),
        "year": str(year),
    }


def test_build_profiles_requires_integrated_validated_indicators():
    all_rows = []
    for index in range(27):
        municipality = f"Comune {index:02d}"
        all_rows.extend(
            [
                _row(municipality, "population_65_plus", 30.0, 2026),
                _row(municipality, "income_vulnerability", 25.0, 2024),
                _row(municipality, "old_building_stock", 70.0, 2011),
                _row(municipality, "heating_degree_days", 3200, "normativo"),
                _row(municipality, "mean_altitude", 800, 2021),
                _row(municipality, "snai_isolation_class", "E", 2020),
                _row(municipality, "dea_access_minutes", 35.0, "2021/2025"),
                _row(
                    municipality,
                    "upper_secondary_access_minutes",
                    28.0,
                    "2024/25 + 2021",
                ),
                _row(municipality, "rail_access_minutes", 22.0, "2026 + 2021"),
            ]
        )

    profiles = build_profiles(all_rows)

    assert len(profiles) == 27
    first = profiles[0]
    assert first["population_65_plus_pct"] == 30.0
    assert first["heating_degree_days"] == 3200.0
    assert first["mean_altitude_m"] == 800.0
    assert first["snai_class"] == "E"
    assert first["dea_access_minutes"] == 35.0
    assert first["upper_secondary_access_minutes"] == 28.0
    assert first["rail_access_minutes"] == 22.0
