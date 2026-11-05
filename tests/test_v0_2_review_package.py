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

def _rehash_artifact(manifest_path: Path, file: Path, key: str) -> None:
    """Simulate someone regenerating the local SHA-256 manifest after an edit."""
    from epah_diagnosis.release_artifacts import sha256_file
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["artifacts"][key]["sha256"] = sha256_file(file)
    manifest["artifacts"][key]["bytes"] = file.stat().st_size
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")


def test_rehashed_but_false_report_facts_are_blocked(pipeline, tmp_path):
    inputs, pilot, report, sheets, analysis, dashboard = pipeline
    forged = tmp_path / "forged-report"
    shutil.copytree(report, forged)
    fact_file = forged / "diagnostic_facts_v0_2.json"
    facts = json.loads(fact_file.read_text(encoding="utf-8"))
    facts["indicators"]["old_building_stock_pct"]["median"] = 999
    fact_file.write_text(json.dumps(facts), encoding="utf-8")
    _rehash_artifact(
        forged / "report_manifest_v0_2.json", fact_file, fact_file.name,
    )
    with pytest.raises(ValueError, match="facts or map/profile provenance"):
        build(pilot, forged, sheets, analysis, dashboard,
              tmp_path / "never-forged-facts",
              inputs["municipality_file"], inputs["release_config"])


def test_rehashed_but_modified_dashboard_values_are_blocked(pipeline, tmp_path):
    inputs, pilot, report, sheets, analysis, dashboard = pipeline
    forged = tmp_path / "forged-dashboard"
    shutil.copytree(dashboard, forged)
    data_file = forged / "dashboard_data_v0_2.json"
    data = json.loads(data_file.read_text(encoding="utf-8"))
    data["municipalities"][0]["values"]["income_vulnerability_pct"]["value"] = 99
    data_file.write_text(json.dumps(data), encoding="utf-8")
    _rehash_artifact(
        forged / "dashboard_manifest_v0_2.json", data_file, data_file.name,
    )
    with pytest.raises(ValueError, match="Dashboard values/years/pair counts"):
        build(pilot, report, sheets, analysis, forged,
              tmp_path / "never-forged-dashboard",
              inputs["municipality_file"], inputs["release_config"])


def test_rehashed_but_modified_dashboard_html_is_blocked(pipeline, tmp_path):
    inputs, pilot, report, sheets, analysis, dashboard = pipeline
    forged = tmp_path / "forged-html"
    shutil.copytree(dashboard, forged)
    html_file = forged / "index.html"
    original = html_file.read_text(encoding="utf-8")
    html_file.write_text(original.replace("Diagnosi territoriale - 27 Comuni",
                                          "Diagnosi territoriale non verificata"),
                         encoding="utf-8")
    _rehash_artifact(
        forged / "dashboard_manifest_v0_2.json", html_file, html_file.name,
    )
    with pytest.raises(ValueError, match="Dashboard HTML differs"):
        build(pilot, report, sheets, analysis, forged,
              tmp_path / "never-forged-html",
              inputs["municipality_file"], inputs["release_config"])


def test_postbuild_verifier_is_readonly_and_detects_zip_mutations(pipeline, tmp_path):
    from epah_diagnosis.review_package_v0_2 import verify_review_package
    inputs, pilot, report, sheets, analysis, dashboard = pipeline
    output = build(pilot, report, sheets, analysis, dashboard,
                   tmp_path / "review-to-verify",
                   inputs["municipality_file"], inputs["release_config"])
    archive = output / "v0_2_technical_review_only.zip"
    original = archive.read_bytes()
    checked = verify_review_package(output)
    assert checked["publication_authorized"] is False
    assert checked["verified_files"] >= 35
    assert archive.read_bytes() == original
    # Adding an unexpected member to an otherwise valid ZIP is rejected.
    with zipfile.ZipFile(archive, "a") as zip_out:
        zip_out.writestr("review/UNEXPECTED.txt", "not an approved review artifact")
    with pytest.raises(ValueError, match="Review ZIP"):
        verify_review_package(output)


def test_postbuild_verifier_refuses_changed_human_approval_gate(pipeline, tmp_path):
    from epah_diagnosis.review_package_v0_2 import verify_review_package
    inputs, pilot, report, sheets, analysis, dashboard = pipeline
    output = build(pilot, report, sheets, analysis, dashboard,
                   tmp_path / "review-checklist",
                   inputs["municipality_file"], inputs["release_config"])
    checklist_file = output / "editorial_review_checklist.json"
    checklist = json.loads(checklist_file.read_text(encoding="utf-8"))
    checklist["publication_authorized"] = True
    checklist_file.write_text(json.dumps(checklist), encoding="utf-8")
    with pytest.raises(ValueError, match="Review publication gates"):
        verify_review_package(output)

