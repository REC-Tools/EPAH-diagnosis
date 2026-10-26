from epah_diagnosis.comparison import build_comparison_rows


def test_build_comparison_rows_ranks_each_dimension_without_total_score():
    profiles = []
    for index in range(27):
        value = float(index + 1)
        profiles.append(
            {
                "municipality": f"Comune {index:02d}",
                "snai_class": "E",
                "population_65_plus_pct": str(value),
                "income_vulnerability_pct": str(value),
                "old_building_stock_pct": str(value),
                "heating_degree_days": str(value),
                "mean_altitude_m": str(value),
                "dea_access_minutes": str(value),
                "upper_secondary_access_minutes": str(value),
                "rail_access_minutes": str(value),
            }
        )

    rows = build_comparison_rows(profiles)

    assert len(rows) == 27
    highest = next(row for row in rows if row["municipality"] == "Comune 26")
    lowest = next(row for row in rows if row["municipality"] == "Comune 00")

    assert highest["rank_population_65_plus"] == 1
    assert highest["rank_rail_access"] == 1
    assert lowest["rank_population_65_plus"] == 27
    assert "overall_score" not in highest
    assert "total_rank" not in highest
