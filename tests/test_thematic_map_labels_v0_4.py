"""v0.4 map labels identify a few large geographic polygons, not high values."""
from __future__ import annotations

import copy

import matplotlib
matplotlib.use("Agg")
import pytest
from pyproj import Transformer

from epah_diagnosis.thematic_map_labels_v0_4 import (
    MAX_LABELS, polygon_area_m2, render_thematic_map, select_map_labels,
)
from test_v0_3_visual_atlas import mod as old_atlas


def geography():
    features = []
    for i in range(27):
        code = f"001{i+1:03d}"
        col, row = i % 9, i // 9
        x, y = 7.0 + col * .10, 45.0 + row * .12
        side = .042 if i != 26 else .09
        shell = [[x, y], [x + side, y], [x + side, y + side],
                 [x, y + side], [x, y]]
        features.append({
            "type": "Feature",
            "properties": {"municipality": f"Synthetic Municipality {i+1:02d}",
                           "municipality_code": code},
            "geometry": {"type": "Polygon", "coordinates": [shell]},
        })
    return {"type": "FeatureCollection",
            "crs": {"type": "name", "properties": {"name": "OGC:CRS84"}},
            "features": features}


def test_five_largest_polygons_selected_without_indicator_data():
    geo = geography()
    selected = select_map_labels(geo)
    assert len(selected) == MAX_LABELS == 5
    assert selected[0].code == "001027"
    assert [x.polygon_area_m2 for x in selected] == sorted(
        [x.polygon_area_m2 for x in selected], reverse=True)
    assert all(x.polygon_area_m2 > 0 for x in selected)
    assert selected == select_map_labels(copy.deepcopy(geo))
    reversed_geo = copy.deepcopy(geo)
    reversed_geo["features"].reverse()
    assert selected == select_map_labels(reversed_geo)
    assert len(set(x.code for x in selected)) == len(selected)


def test_polygon_area_excludes_holes_and_includes_multipart():
    geo = geography()
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:32632", always_xy=True)
    square = geo["features"][0]["geometry"]
    orig = polygon_area_m2(square, transformer)
    x, y = 7, 45
    hole = [[x+.01,y+.01],[x+.03,y+.01],[x+.03,y+.03],
            [x+.01,y+.03],[x+.01,y+.01]]
    with_hole = {"type": "Polygon", "coordinates": [square["coordinates"][0], hole]}
    assert 0 < polygon_area_m2(with_hole, transformer) < orig
    island = [[x+.06,y+.06],[x+.07,y+.06],[x+.07,y+.07],
              [x+.06,y+.07],[x+.06,y+.06]]
    multipart = {"type": "MultiPolygon",
                 "coordinates": [with_hole["coordinates"], [island]]}
    assert polygon_area_m2(multipart, transformer) > polygon_area_m2(with_hole, transformer)


def test_numeric_and_categorical_maps_render_sparse_labels(tmp_path):
    geo = geography()
    labels = select_map_labels(geo)
    for metric, values in (
        (old_atlas.BASE[0], {
            feature["properties"]["municipality_code"]: {"value": float(i * 30), "year": "2024"}
            for i, feature in enumerate(geo["features"])
        }),
        (old_atlas.BASE[-1], {
            feature["properties"]["municipality_code"]: {"value": "ABCDEF"[i % 6], "year": "2020"}
            for i, feature in enumerate(geo["features"])
        }),
    ):
        shown_per_fmt = {}
        for fmt in ("png", "svg"):
            file = tmp_path / f"{metric.id}_map.{fmt}"
            shown = render_thematic_map(geo, metric, values, file, fmt, labels)
            assert file.stat().st_size > 200
            assert set(shown) <= {label.code for label in labels}
            assert 0 < len(shown) <= MAX_LABELS
            shown_per_fmt[fmt] = shown
        assert shown_per_fmt["png"] == shown_per_fmt["svg"]


def test_no_labels_for_missing_data_or_unknown_geography(tmp_path):
    geo = geography()
    labels = select_map_labels(geo, max_labels=0)
    assert labels == []
    with pytest.raises(ValueError, match="No mapped observations"):
        render_thematic_map(geo, old_atlas.BASE[0], {}, tmp_path / "x.png", "png", labels)
    geo["features"].pop()
    with pytest.raises(ValueError, match="27 municipalities"):
        select_map_labels(geo)
