"""Preview isolation and disclosure regressions using only synthetic data."""
import csv
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import xarray as xr

from epah_diagnosis import experimental_previews as previews
from epah_diagnosis.provenance import sha256_file


def sources(tmp_path, *, all_suppressed=False):
    inputs = tmp_path / "originals"
    inputs.mkdir()
    registry = inputs / "registry.csv"
    registry.write_text("municipality,istat_code\n" + "".join(
        f"Comune {i:02d},001{i:03d}\n" for i in range(1,28)))
    survey = inputs / "survey.csv"
    with survey.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["municipality", "respondents", *previews.QUESTIONS])
        for i in range(1,28):
            w.writerow([f"Comune {i:02d}", 9 if i == 1 or all_suppressed else 20, 1, 2, 3, 4])
    return survey, registry


def survey_build(survey, registry, out):
    return previews.build_affordability(survey, registry, out,
        period_start="2025-01-01", period_end="2025-12-31")


def test_suppression_hides_counts_and_excludes_them_from_totals(tmp_path):
    survey, registry = sources(tmp_path)
    original = sha256_file(survey)
    out = survey_build(survey, registry, tmp_path / "preview")
    with (out / "preview.csv").open() as f:
        rows = list(csv.DictReader(f))
    suppressed, eligible = rows[:2]
    assert suppressed["missingness_reason"] == "small_sample_suppressed"
    assert suppressed["respondents"] == ""
    assert all(suppressed[field] == "" for field in previews.QUESTIONS)
    assert all(suppressed[field.removesuffix("_yes") + "_pct"] == "" for field in previews.QUESTIONS)
    assert eligible["respondents"] == "20"
    assert eligible["unable_warm_pct"] == "5.0"
    summary = json.loads((out / "summary.json").read_text())
    assert summary["eligible_respondents"] == 26 * 20
    assert summary["weighted_pct"]["unable_warm_yes"] == 5
    assert summary["excluded_suppressed_counts"] is True
    assert summary["suppressed_municipalities"] == 1
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["canonical_data_modified"] is False
    assert manifest["automatic_promotions"] == 0
    assert manifest["input_sha256"]["survey"] == original == sha256_file(survey)
    assert not (out / "survey.csv").exists()
    for name, expected in manifest["output_sha256"].items():
        assert sha256_file(out / name) == expected


def test_all_suppressed_has_no_reconstructable_aggregate(tmp_path):
    survey, registry = sources(tmp_path, all_suppressed=True)
    out = survey_build(survey, registry, tmp_path / "preview")
    summary = json.loads((out / "summary.json").read_text())
    assert summary["eligible_respondents"] == 0
    assert summary["suppressed_municipalities"] == 27
    assert all(value is None for value in summary["weighted_pct"].values())


def test_failed_validation_leaves_no_partial_output(tmp_path):
    survey, registry = sources(tmp_path)
    survey.write_text(survey.read_text().replace("20,1,2,3,4", "20,,2,3,4", 1))
    out = tmp_path / "preview"
    with pytest.raises(ValueError, match="count"):
        survey_build(survey, registry, out)
    assert not out.exists()


def test_mid_write_failure_leaves_no_published_or_staged_output(tmp_path, monkeypatch):
    survey, registry = sources(tmp_path)
    def interrupted(path, rows):
        path.write_text("incomplete")
        raise OSError("simulated write interruption")
    monkeypatch.setattr(previews, "_csv", interrupted)
    with pytest.raises(OSError, match="write interruption"):
        survey_build(survey, registry, tmp_path / "preview")
    assert not (tmp_path / "preview").exists()
    assert not list(tmp_path.glob(".epah-preview-*"))


def test_concurrent_output_creation_is_not_overwritten(tmp_path, monkeypatch):
    survey, registry = sources(tmp_path)
    out = tmp_path / "preview"
    original = previews._csv
    def competing_output(path, rows):
        original(path, rows)
        out.mkdir()
        (out / "keep").write_text("concurrent evidence")
    monkeypatch.setattr(previews, "_csv", competing_output)
    with pytest.raises(FileExistsError):
        survey_build(survey, registry, out)
    assert (out / "keep").read_text() == "concurrent evidence"
    assert list(out.iterdir()) == [out / "keep"]


def test_survey_cli_creates_preview_without_modifying_matrix(tmp_path):
    survey, registry = sources(tmp_path)
    matrix = previews.ROOT / "data/verification_matrix.csv"
    before = sha256_file(matrix)
    out = tmp_path / "preview"
    result = subprocess.run([sys.executable, str(previews.ROOT / "scripts/finalize_local_energy_affordability.py"),
        "--input", str(survey), "--registry", str(registry), "--out-dir", str(out),
        "--period-start", "2025-01-01", "--period-end", "2025-12-31"], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert (out / "manifest.json").is_file()
    assert sha256_file(matrix) == before


def test_existing_output_and_original_evidence_are_preserved(tmp_path):
    survey, registry = sources(tmp_path)
    out = tmp_path / "preview"
    out.mkdir()
    (out / "keep").write_text("prior evidence")
    with pytest.raises(FileExistsError):
        survey_build(survey, registry, out)
    assert (out / "keep").read_text() == "prior evidence"
    with pytest.raises(ValueError, match="input/evidence"):
        survey_build(survey, registry, survey.parent / "nested-output")


@pytest.mark.parametrize("directory", ["data/indicators", "config", "src", "docs"])
def test_canonical_destination_is_rejected(tmp_path, directory):
    survey, registry = sources(tmp_path)
    with pytest.raises(ValueError, match="canonical or source"):
        survey_build(survey, registry, previews.ROOT / directory / "must-never-be-created")


def test_survey_requires_a_real_ordered_reference_period(tmp_path):
    survey, registry = sources(tmp_path)
    with pytest.raises(ValueError, match="ordered ISO"):
        previews.build_affordability(survey, registry, tmp_path / "preview",
                                     period_start="2025-12-31", period_end="2025-01-01")
    assert not (tmp_path / "preview").exists()


@pytest.mark.parametrize("script", ["finalize_cooling_degree_days.py", "finalize_heat_stress_days.py",
                                   "finalize_local_energy_affordability.py"])
def test_no_argument_legacy_invocation_cannot_write_canonical_data(script):
    matrix = previews.ROOT / "data/verification_matrix.csv"
    before = sha256_file(matrix)
    result = subprocess.run([sys.executable, str(previews.ROOT / "scripts" / script)],
                            capture_output=True, text=True)
    assert result.returncode == 2
    assert "--out-dir" in result.stderr
    assert sha256_file(matrix) == before


@pytest.mark.parametrize("kind", ["cdd", "utci"])
def test_climate_preview_is_fresh_and_never_promotes(kind, tmp_path):
    _, registry = sources(tmp_path)
    originals = registry.parent
    times = pd.date_range("2025-01-01", "2026-01-01", inclusive="left",
                          freq="h" if kind == "utci" else "D")
    variable = "utci" if kind == "utci" else "t2m"
    nc = originals / "temperature.nc"
    xr.Dataset({variable: (("time","latitude","longitude"),
                            np.full((len(times),1,1), 38 if kind == "utci" else 26),
                            {"units":"degrees_Celsius"})},
               coords={"time":times,"latitude":[45.2],"longitude":[7.2]}).to_netcdf(nc)
    geometry = originals / "geo.json"
    # Identical synthetic shapes intentionally simplify the functional exercise.
    features = [{"type":"Feature", "properties":{"municipality":f"Comune {i:02d}",
                 "municipality_code":f"001{i:03d}"}, "geometry":{"type":"Polygon", "coordinates":[
                 [[7.1,45.1],[7.3,45.1],[7.3,45.3],[7.1,45.3],[7.1,45.1]]]}} for i in range(1,28)]
    geometry.write_text(json.dumps({"type":"FeatureCollection","features":features}))
    matrix = previews.ROOT / "data/verification_matrix.csv"
    before = sha256_file(matrix)
    out = previews.build_climate(kind, nc, geometry, registry, tmp_path/"preview", year=2025)
    with (out / "preview.csv").open() as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 27
    assert all(row["status"] == previews.STATUS for row in rows)
    assert all(row["reference_year"] == "2025" for row in rows)
    assert rows[0]["cdd" if kind == "cdd" else "strong_days"] == ("1825.0" if kind == "cdd" else "365")
    assert sha256_file(matrix) == before
    assert json.loads((out/"qa.json").read_text())["automatic_promotions"] == 0
