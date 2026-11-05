"""Check 27-town non-composite multidimensional analysis and provenance."""
from __future__ import annotations

import csv
import importlib.util
import json
import shutil
from pathlib import Path

import pytest

from test_release_bundle import _make_fixture, bundle
from epah_diagnosis.analysis_v0_2 import compare

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "v0_2_analytic_builder", ROOT / "scripts/build_v0_2_multidimensional_analysis.py"
)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


@pytest.fixture(scope="module")
def source_bundle(tmp_path_factory):
    inputs = _make_fixture(tmp_path_factory.mktemp("v02-analysis"))
    return inputs, bundle.build_bundle(**inputs)


def test_27_complete_rows_and_28_pair_counts(source_bundle, tmp_path):
    inputs, pilot = source_bundle
    output = MOD.build(pilot, tmp_path / "new-analysis",
                       inputs["municipality_file"], inputs["release_config"])
    with (output / "municipality_comparison_v0_2.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    with (output / "pairwise_overlap_v0_2.csv").open(newline="", encoding="utf-8") as stream:
        pairs = list(csv.DictReader(stream))
    summary = json.loads((output / "analysis_summary_v0_2.json").read_text())
    manifest = json.loads((output / "analysis_manifest_v0_2.json").read_text())
    assert len(rows) == 27 and len({x["istat_code"] for x in rows}) == 27
    assert len(pairs) == 28
    assert summary["status"] == "technical_draft_do_not_publish"
    assert manifest["no_composite_score"] is True
    assert all(x["municipalities_total"] == "27" for x in pairs)
    assert all(not x["population_65_plus_pct_above_median"] == "true" for x in rows)
    assert all(int(x["municipalities_above_both"]) == 0 for x in pairs)
    assert not any(k in rows[0] for k in ("energy_poverty_score", "risk_rank"))


def test_strict_median_ties_never_count_as_above():
    fake = [{
        "municipality": f"Comune {i:02d}", "snai_class": "E",
        "snai_year": "2020",
        **{field: 20 for field in (
            "population_65_plus_pct", "income_vulnerability_pct",
            "old_building_stock_pct", "heating_degree_days",
            "mean_altitude_m", "dea_access_minutes",
            "upper_secondary_access_minutes", "rail_access_minutes"
        )},
        **{field: "2024" for field in (
            "population_65_plus_year", "income_vulnerability_year",
            "old_building_stock_year", "heating_degree_days_year",
            "mean_altitude_year", "dea_access_year",
            "upper_secondary_access_year", "rail_access_year"
        )},
    } for i in range(27)]
    codes = {p["municipality"]: f"001{i:03d}" for i, p in enumerate(fake, 1)}
    rows, summary = compare(fake, codes)
    assert not any(x["population_65_plus_pct_above_median"] == "true" for x in rows)
    assert all(item["municipalities_above_both"] == 0
               for item in summary["pairwise_cooccurrences"])


def test_output_collision_never_replaces_existing(source_bundle, tmp_path):
    inputs, pilot = source_bundle
    out = tmp_path / "existing"
    out.mkdir()
    (out / "review.json").write_text("preserve")
    with pytest.raises(FileExistsError):
        MOD.build(pilot, out, inputs["municipality_file"], inputs["release_config"])
    assert (out / "review.json").read_text() == "preserve"


def test_changed_bundle_is_rejected(source_bundle, tmp_path):
    inputs, pilot = source_bundle
    bad = tmp_path / "tampered"
    shutil.copytree(pilot, bad)
    path = bad / "municipality_profile.csv"
    path.write_bytes(path.read_bytes().replace(b"21", b"99", 1))
    with pytest.raises(ValueError, match="Manifest checksum"):
        MOD.build(bad, tmp_path / "never-created",
                  inputs["municipality_file"], inputs["release_config"])
