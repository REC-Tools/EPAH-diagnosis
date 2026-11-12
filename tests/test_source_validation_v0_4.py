"""Synthetic-only adversarial tests for technical, never scientific, source replay."""
from __future__ import annotations

import csv
from datetime import date, timedelta
import importlib.util
import json
from pathlib import Path

import pytest

from epah_diagnosis.source_validation_v0_4 import (
    STATUS, assess, digest, publish_report, validate_climate, validate_h05,
)

ROOT = Path(__file__).resolve().parents[1]


def csv_write(path, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def sample_registry(tmp_path):
    registry = tmp_path / "municipalities.csv"
    codes = [(f"001{i:03d}", f"Synthetic {i:02d}") for i in range(1, 28)]
    csv_write(registry, [{"municipality": name, "istat_code": code} for code, name in codes])
    return registry, codes


def preview(folder, file_name, rows, registry, *, indicator, source_sha):
    folder.mkdir()
    csv_write(folder / file_name, rows)
    qa = {"status": STATUS}
    manifest = {
        "status": STATUS, "scientific_approval": False,
        "canonical_data_modified": False,
        "municipality_registry_sha256": digest(registry),
        "outputs_sha256": {file_name: digest(folder / file_name)},
        **source_sha,
    }
    if indicator == "H03":
        qa["indicator_inventory_id"] = "H03"
        manifest["raw_netcdf_temporal_and_spatial_consistency_verified"] = False
    elif indicator == "H04":
        qa["epah_inventory_id"] = "H04"
        manifest.update(indicator_id="H04", source_to_municipality_mapping_verified=False)
    else:
        qa["qa"] = {"source_mapping_verified": False,
                    "residential_filter_verified": False}
        manifest.update(indicator_id="h05_ape_fg", source_mapping_verified=False)
    (folder / "qa.json").write_text(json.dumps(qa), encoding="utf-8")
    manifest["outputs_sha256"]["qa.json"] = digest(folder / "qa.json")
    (folder / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def climate_fixture(tmp_path):
    registry, codes = sample_registry(tmp_path)
    source = tmp_path / "originals"
    source.mkdir()
    originals = {}
    for name in ("tmin", "tmax", "mask", "boundaries"):
        p = source / name
        p.write_text("SYNTHETIC " + name, encoding="utf-8")
        originals[name] = p
    daily = source / "daily.csv"
    dates = [(date(2025, 1, 1) + timedelta(days=i)).isoformat() for i in range(365)]
    records, rows03, rows04 = [], [], []
    for i, (code, name) in enumerate(codes):
        cell = f"synthetic-cell:{i}"
        lat = f"{45 + i * 0.002:.3f}"
        lon = f"{7 + i * 0.002:.3f}"
        for day in dates:
            records.append({
                "municipality_code": code, "municipality": name, "date": day,
                "grid_cell_id": cell, "grid_latitude": lat, "grid_longitude": lon,
                "tmin_c": "10.0", "tmax_c": "12.0",
            })
        row = {"municipality_code": code, "municipality": name,
               "reference_year": "2025", "temperature_days": "365",
               "grid_cell_id": cell, "grid_latitude": lat, "grid_longitude": lon,
               "status": STATUS}
        rows03.append({**row, "hdd_eurostat_estimated_c_days": "2555.00"})
        rows04.append({**row, "cdd_eurostat_estimated_c_days": "0.00"})
    csv_write(daily, records)
    common = {
        "normalized_daily_csv_sha256": digest(daily),
        "original_tmin_netcdf_sha256": digest(originals["tmin"]),
        "original_tmax_netcdf_sha256": digest(originals["tmax"]),
    }
    h03, h04 = tmp_path / "h03", tmp_path / "h04"
    preview(h03, "hdd_eurostat_annual_preview.csv", rows03, registry,
            indicator="H03", source_sha=common)
    preview(h04, "cdd_eurostat_annual_preview.csv", rows04, registry,
            indicator="H04", source_sha=common)
    extraction = source / "extraction_qa.json"
    extraction.write_text(json.dumps({
        "status": STATUS, "candidate_id": "H03", "reference_year": 2025,
        "daily_observations": 9855,
        "source_netcdf_temporal_grid_and_temperature_checks_passed": True,
        "technical_geospatial_cell_selection_completed": True,
        "masked_cells_only": True, "scientific_approval": False,
        "input_hashes_sha256": {
            "normalized_daily_csv": digest(daily),
            "tmin_netcdf": digest(originals["tmin"]),
            "tmax_netcdf": digest(originals["tmax"]),
            "mask_netcdf": digest(originals["mask"]),
            "boundaries_geojson": digest(originals["boundaries"]),
            "municipality_registry": digest(registry),
        },
        "annual_hdd_preview_sha256": digest(h03 / "hdd_eurostat_annual_preview.csv"),
    }), encoding="utf-8")
    return registry, {
        **originals, "daily": daily, "h03_dir": h03,
        "h04_dir": h04, "extraction_qa": extraction,
    }


def h05_fixture(tmp_path):
    registry, codes = sample_registry(tmp_path)
    folder = tmp_path / "h05"
    original = tmp_path / "original-ape.csv"
    original.write_text("SYNTHETIC original: not real EPC evidence")
    normalized = tmp_path / "normalized.csv"
    categories = ("A4", "A3", "A2", "A1", "B", "C", "D", "E", "F", "G", "total")
    counts = {"D": 7, "F": 2, "G": 1, "total": 10}
    source = [{
        "municipality_code": code, "municipality": name,
        "reference_date": "2025-10-31",
        "data_scope": "valid_residential_ape", "group": category,
        "count": str(counts.get(category, 0)),
    } for code, name in codes for category in categories]
    csv_write(normalized, source)
    values = [{
        "municipality_code": code, "municipality": name,
        "reference_date": "2025-10-31", "indicator_id": "h05_ape_fg",
        "numerator": "3", "denominator": "10", "value_pct": "30.00",
        "status": STATUS,
    } for code, name in codes]
    preview(folder, "h05_ape_fg_preview.csv", values, registry, indicator="H05",
            source_sha={"original_export_sha256": digest(original),
                        "normalized_csv_sha256": digest(normalized)})
    return registry, {"normalized": normalized, "original": original, "h05_dir": folder}


def test_climate_recomputes_9855_values_with_no_scientific_approval(tmp_path):
    registry, paths = climate_fixture(tmp_path)
    result = validate_climate(paths, registry)
    assert result["status"] == "technical_replay_passed_review_pending"
    assert result["h03_h04_recomputed_27_by_365"] is True
    assert result["independent_netcdf_decoding"] is False
    assert result["publication_allowed"] is False
    assert result["daily_rows"] == 9855


def test_climate_detects_mismatched_original_hash(tmp_path):
    registry, paths = climate_fixture(tmp_path)
    paths["tmin"].write_text("SYNTHETIC changed without a new receipt")
    with pytest.raises(ValueError, match="SHA-256"):
        validate_climate(paths, registry)


def test_climate_independent_reproduction_blocks_changed_annual_value(tmp_path):
    registry, paths = climate_fixture(tmp_path)
    output = paths["h04_dir"] / "cdd_eurostat_annual_preview.csv"
    content = output.read_text().replace("0.00", "7.00", 1)
    output.write_text(content)
    manifest_file = paths["h04_dir"] / "manifest.json"
    manifest = json.loads(manifest_file.read_text())
    manifest["outputs_sha256"][output.name] = digest(output)
    manifest_file.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="independent annual reproduction mismatch"):
        validate_climate(paths, registry)


def test_climate_missing_date_blocks_replay_even_if_hashes_are_rewritten(tmp_path):
    registry, paths = climate_fixture(tmp_path)
    daily = paths["daily"]
    rows = list(csv.DictReader(daily.open(newline="", encoding="utf-8")))
    csv_write(daily, rows[:-1])
    for directory in ("h03_dir", "h04_dir"):
        manifest_file = paths[directory] / "manifest.json"
        manifest = json.loads(manifest_file.read_text())
        manifest["normalized_daily_csv_sha256"] = digest(daily)
        manifest_file.write_text(json.dumps(manifest))
    extract = paths["extraction_qa"]
    qa = json.loads(extract.read_text())
    qa["input_hashes_sha256"]["normalized_daily_csv"] = digest(daily)
    extract.write_text(json.dumps(qa))
    with pytest.raises(ValueError, match="27 x 365"):
        validate_climate(paths, registry)


def test_h05_recomputes_residential_class_shares(tmp_path):
    registry, paths = h05_fixture(tmp_path)
    result = validate_h05(paths, registry)
    assert result["normalized_ape_classes_recomputed"] is True
    assert result["class_records"] == 27 * 11
    assert result["independent_original_residential_filter"] is False
    assert result["scientific_approval"] is False


def test_h05_counts_change_rejected_with_rehashed_local_manifest(tmp_path):
    registry, paths = h05_fixture(tmp_path)
    file = paths["h05_dir"] / "h05_ape_fg_preview.csv"
    file.write_text(file.read_text().replace("30.00", "40.00", 1))
    manifest_file = paths["h05_dir"] / "manifest.json"
    manifest = json.loads(manifest_file.read_text())
    manifest["outputs_sha256"][file.name] = digest(file)
    manifest_file.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="percentage inconsistent"):
        validate_h05(paths, registry)


def test_missing_inputs_are_explicitly_blocked_and_report_immutable(tmp_path):
    registry, _ = sample_registry(tmp_path)
    report = assess(registry)
    assert report["climate_h03_h04"]["status"] == "blocked_missing_originals"
    assert report["residential_h05"]["status"] == "blocked_missing_originals"
    assert report["completely_validated_for_territorial_publication"] is False
    out = tmp_path / "report"
    publish_report(out, report)
    receipt = json.loads((out / "manifest.json").read_text())
    assert receipt["outputs_sha256"]["validation.json"] == digest(out / "validation.json")
    with pytest.raises(FileExistsError):
        publish_report(out, report)


def test_cli_blocks_missing_originals_but_preserves_json_report(tmp_path):
    registry, _ = sample_registry(tmp_path)
    spec = importlib.util.spec_from_file_location("v04_validation_cli", ROOT / "scripts/validate_v0_4_sources.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    folder = tmp_path / "missing"
    with pytest.raises(SystemExit) as e:
        mod.main(["--registry", str(registry), "--out-dir", str(folder)])
    assert e.value.code == 2
    assert json.loads((folder / "validation.json").read_text())["scientific_approval"] is False
