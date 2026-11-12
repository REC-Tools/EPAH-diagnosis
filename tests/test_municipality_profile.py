from epah_diagnosis.municipality_profile import build_profiles
import pytest


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
                _row(municipality, "snai_classification", "E", 2020),
                _row(municipality, "dea_accessibility", 35.0, "2021/2025"),
                _row(
                    municipality,
                    "upper_secondary_accessibility",
                    28.0,
                    "2024/25 + 2021",
                ),
                _row(municipality, "rail_accessibility", 22.0, "2026 + 2021"),
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


def test_profile_uses_canonical_catalog_ids():
    from epah_diagnosis.municipality_profile import REQUIRED_INDICATORS

    assert set(REQUIRED_INDICATORS) == {
        "population_65_plus", "income_vulnerability", "old_building_stock",
        "heating_degree_days", "mean_altitude", "snai_classification",
        "dea_accessibility", "upper_secondary_accessibility", "rail_accessibility",
    }


def test_profile_rejects_duplicate_indicator_even_if_last_row_is_validated():
    rows = _complete_rows()
    rows.insert(0, _row("Comune 00", "population_65_plus", 99, 2026, "Da verificare"))
    with pytest.raises(ValueError, match="Duplicate"):
        build_profiles(rows)


@pytest.mark.parametrize("value", ["nan", "inf", "-inf", "1e999"])
def test_profile_rejects_nonfinite_values(value):
    rows = _complete_rows()
    rows[0]["value"] = value
    with pytest.raises(ValueError, match="Invalid numeric"):
        build_profiles(rows)


def _complete_rows():
    from epah_diagnosis.municipality_profile import REQUIRED_INDICATORS
    return [_row(f"Comune {index:02d}", indicator,
                 "E" if indicator == "snai_classification" else 30, 2026)
            for index in range(27) for indicator in REQUIRED_INDICATORS]
