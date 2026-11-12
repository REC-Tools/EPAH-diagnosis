"""Synthetic map validation, labels inside polygons, and nonpublication status."""
from __future__ import annotations

import csv
import json

import pytest
from pyproj import Transformer

from epah_diagnosis.cartography import RENDER_CRS
from epah_diagnosis.municipality_locator_v0_4 import (
    _contains, _project, build, interior_label_point, sha,
)


def fixture(tmp_path):
    base = tmp_path / "inputs"
    base.mkdir()
    registry = base / "municipalities.csv"
    with registry.open("w", newline="", encoding="utf-8") as output:
        writer = csv.writer(output)
        writer.writerow(["municipality", "istat_code"])
        writer.writerows((f"Synthetic {i:02d}", f"001{i:03d}") for i in range(1, 28))
    features = []
    for i in range(1, 28):
        lon = 7 + (i % 6) * 0.08
        lat = 45 + (i // 6) * 0.08
        ring = [[lon, lat], [lon + .07, lat], [lon + .07, lat + .07],
                [lon, lat + .07], [lon, lat]]
        features.append({
            "type": "Feature",
            "properties": {"municipality": f"Synthetic {i:02d}",
                           "municipality_code": f"001{i:03d}"},
            "geometry": {"type": "Polygon", "coordinates": [ring]},
        })
    geometry = {"type": "FeatureCollection",
                "crs": {"type": "name", "properties": {"name": "OGC:CRS84"}},
                "features": features}
    source = base / "municipalities.geojson"
    source.write_text(json.dumps(geometry), encoding="utf-8")
    return source, registry, geometry


def test_locator_a4_has_all_27_names_and_three_formats(tmp_path):
    geo, registry, _ = fixture(tmp_path)
    out = tmp_path / "results" / "locator"
    assert build(geo, registry, out) == out
    for extension in ("png", "svg", "pdf"):
        assert (out / f"municipality_locator.{extension}").stat().st_size > 150
    assert (out / "municipality_locator.png").read_bytes().startswith(b"\x89PNG")
    assert (out / "municipality_locator.pdf").read_bytes().startswith(b"%PDF")
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["outputs_sha256"]["municipality_locator.pdf"] == sha(out / "municipality_locator.pdf")
    meta = json.loads((out / "metadata.json").read_text())
    assert meta["municipalities"] == 27
    assert meta["publication_allowed"] is False
    assert len(meta["legend"]) == 27
    assert {x["municipality_code"] for x in meta["legend"]} == {f"001{i:03d}" for i in range(1, 28)}
    with pytest.raises(FileExistsError):
        build(geo, registry, out)


def test_multipart_anchor_does_not_fall_in_hole(tmp_path):
    _ = tmp_path
    shell = [[7,45], [7.06,45], [7.06,45.06], [7,45.06], [7,45]]
    hole = [[7.018,45.018], [7.042,45.018], [7.042,45.042],
            [7.018,45.042], [7.018,45.018]]
    island = [[7.2,45.2], [7.21,45.2], [7.21,45.21], [7.2,45.21], [7.2,45.2]]
    geom = {"type": "MultiPolygon", "coordinates": [[shell, hole], [island]]}
    transformer = Transformer.from_crs("EPSG:4326", RENDER_CRS, always_xy=True)
    anchor = interior_label_point(geom, transformer)
    projected = _project([shell, hole], transformer)
    assert _contains(anchor, projected)
    assert not _contains(anchor, [_project([hole], transformer)[0]])


def test_locator_rejects_mismatched_registry_crs_or_incomplete_scope(tmp_path):
    source, registry, geometry = fixture(tmp_path)
    geometry["features"].pop()
    source.write_text(json.dumps(geometry))
    with pytest.raises(ValueError, match="27"):
        build(source, registry, tmp_path / "blocked")
    assert not (tmp_path / "blocked").exists()
    source, registry, geometry = fixture(tmp_path / "other")
    geometry["crs"]["properties"]["name"] = "EPSG:3857"
    source.write_text(json.dumps(geometry))
    with pytest.raises(ValueError, match="WGS84"):
        build(source, registry, tmp_path / "blocked2")


def test_locator_rejects_input_nested_output(tmp_path):
    source, registry, _ = fixture(tmp_path)
    with pytest.raises(ValueError, match="outside input"):
        build(source, registry, source.parent / "output")
