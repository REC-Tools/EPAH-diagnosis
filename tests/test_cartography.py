"""Synthetic map tests; no municipality observations are implied."""
from __future__ import annotations
import copy
import matplotlib
matplotlib.use("Agg")
from matplotlib.axes import Axes
from matplotlib.patches import PathPatch
from pyproj import Transformer
import pytest
from epah_diagnosis.cartography import (
    INPUT_CRS, RENDER_CRS, _oriented_polygon_path, _ring_area,
    render_thematic_map,
)

def sample():
    ring = [[7.2,45.1],[7.3,45.1],[7.3,45.2],[7.2,45.2],[7.2,45.1]]
    hole = [[7.22,45.12],[7.28,45.12],[7.28,45.18],[7.22,45.18],[7.22,45.12]]
    return {"type":"FeatureCollection","crs":{"type":"name","properties":{"name":"urn:ogc:def:crs:OGC:1.3:CRS84"}},"features":[{"type":"Feature","properties":{"value":12.5,"class":"D"},"geometry":{"type":"Polygon","coordinates":[ring,hole]}}]}

def test_lat_lon_degrees_do_not_correspond_to_equal_distances():
    t=Transformer.from_crs(INPUT_CRS, RENDER_CRS, always_xy=True)
    x,y=t.transform(7.2,45.1)
    x2,y2=t.transform(7.3,45.1)
    x3,y3=t.transform(7.2,45.2)
    horizontal=((x2-x)**2+(y2-y)**2)**.5
    vertical=((x3-x)**2+(y3-y)**2)**.5
    assert 7000<horizontal<9000 and 10000<vertical<12000

def test_png_contains_projected_geometry_but_geojson_is_unchanged(tmp_path, monkeypatch):
    geo=sample()
    before=copy.deepcopy(geo)
    seen=[]
    add=Axes.add_patch
    def capture(self, patch):
        if isinstance(patch,PathPatch):
            seen.extend(patch.get_path().vertices.tolist())
        return add(self,patch)
    monkeypatch.setattr(Axes,"add_patch",capture)
    output=tmp_path/"map.png"
    render_thematic_map(geo,"value","Test","%",output)
    assert output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert min(p[0] for p in seen)>100000 and min(p[1] for p in seen)>4000000
    assert geo==before

def test_holes_preserved_after_utm_projection():
    geo=sample()
    t=Transformer.from_crs(INPUT_CRS,RENDER_CRS,always_xy=True)
    path=_oriented_polygon_path(geo["features"][0]["geometry"]["coordinates"],t)
    assert _ring_area(path.vertices[:5])>0
    assert _ring_area(path.vertices[5:])<0

def test_categorical_and_invalid_crs(tmp_path):
    geo=sample()
    out=tmp_path/"cat.png"
    render_thematic_map(geo,"class","SNAI","class",out,category_colors={"D":"#123456"})
    assert out.is_file()
    wrong=copy.deepcopy(geo)
    wrong["crs"]["properties"]["name"]="EPSG:32632"
    with pytest.raises(ValueError,match="WGS84/CRS84"):
        render_thematic_map(wrong,"value","Test","%",tmp_path/"invalid.png")

def test_mislabelled_projected_coordinates_rejected(tmp_path):
    geo=sample()
    geo["features"][0]["geometry"]["coordinates"][0][0]=[400000,5000000]
    with pytest.raises(ValueError,match="Invalid or non-geographic"):
        render_thematic_map(geo,"value","Test","%",tmp_path/"invalid.png")
