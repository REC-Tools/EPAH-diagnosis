"""End-to-end synthetic v0.2 review pack; no automatic publication."""
from __future__ import annotations

import importlib.util
import json
import shutil
import zipfile
from pathlib import Path

import pytest

from test_release_bundle import _make_fixture, bundle
from epah_diagnosis.review_package_v0_2 import build

ROOT = Path(__file__).resolve().parents[1]


def load_script(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/"scripts"/(name+".py"))
    assert spec and spec.loader
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


REPORT=load_script("build_v0_2_territorial_report")
SHEETS=load_script("build_v0_2_municipality_sheets")
ANALYSIS=load_script("build_v0_2_multidimensional_analysis")
DASH=load_script("build_v0_2_dashboard")


@pytest.fixture(scope="module")
def pipeline(tmp_path_factory):
    root=tmp_path_factory.mktemp("v02-pack")
    inputs=_make_fixture(root)
    pilot=bundle.build_bundle(**inputs)
    r=REPORT.build_report(pilot,root/"report",inputs["municipality_file"],inputs["release_config"])
    s=SHEETS.build(pilot,root/"sheets",inputs["municipality_file"],inputs["release_config"])
    a=ANALYSIS.build(pilot,root/"analysis",inputs["municipality_file"],inputs["release_config"])
    d=DASH.build(a,pilot,root/"dashboard",inputs["municipality_file"],inputs["release_config"])
    return inputs,pilot,r,s,a,d


def test_complete_review_candidate_preserves_all_manual_review_gates(pipeline,tmp_path):
    inputs,pilot,r,s,a,d=pipeline
    out=build(pilot,r,s,a,d,tmp_path/"candidate",
              inputs["municipality_file"],inputs["release_config"])
    summary=json.loads((out/"qa_summary_v0_2.json").read_text())
    checklist=json.loads((out/"editorial_review_checklist.json").read_text())
    manifest=json.loads((out/"review_package_manifest_v0_2.json").read_text())
    assert summary["status"]=="technical_review_candidate_not_authorized_for_publication"
    assert summary["municipalities"]==27 and summary["core_indicators"]==9
    assert summary["cit_included"] is False
    assert summary["human_signoff"]=="pending"
    assert not checklist["publication_authorized"]
    assert all(s["status"]=="pending"
               for s in checklist["required_human_checks"].values())
    assert len(list((out/"sheets/municipalities").glob("*.pdf")))==27
    assert (out/"report/diagnostic_report_v0_2_technical.pdf").is_file()
    assert (out/"dashboard/index.html").is_file()
    assert "review_package_manifest_v0_2.json" not in manifest["artifacts"]
    with zipfile.ZipFile(out/"v0_2_technical_review_only.zip") as z:
        assert z.testzip() is None
        assert "review/README_REVIEW.md" in z.namelist()
        assert "review/editorial_review_checklist.json" in z.namelist()
        assert "review/v0_2_technical_review_only.zip" not in z.namelist()
        assert all(not x.startswith("/") and ".." not in Path(x).parts
                   for x in z.namelist())


def test_source_tampering_refuses_all_output(pipeline,tmp_path):
    inputs,pilot,r,s,a,d=pipeline
    copy=tmp_path/"tampered-dashboard"
    shutil.copytree(d,copy)
    page=copy/"index.html"
    page.write_text(page.read_text(encoding="utf-8")+"MODIFIED",encoding="utf-8")
    out=tmp_path/"should-not-exist"
    with pytest.raises(ValueError,match="SHA-256 mismatch"):
        build(pilot,r,s,a,copy,out,inputs["municipality_file"],inputs["release_config"])
    assert not out.exists()


def test_existing_output_is_preserved(pipeline,tmp_path):
    inputs,pilot,r,s,a,d=pipeline
    out=tmp_path/"existing"
    out.mkdir()
    marker=out/"do-not-remove"
    marker.write_text("preserve")
    with pytest.raises(FileExistsError):
        build(pilot,r,s,a,d,out,inputs["municipality_file"],inputs["release_config"])
    assert marker.read_text()=="preserve"
