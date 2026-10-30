"""Synthetic CIT inspection and v0.2 mapped PDF end-to-end tests."""
from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path

import pytest
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / relative)
    assert spec and spec.loader
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


INSPECT = module("inspect_cit_v02", "inspect_piemonte_cit.py")
BUILDER = module("build_cit_v02", "build_v0_2_cit_preview.py")
REGISTRY = ROOT / "data/municipalities.csv"


def make_sources(tmp_path):
    registry = list(csv.DictReader(REGISTRY.open(encoding="utf-8")))
    assert len(registry) == 27
    outputs = []
    for mode, filename, field, ratio_num, counts in (
        ("fuel", "cit_fuel_27.csv", "diesel_lpg_share_pct", 3,
         {"natural_gas_groups": 7, "diesel_groups": 2,
          "lpg_groups": 1, "solid_fuels_groups": 0,
          "electricity_groups": 0, "other_groups": 0}),
        ("age", "cit_generator_age_27.csv", "older_generator_share_pct", 4,
         {"groups_with_known_year": 10,
          "groups_with_unknown_year": 0, "groups_aged_20_or_more": 4})
    ):
        folder = tmp_path / ("cit_" + mode)
        folder.mkdir()
        path = folder / filename
        result = []
        for town in registry:
            fields = {
                "municipality": town["municipality"],
                "istat_code": town["istat_code"],
                "generator_groups_total": 10,
                "snapshot_date": "2026-08-31",
            }
            if mode == "fuel":
                fields.update({"classified_groups": 10,
                               "unclassified_groups": 0,
                               "denominator": "classified_generator_groups"})
            else:
                fields["denominator"] = "generator_groups_with_known_installation_year"
            fields.update(counts)
            fields[field] = f"{ratio_num * 10:.2f}"
            result.append(fields)
        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(result[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(result)
        qa = {
            "qa_status": "technical_extraction_only",
            "validated_for_release": False,
            "indicator_id": BUILDER.FUEL_INDICATOR if mode == "fuel" else BUILDER.AGE_INDICATOR,
            "source_url": BUILDER.FUEL_SOURCE if mode == "fuel" else BUILDER.AGE_SOURCE,
            "registry_csv_sha256": BUILDER.hash_file(REGISTRY),
            "source_csv_sha256": "b" * 64,
            "output_csv_sha256": BUILDER.hash_file(path),
            "municipalities_expected": 27,
            "municipalities_with_generator_data": 27,
            "missing": [],
            "unclassified_fuel_labels": {},
            "older_years_threshold": 20 if mode == "age" else None,
            "snapshot_date_operator_reported": "2026-08-31",
        }
        (folder / "cit_qa.json").write_text(json.dumps(qa), encoding="utf-8")
        outputs.append(folder)
    return (*outputs, registry)


def test_27_generator_aggregates_load_and_keep_correct_denominators(tmp_path):
    fuel_dir, age_dir, _ = make_sources(tmp_path)
    names = BUILDER.load_registry(REGISTRY)
    f, fs = BUILDER.load_output(fuel_dir, names, BUILDER.hash_file(REGISTRY), "fuel")
    a, ag = BUILDER.load_output(age_dir, names, BUILDER.hash_file(REGISTRY), "age")
    assert len(f) == len(a) == 27
    assert all(x["value"] == 30 for x in f.values())
    assert all(x["value"] == 40 for x in a.values())
    assert fs["sum_numerator"] == 81
    assert ag["sum_numerator"] == 108
    assert fs["sum_denominator"] == ag["sum_denominator"] == 270


def test_bad_fuel_share_is_rejected_even_if_hash_updated(tmp_path):
    fuel_dir, age_dir, _ = make_sources(tmp_path)
    csv_file = fuel_dir / BUILDER.FUELS_CSV
    text = csv_file.read_text(encoding="utf-8").replace("30.00", "99.00", 1)
    csv_file.write_text(text, encoding="utf-8")
    qa_file = fuel_dir / "cit_qa.json"
    qa = json.loads(qa_file.read_text(encoding="utf-8"))
    qa["output_csv_sha256"] = BUILDER.hash_file(csv_file)
    qa_file.write_text(json.dumps(qa), encoding="utf-8")
    with pytest.raises(ValueError, match="does not equal numerator"):
        BUILDER.load_output(fuel_dir, BUILDER.load_registry(REGISTRY),
                            BUILDER.hash_file(REGISTRY), "fuel")


def test_unclassified_or_missing_cit_data_refused(tmp_path):
    fuel_dir, age_dir, _ = make_sources(tmp_path)
    qa_file = fuel_dir / "cit_qa.json"
    qa = json.loads(qa_file.read_text(encoding="utf-8"))
    qa["unclassified_fuel_labels"] = {"Alpette": {"unspecified liquid": 4}}
    qa_file.write_text(json.dumps(qa), encoding="utf-8")
    with pytest.raises(ValueError, match="wrong QA"):
        BUILDER.load_output(fuel_dir, BUILDER.load_registry(REGISTRY),
                            BUILDER.hash_file(REGISTRY), "fuel")


def test_inspector_recognizes_long_csv_and_27_istat_codes(tmp_path):
    raw = tmp_path / "thermal_fuel.csv"
    with raw.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["Key_istat_comune","Desc_combustibile","Numero"],
                                delimiter=";", lineterminator="\n")
        writer.writeheader()
        for record in csv.DictReader(REGISTRY.open(encoding="utf-8")):
            writer.writerow({"Key_istat_comune":record["istat_code"],
                             "Desc_combustibile":"GPL","Numero":"3"})
    info = INSPECT.inspect(raw, REGISTRY, "fuel")
    assert info["source_rows"] == 27
    assert info["selected_27_matched"] == 27
    assert info["suggested_columns"]["category"] == "Desc_combustibile"
    assert info["requires_schema_mapping"] is False
    assert info["category_labels_top_30"][0][0] == "GPL"


def test_build_maps_pdf_and_manifest_with_synthetic_geography(tmp_path, monkeypatch):
    fuel_dir, age_dir, entries = make_sources(tmp_path)
    bounds = tmp_path / "synthetic.zip"
    bounds.write_bytes(b"test-only no original geographical claims")
    features = []
    for i, entry in enumerate(entries):
        x = 7.05 + (i % 9) * .035
        y = 45.05 + (i // 9) * .05
        ring = [[x, y], [x+.025,y], [x+.025,y+.025], [x,y+.025], [x,y]]
        features.append({
            "type":"Feature",
            "properties":{"municipality":entry["municipality"],
                          "municipality_code":entry["istat_code"]},
            "geometry":{"type":"Polygon","coordinates":[ring]},
        })
    geo = {"type":"FeatureCollection",
           "crs":{"type":"name","properties":{"name":"OGC:CRS84"}},
           "features":features}
    monkeypatch.setattr(BUILDER, "parse_boundaries_zip", lambda payload, names: geo)
    result = tmp_path / "report"
    BUILDER.build(fuel_dir, age_dir, REGISTRY, bounds, result)
    expected = {"cit_indicators_27.csv", "cit_indicators_27.geojson",
                "cit_fuel_absolute.png", "cit_fuel_relative.png",
                "cit_age_absolute.png", "cit_age_relative.png",
                "cit_technical_report_v0_2.pdf", "cit_manifest_v0_2.json"}
    assert expected <= {p.name for p in result.iterdir()}
    manifest = json.loads((result/"cit_manifest_v0_2.json").read_text(encoding="utf-8"))
    assert manifest["municipalities"] == 27
    assert manifest["institutional_approval"] == "pending"
    assert len(manifest["outputs_sha256"]) == 7
    content = "\n".join(p.extract_text() or "" for p in
                        PdfReader(result/"cit_technical_report_v0_2.pdf").pages)
    assert BUILDER.TA_CODE in content
    assert "20 anni" in content
    assert "270" in content
    assert "famiglie" in content
    with pytest.raises(FileExistsError):
        BUILDER.build(fuel_dir, age_dir, REGISTRY, bounds, result)
