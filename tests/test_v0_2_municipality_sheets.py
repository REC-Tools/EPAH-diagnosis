"""Synthetic QA of 27 one-page municipal PDF profiles."""
from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path

import pytest
from pypdf import PdfReader

from test_release_bundle import _make_fixture, bundle
from epah_diagnosis.release_artifacts import sha256_file

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "sheet_builder", ROOT / "scripts/build_v0_2_municipality_sheets.py"
)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


@pytest.fixture(scope="module")
def synthetic_bundle(tmp_path_factory):
    inputs = _make_fixture(tmp_path_factory.mktemp("v02-sheets"))
    return inputs, bundle.build_bundle(**inputs)


def test_all_municipal_sheets_are_single_page_and_hashed(synthetic_bundle, tmp_path):
    inputs, source = synthetic_bundle
    out = MOD.build(source, tmp_path / "new-sheets",
                    inputs["municipality_file"], inputs["release_config"])
    index = json.loads((out / "sheets_index_v0_2.json").read_text())
    assert index["status"] == "technical_draft_do_not_publish"
    assert index["municipalities"] == 27
    assert index["no_composite_score"] is True
    assert len(index["sheets"]) == 27
    for entry in index["sheets"]:
        pdf = out / entry["path"]
        assert pdf.is_file()
        assert sha256_file(pdf) == entry["sha256"]
        reader = PdfReader(str(pdf))
        assert len(reader.pages) == 1
        text = reader.pages[0].extract_text()
        assert entry["istat_code"] in text
        assert "NON PUBBLICARE" in text


def test_output_collision_does_not_replace_evidence(synthetic_bundle, tmp_path):
    inputs, source = synthetic_bundle
    out = tmp_path / "already-exists"
    out.mkdir()
    (out / "marker").write_text("immutable")
    with pytest.raises(FileExistsError):
        MOD.build(source, out, inputs["municipality_file"], inputs["release_config"])
    assert (out / "marker").read_text() == "immutable"


def test_tampered_profile_never_gets_exported(synthetic_bundle, tmp_path):
    inputs, source = synthetic_bundle
    copy = tmp_path / "tampered-source"
    shutil.copytree(source, copy)
    path = copy / "municipality_profile.csv"
    path.write_bytes(path.read_bytes().replace(b"21", b"99", 1))
    dest = tmp_path / "should-not-exist"
    with pytest.raises(ValueError, match="Manifest checksum"):
        MOD.build(copy, dest, inputs["municipality_file"], inputs["release_config"])
    assert not dest.exists()
