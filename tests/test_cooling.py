from epah_diagnosis.cooling import (
    annual_cdd,
    daily_cdd,
    geometry_contains_point,
)


def test_eurostat_cooling_degree_day_formula():
    assert daily_cdd(23.9) == 0.0
    assert daily_cdd(24.0) == 3.0
    assert daily_cdd(26.0) == 5.0
    assert annual_cdd([20.0, 24.0, 26.0]) == 8.0


def test_polygon_point_membership():
    geometry = {
        "type": "Polygon",
        "coordinates": [[
            [7.0, 45.0],
            [8.0, 45.0],
            [8.0, 46.0],
            [7.0, 46.0],
            [7.0, 45.0],
        ]],
    }

    assert geometry_contains_point(geometry, 7.5, 45.5)
    assert not geometry_contains_point(geometry, 8.5, 45.5)
