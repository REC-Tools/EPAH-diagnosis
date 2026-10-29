"""Synthetic data-join integrity regression tests."""
from __future__ import annotations
import copy
import pytest
from epah_diagnosis.mapping import NUMERIC_FIELDS, TEXT_FIELDS, enrich_geojson

def fixture():
    profiles={}
    features=[]
    for i in range(27):
        name=f"Comune {i:02d}"
        profiles[name]={"municipality":name,**{f:"12.5" for f in NUMERIC_FIELDS},**{f:"2026" for f in TEXT_FIELDS}}
        features.append({"type":"Feature","properties":{"municipality":name},"geometry":{"type":"Polygon","coordinates":[]}})
    return {"type":"FeatureCollection","features":features},profiles

def test_join_preserves_input():
    geo,profiles=fixture()
    original=copy.deepcopy(geo)
    result=enrich_geojson(geo,profiles)
    assert result is not geo and geo==original
    assert result["features"][0]["properties"]["mean_altitude_m"]==12.5

def test_duplicate_geometry_rejected():
    geo,profiles=fixture()
    geo["features"][1]["properties"]["municipality"]="Comune 00"
    with pytest.raises(ValueError,match="Duplicate municipality"):
        enrich_geojson(geo,profiles)

def test_nonfinite_indicator_rejected():
    geo,profiles=fixture()
    profiles["Comune 00"]["mean_altitude_m"]="nan"
    with pytest.raises(ValueError,match="Invalid numeric"):
        enrich_geojson(geo,profiles)
