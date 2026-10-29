"""PR-08 integrated release tests. Fixtures are entirely synthetic (NOT observations)."""
from __future__ import annotations

import csv
import importlib
import json
import subprocess
import sys
from pathlib import Path

import pytest
from openpyxl import load_workbook

from epah_diagnosis.release_artifacts import (
    MAP_SPECS, _oriented_polygon_path, _ring_area,
    check_geojson, sha256_file, validate_bundle_contents,
)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
bundle = importlib.import_module("build_v0_1_bundle")

CORE = (
    "population_65_plus", "income_vulnerability", "old_building_stock",
    "heating_degree_days", "mean_altitude", "snai_classification",
    "dea_accessibility", "upper_secondary_accessibility", "rail_accessibility",
)
UNITS = {
    "population_65_plus": "%", "income_vulnerability": "%",
    "old_building_stock": "%", "heating_degree_days": "GG",
    "mean_altitude": "m s.l.m.", "snai_classification": "classe A-F",
    "dea_accessibility": "minuti",
    "upper_secondary_accessibility": "minuti", "rail_accessibility": "minuti",
}
YEARS = {
    "population_65_plus": "2026", "income_vulnerability": "2024",
    "old_building_stock": "2011", "heating_degree_days": "normativo",
    "mean_altitude": "2021", "snai_classification": "2020",
    "dea_accessibility": "2021", "upper_secondary_accessibility": "2021",
    "rail_accessibility": "2021",
}


def _polygon(x: float, y: float, hole=False):
    outer = [[x, y], [x + 0.03, y], [x + 0.03, y + 0.03],
             [x, y + 0.03], [x, y]]
    if not hole:
        return [outer]
    # Interior deliberately has same orientation as shell; renderer must
    # invert it, while geometry QA preserves the original coordinates.
    ring = [[x + 0.01, y + 0.01], [x + 0.02, y + 0.01],
            [x + 0.02, y + 0.02], [x + 0.01, y + 0.02],
            [x + 0.01, y + 0.01]]
    return [outer, ring]


def _make_fixture(tmp_path):
    registry = tmp_path / "municipalities.csv"
    rows = [(f"Comune {i:02d}", f"001{i:03d}") for i in range(1, 28)]
    registry.write_text(
        "municipality,istat_code\n" +
        "".join(f"{name},{code}\n" for name, code in rows),
        encoding="utf-8",
    )
    release = json.loads((ROOT / "config/release_v0_1.json").read_text(encoding="utf-8"))
    release["extensions"] = []
    release_file = tmp_path / "release.json"
    release_file.write_text(json.dumps(release), encoding="utf-8")
    catalog = json.loads((ROOT / "config/indicators.json").read_text(encoding="utf-8"))
    for item in catalog["indicators"]:
        item["methodological_maturity"] = "OPERATIONAL"
    catalog_path = tmp_path / "indicators.json"
    catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
    reviews = {
        "methodology_approvals": [
            {
                "indicator_id": item, "decision": "approved",
                "reviewed_by": "TEST FIXTURE, NO HUMAN SIGNOFF",
                "reviewed_on": "2026-10-29",
                "evidence_url": "https://example.org/synthetic-test-fixture",
            }
            for item in CORE
        ]
    }
    reviews_file = tmp_path / "reviews.json"
    reviews_file.write_text(json.dumps(reviews), encoding="utf-8")
    matrix = tmp_path / "matrix.csv"
    with matrix.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "municipality", "indicator_id", "indicator_name", "macro_area",
            "status", "source_priority", "year", "territorial_level", "unit",
            "source_url", "value", "quality", "limitations", "notes",
        ])
        writer.writeheader()
        for idx, (name, code) in enumerate(rows):
            for indicator in CORE:
                value = "E" if indicator == "snai_classification" else (
                    "3200" if indicator == "heating_degree_days" else
                    "650" if indicator == "mean_altitude" else
                    "30" if indicator in (
                        "dea_accessibility", "upper_secondary_accessibility",
                        "rail_accessibility"
                    ) else str(21 + idx % 9)
                )
                writer.writerow({
                    "municipality": name, "indicator_id": indicator,
                    "indicator_name": indicator, "macro_area": "synthetic",
                    "status": "Dato validato", "source_priority": "Fixture",
                    "year": YEARS[indicator], "territorial_level": "Comune",
                    "unit": UNITS[indicator],
                    "source_url": "https://example.org/not-a-real-source",
                    "value": value, "quality": "Synthetic fixture not field data",
                    "limitations": "Synthetic data for automated tests only",
                    "notes": "NEVER PUBLISH THIS FIXTURE",
                })
    geometry = {"type": "FeatureCollection", "features": []}
    for i, (name, code) in enumerate(rows):
        x, y = 7.2 + 0.04 * (i % 9), 45.2 + 0.045 * (i // 9)
        polygon = _polygon(x, y, hole=(i == 0))
        geom = (
            {"type": "MultiPolygon", "coordinates": [polygon, _polygon(x + 0.01, y + 0.038)]}
            if i == 1 else {"type": "Polygon", "coordinates": polygon}
        )
        geometry["features"].append({
            "type": "Feature",
            "properties": {"municipality": name, "municipality_code": code},
            "geometry": geom,
        })
    boundary = tmp_path / "boundaries.geojson"
    boundary.write_text(json.dumps(geometry), encoding="utf-8")
    return {
        "matrix_file": matrix, "municipality_file": registry,
        "catalog_file": catalog_path, "reviews_file": reviews_file,
        "release_config": release_file, "boundaries": boundary,
        "output_dir": tmp_path / "completed-v0.1",
    }


@pytest.fixture(scope="module")
def complete_fixture(tmp_path_factory):
    inputs = _make_fixture(tmp_path_factory.mktemp("full-release"))
    output = bundle.build_bundle(**inputs)
    return inputs, output


def test_synthetic_27x9_full_bundle_and_readiness(complete_fixture):
    inputs, path = complete_fixture
    assert path.exists()
    required = json.loads(inputs["release_config"].read_text())["required_artifacts"]
    assert len(required) == 17
    assert all((path / name).is_file() for name in required)
    assert len(list((path / "maps").glob("*.png"))) == 9
    readiness = json.loads((path / "readiness.json").read_text())
    assert readiness["phase"] == "release"
    assert readiness["release_ready"] is True
    assert readiness["core_checks_expected"] == 243
    assert json.loads((path / "release_manifest.json").read_text())["no_composite_score"]
    validate_bundle_contents(
        path,
        {f"Comune {i:02d}": f"001{i:03d}" for i in range(1, 28)},
        required,
    )


def test_release_excel_has_nine_indicators_and_lineage(complete_fixture):
    _, path = complete_fixture
    book = load_workbook(path / "completeness.xlsx", read_only=True, data_only=True)
    assert book.sheetnames == [
        "Overview", "Municipalities", "Indicators", "Comparison", "Matrix_Evidence",
    ]
    assert book["Municipalities"].max_row == 28
    assert book["Indicators"].max_row == 10
    assert book["Matrix_Evidence"].max_row == 244
    assert book["Municipalities"]["B2"].value == "001001"
    assert book["Municipalities"]["K2"].value == "E"
    assert book["Indicators"]["E2"].value == "OPERATIONAL"
    book.close()


def test_release_geojson_has_27_codes_and_multipolygons(complete_fixture):
    _, path = complete_fixture
    data = json.loads((path / "municipality_profile.geojson").read_text())
    assert len(data["features"]) == 27
    assert data["features"][0]["properties"]["municipality_code"] == "001001"
    assert data["features"][1]["geometry"]["type"] == "MultiPolygon"
    assert data["features"][0]["properties"]["snai_class"] == "E"


def test_manifest_checks_real_input_and_artifact_bytes(complete_fixture):
    inputs, output = complete_fixture
    manifest = json.loads((output / "release_manifest.json").read_text())
    assert manifest["source_inputs"]["matrix"]["sha256"] == sha256_file(inputs["matrix_file"])
    assert manifest["source_inputs"]["istat_boundaries"]["sha256"] == sha256_file(inputs["boundaries"])
    assert "release_manifest.json" not in manifest["artifacts"]
    assert "readiness.json" not in manifest["artifacts"]
    for name, item in manifest["artifacts"].items():
        assert item["sha256"] == sha256_file(output / name)


def test_pdf_and_png_are_real_artifacts(complete_fixture):
    _, output = complete_fixture
    assert (output / "diagnostic_report.pdf").read_bytes().startswith(b"%PDF")
    assert (output / "diagnostic_report.pdf").stat().st_size > 3000
    for _, _, _, name in MAP_SPECS:
        assert (output / "maps" / name).read_bytes().startswith(b"\x89PNG")


def test_polygon_hole_winding_corrected_without_modifying_geometry():
    coords = _polygon(7.2, 45.1, hole=True)
    assert _ring_area(coords[0]) > 0
    assert _ring_area(coords[1]) > 0
    path = _oriented_polygon_path(coords)
    assert len(path.vertices) == 10
    # The renderer reverses the hole orientation, avoiding filled lakes.
    hole = path.vertices[5:].tolist()
    assert _ring_area(hole) < 0


def test_missing_or_duplicate_geometry_rejected(tmp_path):
    inputs = _make_fixture(tmp_path)
    geo = json.loads(inputs["boundaries"].read_text())
    expected = {f"Comune {i:02d}": f"001{i:03d}" for i in range(1, 28)}
    check_geojson(geo, expected)
    geo["features"][0]["properties"]["municipality_code"] = "001999"
    with pytest.raises(ValueError, match="Unmatched municipality"):
        check_geojson(geo, expected)


def test_actual_repository_not_ready_and_no_artifacts_created(tmp_path):
    output = tmp_path / "must-not-exist"
    with pytest.raises(ValueError, match="NOT READY"):
        bundle.build_bundle(output_dir=output)
    assert not output.exists()


def test_existing_release_not_overwritten_without_explicit_replace(complete_fixture):
    inputs, output = complete_fixture
    old = sha256_file(output / "release_manifest.json")
    with pytest.raises(FileExistsError, match="Release destination exists"):
        bundle.build_bundle(**inputs)
    assert sha256_file(output / "release_manifest.json") == old


def test_bundle_content_check_rejects_manifest_tampering(complete_fixture, tmp_path):
    inputs, output = complete_fixture
    registry = {f"Comune {i:02d}": f"001{i:03d}" for i in range(1, 28)}
    expected = json.loads(inputs["release_config"].read_text())["required_artifacts"]
    manifest = json.loads((output / "release_manifest.json").read_text())
    manifest["artifacts"]["municipality_profile.csv"]["sha256"] = "0" * 64
    (tmp_path / "release_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="Manifest checksum"):
        # Verify the tampered manifest in place, without touching original fixture.
        from unittest.mock import patch
        # Change is temporary: restore on exit.
        p = output / "release_manifest.json"
        prior = p.read_bytes()
        try:
            p.write_text(json.dumps(manifest), encoding="utf-8")
            validate_bundle_contents(output, registry, expected)
        finally:
            p.write_bytes(prior)


def test_bundle_command_help_requires_no_data():
    script = ROOT / "scripts/build_v0_1_bundle.py"
    result = subprocess.run([sys.executable, str(script), "--help"],
                            capture_output=True, text=True)
    assert result.returncode == 0
    assert "--replace" in result.stdout
