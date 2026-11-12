"""v0.4 extended atlas fixtures are synthetic; no territorial values are published."""
from __future__ import annotations

import csv
import importlib.util
import io
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("epah_v04_atlas_test", ROOT / "scripts/build_v0_4_visual_atlas.py")
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = mod
SPEC.loader.exec_module(mod)


def make_registry(tmp_path):
    p = tmp_path / "municipalities.csv"
    p.write_text("municipality,istat_code\n" + "".join(
        f"Synthetic {i:02d},001{i:03d}\n" for i in range(1, 28)), encoding="utf-8")
    return p, {f"001{i:03d}": f"Synthetic {i:02d}" for i in range(1, 28)}


def csvbytes(rows):
    with io.StringIO(newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        return output.getvalue().encode()


def preview(path, filename, rows, manifest_extras, qa_extras, registry):
    path.mkdir()
    contents = csvbytes(rows)
    qa = {"status": mod.STATUS, **qa_extras}
    qa_bytes = json.dumps(qa).encode()
    (path / filename).write_bytes(contents)
    (path / "qa.json").write_bytes(qa_bytes)
    manifest = {
        "status": mod.STATUS, "scientific_approval": False,
        "canonical_data_modified": False,
        "municipality_registry_sha256": mod.v3.file_sha(registry),
        "outputs_sha256": {
            filename: mod.v3.byte_sha(contents), "qa.json": mod.v3.byte_sha(qa_bytes),
        }, **manifest_extras,
    }
    (path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return manifest


def climate_inputs(tmp_path, registry, names):
    h03 = tmp_path / "h03"
    h04 = tmp_path / "h04"
    hashes = {
        "original_tmin_netcdf_sha256": "a" * 64,
        "original_tmax_netcdf_sha256": "b" * 64,
        "normalized_daily_csv_sha256": "c" * 64,
    }
    rows03 = [{
        "municipality_code": code, "municipality": name,
        "reference_year": "2025", "hdd_eurostat_estimated_c_days": "1900.00",
        "temperature_days": "365", "grid_cell_id": "NWIOI:1",
        "grid_latitude": "45.1", "grid_longitude": "7.2", "status": mod.STATUS,
    } for code, name in names.items()]
    preview(h03, "hdd_eurostat_annual_preview.csv", rows03, hashes,
            {"indicator_inventory_id": "H03"}, registry)
    rows04 = [{
        "municipality_code": code, "municipality": name,
        "reference_year": "2025", "cdd_eurostat_estimated_c_days": "42.50",
        "temperature_days": "365", "grid_cell_id": "NWIOI:1",
        "grid_latitude": "45.1", "grid_longitude": "7.2", "status": mod.STATUS,
    } for code, name in names.items()]
    preview(h04, "cdd_eurostat_annual_preview.csv", rows04,
            {**hashes, "indicator_id": "H04",
             "source_to_municipality_mapping_verified": False},
            {"epah_inventory_id": "H04"}, registry)
    return h03, h04


def housing_input(tmp_path, registry, names, kind):
    folder = tmp_path / kind
    source = mod.HOUSING[kind]
    date = "2023-12-31" if kind == "ADD-HOUSING-01" else "2025-10-31"
    rows = [{
        "municipality_code": code, "municipality": name,
        "reference_date": date, "indicator_id": source,
        "numerator": "3", "denominator": "10", "value_pct": "30.00",
        "status": mod.STATUS,
    } for code, name in names.items()]
    preview(folder, source + "_preview.csv", rows,
            {"indicator_id": source, "source_mapping_verified": False,
             "original_export_sha256": "a" * 64, "normalized_csv_sha256": "b" * 64},
            {"qa": {"source_mapping_verified": False,
                    "residential_filter_verified": False if kind == "H05" else None}}, registry)
    return folder


def test_h04_requires_same_original_daily_input_and_cells(tmp_path):
    registry, names = make_registry(tmp_path)
    h03, h04 = climate_inputs(tmp_path, registry, names)
    values, receipt = mod.load_h04(h04, h03, names, registry)
    assert len(values) == 27 and values["001001"]["value"] == 42.5
    assert receipt["evidence_level"].startswith("technical_")
    manifest = json.loads((h04 / "manifest.json").read_text())
    manifest["normalized_daily_csv_sha256"] = "f" * 64
    (h04 / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="same normalized"):
        mod.load_h04(h04, h03, names, registry)


def test_h04_rejects_different_grid_cell(tmp_path):
    registry, names = make_registry(tmp_path)
    h03, h04 = climate_inputs(tmp_path, registry, names)
    file = h04 / "cdd_eurostat_annual_preview.csv"
    file.write_bytes(file.read_bytes().replace(b"NWIOI:1", b"NWIOI:2", 1))
    manifest = json.loads((h04 / "manifest.json").read_text())
    manifest["outputs_sha256"][file.name] = mod.v3.file_sha(file)
    (h04 / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="cell selection mismatch"):
        mod.load_h04(h04, h03, names, registry)


@pytest.mark.parametrize("kind", ["H05", "ADD-HOUSING-01"])
def test_housing_counts_and_missing_period_rejected(tmp_path, kind):
    registry, names = make_registry(tmp_path)
    folder = housing_input(tmp_path, registry, names, kind)
    result, evidence = mod.load_housing(folder, kind, names, registry)
    assert result["001001"]["numerator"] == "3"
    assert result["001001"]["denominator"] == "10"
    assert result["001001"]["value"] == 30.0
    assert evidence["evidence_level"].startswith("technical_")
    file = folder / (mod.HOUSING[kind] + "_preview.csv")
    file.write_bytes(file.read_bytes().replace(b"30.00", b"31.00", 1))
    manifest = json.loads((folder / "manifest.json").read_text())
    manifest["outputs_sha256"][file.name] = mod.v3.file_sha(file)
    (folder / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="reconciliation"):
        mod.load_housing(folder, kind, names, registry)


def test_new_atlas_has_sixteen_slots_and_no_fake_values(tmp_path, monkeypatch):
    registry, names = make_registry(tmp_path)
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    geo = {"type": "FeatureCollection",
           "crs": {"type": "name", "properties": {"name": "OGC:CRS84"}},
           "features": [{"type": "Feature", "properties": {},
                         "geometry": {"type": "Polygon", "coordinates": [[
                             [7, 45], [7.1, 45], [7.1, 45.1], [7, 45.1], [7, 45]
                         ]]}}]}
    (bundle / "municipality_profile.geojson").write_text(json.dumps(geo))
    def fake_v3_build(bundle, out, **kwargs):
        out.mkdir()
        (out / "charts").mkdir()
        payload = {
            "status": mod.STATUS, "publication_allowed": False,
            "no_composite_score": True, "municipality_count": 27,
            "identical_numeric_series": [],
            "indicators": [{
                "id": metric.id, "name": metric.name, "unit": metric.unit,
                "family": metric.family, "description": metric.description,
                "source": metric.source, "available": False,
                "count": 0, "years": [], "evidence": "not_available",
            } for metric in mod.v3.METRICS],
            "municipalities": [
                {"code": code, "name": name, "values": {}} for code, name in names.items()
            ],
        }
        (out / "atlas_data.json").write_text(json.dumps(payload))
        (out / "index.html").write_text("old template")
        (out / "README_REVIEW.txt").write_text("old")
        (out / "atlas_manifest.json").write_text(json.dumps({
            "status": mod.STATUS, "publication_allowed": False,
            "registry_sha256": mod.v3.file_sha(registry),
            "input_evidence": {},
            "output_sha256": {"atlas_data.json": mod.v3.file_sha(out / "atlas_data.json")},
        }))
    monkeypatch.setattr(mod.v3, "build", fake_v3_build)
    monkeypatch.setattr(mod.v3, "check_geojson", lambda *args, **kwargs: None)
    monkeypatch.setattr(mod.v3, "_make_map", lambda *args: args[-2].write_text("synthetic"))
    monkeypatch.setattr(mod.v3, "_make_distribution", lambda *args: args[-2].write_text("synthetic"))
    h05 = housing_input(tmp_path, registry, names, "H05")
    output = mod.build(bundle, tmp_path / "atlas", registry_path=registry,
                       h05_dir=h05)
    payload = json.loads((output / "atlas_data.json").read_text())
    manifest = json.loads((output / "atlas_manifest.json").read_text())
    assert len(payload["indicators"]) == 16
    assert len(manifest["indicators_pending"]) == 15
    assert manifest["indicators_available"] == ["H05"]
    assert payload["municipalities"][0]["values"]["H05"]["denominator"] == "10"
    assert "H04" not in payload["municipalities"][0]["values"]
    assert "ADD-HOUSING-01" not in payload["municipalities"][0]["values"]
    assert "16</strong>" in (output / "index.html").read_text()
    assert (output / "charts/H05_map.png").is_file()
    with pytest.raises(FileExistsError):
        mod.build(bundle, output, registry_path=registry)


def test_h04_requires_h03_without_writing(tmp_path):
    with pytest.raises(ValueError, match="requires the H03"):
        mod.build(tmp_path / "bundle", tmp_path / "out", h04_dir=tmp_path / "h04")
    assert not (tmp_path / "out").exists()
