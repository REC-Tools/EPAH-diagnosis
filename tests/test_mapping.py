from epah_diagnosis.mapping import enrich_geojson


def test_enrich_geojson_adds_three_indicators():
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
        }

    result = enrich_geojson(
        {"type": "FeatureCollection", "features": features},
        profiles,
    )

    props = result["features"][0]["properties"]
    assert props["population_65_plus_pct"] == 30.0
    assert props["income_vulnerability_pct"] == 25.0
    assert props["old_building_stock_pct"] == 70.0
