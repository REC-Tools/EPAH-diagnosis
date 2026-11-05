"""Offline dashboard QA from a complete synthetic 27-town pilot/analysis."""
from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path

import pytest

from test_release_bundle import _make_fixture, bundle
from epah_diagnosis.dashboard_v0_2 import document
from epah_diagnosis.release_artifacts import sha256_file

ROOT = Path(__file__).resolve().parents[1]


def load_script(filename):
    spec=importlib.util.spec_from_file_location(filename.replace(".py",""),
           ROOT / "scripts" / filename)
    assert spec and spec.loader
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ANALYSIS=load_script("build_v0_2_multidimensional_analysis.py")
DASH=load_script("build_v0_2_dashboard.py")


@pytest.fixture(scope="module")
def inputs(tmp_path_factory):
    root=tmp_path_factory.mktemp("v02-dash")
    fixture=_make_fixture(root)
    pilot=bundle.build_bundle(**fixture)
    analysis=ANALYSIS.build(pilot, root / "analysis",
                            fixture["municipality_file"], fixture["release_config"])
    return fixture, pilot, analysis


def test_dashboard_is_standalone_hashed_and_27_town(inputs, tmp_path):
    fixture,pilot,analysis=inputs
    out=DASH.build(analysis,pilot,tmp_path/"dashboard",
                   fixture["municipality_file"],fixture["release_config"])
    html=(out/"index.html").read_text(encoding="utf-8")
    manifest=json.loads((out/"dashboard_manifest_v0_2.json").read_text())
    data=json.loads((out/"dashboard_data_v0_2.json").read_text())
    assert len(data["municipalities"])==27
    assert len(data["pairs"])==28
    assert data["no_composite_score"] is True
    assert manifest["offline_only"] is True
    assert manifest["status"]=="technical_draft_do_not_publish"
    assert "NON PUBBLICARE" in html
    assert "id=\"municipalities\"" in html
    assert "id=\"search\"" in html
    assert "https://" not in html and "fetch(" not in html and "<script src=" not in html
    assert manifest["artifacts"]["index.html"]["sha256"]==sha256_file(out/"index.html")


def test_embedded_json_prevents_script_tag_breakout():
    html=document({"status":"technical_draft_do_not_publish",
                   "name":"</script><script>alert(1)</script>"})
    assert "</script><script>alert(1)</script>" not in html
    assert "\\u003c/script\\u003e" in html


def test_modified_analysis_or_existing_output_blocks(inputs,tmp_path):
    fixture,pilot,analysis=inputs
    modified=tmp_path/"bad-analysis"
    shutil.copytree(analysis,modified)
    file=modified/"municipality_comparison_v0_2.csv"
    file.write_bytes(file.read_bytes().replace(b"21.0000",b"99.0000",1))
    out=tmp_path/"bad-dest"
    with pytest.raises(ValueError):
        DASH.build(modified,pilot,out,
                   fixture["municipality_file"],fixture["release_config"])
    assert not out.exists()
    out.mkdir()
    with pytest.raises(FileExistsError):
        DASH.build(analysis,pilot,out,
                   fixture["municipality_file"],fixture["release_config"])
