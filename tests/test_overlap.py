from epah_diagnosis.overlap import add_overlap_classification


def test_overlap_counts_dimensions_above_benchmark():
    features = []

    for index in range(27):
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "municipality": f"Comune {index:02d}",
                    "population_65_plus_pct": 30.0,
                    "income_vulnerability_pct": 20.0,
                    "old_building_stock_pct": 80.0,
                },
                "geometry": {"type": "Polygon", "coordinates": []},
            }
        )

    geojson = {"type": "FeatureCollection", "features": features}
    benchmarks = {
        "population_65_plus_pct": 28.0,
        "income_vulnerability_pct": 25.0,
        "old_building_stock_pct": 70.0,
    }

    result = add_overlap_classification(geojson, benchmarks)
    props = result["features"][0]["properties"]

    assert props["vulnerability_overlap_count"] == 2
    assert props["population_65_plus_pct_above_gc"] is True
    assert props["income_vulnerability_pct_above_gc"] is False
    assert props["old_building_stock_pct_above_gc"] is True
    assert props["vulnerability_overlap_is_energy_poverty_score"] is False
