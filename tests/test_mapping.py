from epah_diagnosis.mapping import enrich_geojson


def test_enrich_geojson_adds_integrated_indicators():
    features = []
    profiles = {}

    for index in range(27):
        name = f"Comune {index:02d}"
        features.append(
            {
                "type": "Feature",
                "properties": {"municipality": name},
                "geometry": {"type": "Polygon", "coordinates": []},
            }
        )
        profiles[name] = {
            "municipality": name,
            "population_65_plus_pct": "30.0",
            "population_65_plus_year": "2026",
            "income_vulnerability_pct": "25.0",
            "income_vulnerability_year": "2024",
            "old_building_stock_pct": "70.0",
            "old_building_stock_year": "2011",
            "heating_degree_days": "3200",
            "heating_degree_days_year": "normativo",
            "mean_altitude_m": "800",
            "mean_altitude_year": "2021",
            "snai_class": "E",
            "snai_year": "2020",
            "dea_access_minutes": "35",
            "dea_access_year": "2021/2025",
            "upper_secondary_access_minutes": "28",
            "upper_secondary_access_year": "2024/25 + 2021",
            "rail_access_minutes": "22",
            "rail_access_year": "2026 + 2021",
        }

    result = enrich_geojson(
        {"type": "FeatureCollection", "features": features},
        profiles,
    )

    props = result["features"][0]["properties"]
    assert props["population_65_plus_pct"] == 30.0
    assert props["heating_degree_days"] == 3200.0
    assert props["mean_altitude_m"] == 800.0
    assert props["snai_class"] == "E"
    assert props["dea_access_minutes"] == 35.0
    assert props["upper_secondary_access_minutes"] == 28.0
    assert props["rail_access_minutes"] == 22.0
