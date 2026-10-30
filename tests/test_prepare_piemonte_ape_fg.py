"""Synthetic checks for Piemonte APE extraction; no real APE values in CI."""
import csv
import importlib.util
import json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "ape", ROOT / "scripts/prepare_piemonte_ape_fg.py")
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


def fixture(tmp_path, *, missing=False, bad=False, selected_duplicate=False):
    rows = list(csv.DictReader((ROOT / "data/municipalities.csv").open(
        encoding="utf-8", newline="")))
    source = tmp_path / "source.csv"
    with source.open("w", encoding="utf-8", newline="") as f:
        fields = ["Key_istat_comune", "Desc_comune",
                  *MOD.CLASSES, "Data_aggiornamento_record"]
        writer = csv.DictWriter(f, fieldnames=fields, delimiter=";", lineterminator="\n")
        writer.writeheader()
        for i, entry in enumerate(rows):
            if missing and i == 0:
                continue
            item = {"Key_istat_comune": entry["istat_code"],
                    "Desc_comune": entry["municipality"],
                    "Data_aggiornamento_record": "2026-08-31T00:00:00.000Z",
                    **{c: "1" for c in MOD.CLASSES}}
            if bad and i == 0:
                item["Classe_g"] = "-1"
            writer.writerow(item)
            if selected_duplicate and i == 0:
                writer.writerow(item)
        for name in ("OLD MUNICIPALITY", "RENAMED MUNICIPALITY"):
            writer.writerow({"Key_istat_comune": "005014", "Desc_comune": name,
                             "Data_aggiornamento_record": "2026-08-31T00:00:00.000Z",
                             **{c: "3" for c in MOD.CLASSES}})
    return source


def test_27_values_and_valid_provenance(tmp_path):
    source = fixture(tmp_path)
    rows, report = MOD.prepare(source, ROOT / "data/municipalities.csv")
    assert len(rows) == 27
    assert report["ape_count_27"] == 270
    assert report["ape_fg_count_27"] == 54
    assert report["pooled_fg_share_pct"] == 20
    assert report["snapshot_date"] == "2026-08-31"
    assert len(report["duplicate_codes_outside_study"]) == 1
    assert report["validated_as_residential_share"] is False
    assert all(r["denominator"] == "all_ape" for r in rows)


def test_missing_municipality_fails(tmp_path):
    with pytest.raises(ValueError, match="Missing Green Community codes"):
        MOD.prepare(fixture(tmp_path, missing=True), ROOT / "data/municipalities.csv")


def test_negative_count_fails(tmp_path):
    with pytest.raises(ValueError, match="Negative or noncanonical"):
        MOD.prepare(fixture(tmp_path, bad=True), ROOT / "data/municipalities.csv")


def test_duplicate_27_code_fails(tmp_path):
    with pytest.raises(ValueError, match="Duplicate selected"):
        MOD.prepare(fixture(tmp_path, selected_duplicate=True), ROOT / "data/municipalities.csv")


def test_csv_delimiter_is_semicolon(tmp_path):
    path = fixture(tmp_path)
    with path.open(encoding="utf-8") as f:
        assert f.readline().startswith("Key_istat_comune;")
