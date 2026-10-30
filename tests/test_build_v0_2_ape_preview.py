"""Synthetic v0.2 PDF/map tests: never claim real source validation."""
from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path

import pytest
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "ape_v02_builder", ROOT / "scripts/build_v0_2_ape_preview.py")
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)


def sample_input(tmp_path):
    registry = ROOT / "data/municipalities.csv"
    towns = list(csv.DictReader(registry.open(encoding="utf-8")))
    assert len(towns) == 27
    file = tmp_path / "sample.csv"
    with file.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "municipality", "istat_code", *BUILDER.COLS,
            "ape_fg", "ape_total", "ape_fg_share_pct",
            "snapshot_date", "denominator", "scope",
        ], lineterminator="\n")
        writer.writeheader()
        for t in towns:
            writer.writerow({
                "municipality": t["municipality"], "istat_code": t["istat_code"],
                **{k: 1 for k in BUILDER.COLS},
                "ape_fg": 2, "ape_total": 10, "ape_fg_share_pct": "20.00",
                "snapshot_date": "2026-08-31", "denominator": "all_ape",
                "scope": "all_building_uses_not_residential_only",
            })
    qa_file = tmp_path / "qa.json"
    qa_file.write_text(json.dumps({
        "indicator_id": "ape_fg_share_all_uses",
        "qa_status": "technical_extraction_only",
        "validated_as_residential_share": False,
        "municipalities_matched": 27, "municipalities_expected": 27,
        "source_license": "CC BY 4.0",
        "municipality_registry_sha256": BUILDER.hash_file(registry),
        "result_csv_sha256": BUILDER.hash_file(file),
        "source_csv_sha256": "a" * 64,
        "snapshot_date": "2026-08-31",
        "ape_count_27": 270, "ape_fg_count_27": 54,
        "pooled_fg_share_pct": 20.0,
    }), encoding="utf-8")
    return file, qa_file, registry


def test_loads_27_ape_observations_with_correct_denominator(tmp_path):
    file, qa, registry = sample_input(tmp_path)
    rows, stats = BUILDER.load_ape(file, qa, registry)
    assert len(rows) == 27
    assert stats["total"] == 270
    assert stats["fg"] == 54
    assert stats["pooled_pct"] == 20.0


def test_refuses_misleading_residential_approval(tmp_path):
    file, qa, registry = sample_input(tmp_path)
    data = json.loads(qa.read_text(encoding="utf-8"))
    data["validated_as_residential_share"] = True
    qa.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="QA metadata"):
        BUILDER.load_ape(file, qa, registry)


def test_refuses_tampered_counts_even_if_csv_sha_is_updated(tmp_path):
    file, qa, registry = sample_input(tmp_path)
    data = file.read_text(encoding="utf-8")
    file.write_text(data.replace(",2,10,20.00,", ",3,10,20.00,", 1), encoding="utf-8")
    doc = json.loads(qa.read_text(encoding="utf-8"))
    doc["result_csv_sha256"] = BUILDER.hash_file(file)
    qa.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(ValueError, match="numerator or denominator"):
        BUILDER.load_ape(file, qa, registry)


def test_report_has_project_code_and_limitations(tmp_path):
    file, qa, registry = sample_input(tmp_path)
    rows, stats = BUILDER.load_ape(file, qa, registry)
    chart = tmp_path / "classes.png"
    BUILDER.class_chart(stats, chart)
    from PIL import Image as PILImage
    mapfile = tmp_path / "map.png"
    PILImage.new("RGB", (800, 800), "white").save(mapfile)
    pdf = tmp_path / "report.pdf"
    BUILDER.build_report(pdf, rows, stats, mapfile, chart)
    assert pdf.stat().st_size > 5000
    reader = PdfReader(pdf)
    text = "\n".join(page.extract_text() for page in reader.pages)
    assert len(reader.pages) >= 4
    assert BUILDER.TA_CODE in text
    assert "Regione Piemonte" in text
    assert "non residenziale" in text or "non residenziale" in text.lower()
    assert "8.070" not in text  # synthetic fixtures, not user data


def test_geojson_code_mismatch_is_rejected(tmp_path, monkeypatch):
    file, qa, registry = sample_input(tmp_path)
    rows, _ = BUILDER.load_ape(file, qa, registry)
    towns = {r["municipality"] for r in rows}
    fake = {"type":"FeatureCollection","features":[
        {"type":"Feature",
         "properties":{"municipality":r["municipality"],"municipality_code":"009999"},
         "geometry":{"type":"Polygon","coordinates":[[
            [7.1,45.1],[7.2,45.1],[7.2,45.2],[7.1,45.2],[7.1,45.1]]]}}
        for r in rows]}
    monkeypatch.setattr(BUILDER,"parse_boundaries_zip",lambda *args:fake)
    source=tmp_path / "boundaries.zip"
    source.write_bytes(b"dummy")
    with pytest.raises(ValueError,match="ISTAT code mismatch"):
        BUILDER.enriched_geography(source,rows)


def test_full_preview_pipeline_and_immutable_outputs(tmp_path, monkeypatch):
    file, qa, registry = sample_input(tmp_path)
    rows, _ = BUILDER.load_ape(file, qa, registry)
    features = []
    for idx, row in enumerate(rows):
        x = 7.1 + (idx % 9) * .04
        y = 45.1 + (idx // 9) * .04
        ring = [[x,y],[x+.025,y],[x+.025,y+.025],[x,y+.025],[x,y]]
        features.append({
            "type": "Feature",
            "properties": {
                "municipality": row["municipality"],
                "municipality_code": row["istat_code"],
                "boundary_year": 2026,
            },
            "geometry": {"type": "Polygon", "coordinates": [ring]},
        })
    geo = {
        "type":"FeatureCollection",
        "crs":{"type":"name","properties":{"name":"OGC:CRS84"}},
        "features":features,
    }
    monkeypatch.setattr(BUILDER, "parse_boundaries_zip", lambda *a: geo)
    boundary = tmp_path / "ISTAT_dummy.zip"
    boundary.write_bytes(b"synthetic input, not original ISTAT")
    out = tmp_path / "v02-preview"
    assert BUILDER.build_preview(file, qa, registry, boundary, out) == out
    names = {p.name for p in out.iterdir()}
    assert {"diagnostic_report_v0_2_ape_preview.pdf",
            "map_ape_fg_share_all_uses.png",
            "map_ape_fg_relative_27.png",
            "ape_fg_27_municipalities.geojson",
            "ape_v0_2_manifest.json"} <= names
    manifest = json.loads((out / "ape_v0_2_manifest.json").read_text(encoding="utf-8"))
    assert manifest["municipalities"] == 27
    assert manifest["map_mode"] == "both"
    assert manifest["relative_reference"] == "unweighted_arithmetic_mean_of_27_municipal_shares"
    assert manifest["registered_apes"] == 270
    assert manifest["status"] == "technical_preview_not_institutionally_approved"
    assert len(manifest["files_sha256"]) >= 6
    geometry = json.loads((out / "ape_fg_27_municipalities.geojson").read_text(encoding="utf-8"))
    assert len(geometry["features"]) == 27
    assert all(f["properties"]["ape_snapshot_date"] == "2026-08-31"
               for f in geometry["features"])
    with pytest.raises(FileExistsError, match="already exists"):
        BUILDER.build_preview(file, qa, registry, boundary, out)


def test_user_can_select_relative_only(tmp_path, monkeypatch):
    file, qa, registry = sample_input(tmp_path)
    rows, _ = BUILDER.load_ape(file, qa, registry)
    features = []
    for i, r in enumerate(rows):
        x, y = 7.1 + (i % 9) * .04, 45.1 + (i // 9) * .04
        ring = [[x,y],[x+.02,y],[x+.02,y+.02],[x,y+.02],[x,y]]
        features.append({"type":"Feature",
                         "properties":{"municipality":r["municipality"],"municipality_code":r["istat_code"]},
                         "geometry":{"type":"Polygon","coordinates":[ring]}})
    geo = {"type":"FeatureCollection","features":features}
    monkeypatch.setattr(BUILDER,"parse_boundaries_zip",lambda *a: geo)
    bounds=tmp_path/"dummy.zip"
    bounds.write_bytes(b"synthetic")
    out=tmp_path/"relative-only"
    BUILDER.build_preview(file,qa,registry,bounds,out,map_mode="relative")
    assert (out/"map_ape_fg_relative_27.png").exists()
    assert not (out/"map_ape_fg_share_all_uses.png").exists()
