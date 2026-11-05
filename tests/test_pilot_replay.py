"""Synthetic tests for deterministic EPAH core-output replay."""
from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from test_release_bundle import _make_fixture, bundle

import importlib.util

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "check_pilot_replay", ROOT / "scripts/check_pilot_replay.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _bundle_stub(path: Path) -> None:
    path.mkdir()
    for filename in ("municipality_profile.csv", "municipality_comparison.csv"):
        with (path / filename).open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerows([["municipality", "value"], ["Fictitious A", "1.23"]])
    (path / "municipality_profile.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": [
            {"type": "Feature",
             "properties": {"municipality_code": "001001", "value": 1.23},
             "geometry": {"type": "Point", "coordinates": [7.1, 45.1]}}
        ]}), encoding="utf-8"
    )


def test_identical_synthetic_core_matches_ignoring_nondeterministic_metadata(tmp_path):
    first, second = tmp_path / "a", tmp_path / "b"
    _bundle_stub(first)
    _bundle_stub(second)
    (first / "release_manifest.json").write_text('{"generated_at_utc":"one"}')
    (second / "release_manifest.json").write_text('{"generated_at_utc":"two"}')
    assert MODULE.compare(first, second)["status"] == "match"


def test_numeric_change_is_detected(tmp_path):
    first, second = tmp_path / "a", tmp_path / "b"
    _bundle_stub(first)
    _bundle_stub(second)
    target = second / "municipality_profile.csv"
    target.write_text(target.read_text().replace("1.23", "1.24"), encoding="utf-8")
    result = MODULE.compare(first, second)
    assert result["status"] == "blocked"
    assert result["files"]["municipality_profile.csv"] == "different"


def test_missing_file_and_duplicate_municipality_fail_closed(tmp_path):
    first, second = tmp_path / "a", tmp_path / "b"
    _bundle_stub(first)
    _bundle_stub(second)
    (second / "municipality_profile.geojson").unlink()
    assert MODULE.compare(first, second)["files"]["municipality_profile.geojson"] == "missing"
    _bundle_stub(tmp_path / "third")
    other = tmp_path / "third"
    with (other / "municipality_profile.csv").open("a", encoding="utf-8") as out:
        out.write("Fictitious A,1.23\n")
    assert MODULE.compare(first, other)["files"]["municipality_profile.csv"] == "invalid"


def test_two_independent_synthetic_full_builds_have_identical_core(tmp_path):
    # All values and geometry are synthetic: no local official source access needed.
    inputs = _make_fixture(tmp_path)
    first = bundle.build_bundle(**inputs)
    second = bundle.build_bundle(
        **{**inputs, "output_dir": tmp_path / "replayed-v0.1"}
    )
    result = MODULE.compare(first, second)
    assert result["status"] == "match", result
    assert set(result["files"]) == set(MODULE.CORE_FILES)
