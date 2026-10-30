"""Synthetic tests for the 2025 Ministry DEA XLSX extractor."""
import csv
import importlib.util
import io
from pathlib import Path

import pytest
from openpyxl import Workbook

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audit_dea_2025_source.py"
SPEC = importlib.util.spec_from_file_location("audit_dea_2025_source", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def make_book(path, *, levels=("DEA1", "DEA2", "PS"), years=None, duplicate=False):
    wb = Workbook()
    ws = wb.active
    ws.title = "Strutture_Emergenza_2025"
    ws.append(["Anno", "Codice Regione", "Codice struttura", "Subcodice",
               "Denominazione struttura", "Comune", "Livello Emergenza"])
    years = years or ("2025",) * len(levels)
    for i, (level, year) in enumerate(zip(levels, years)):
        ws.append([year, "010", "010001" if duplicate else f"01000{i+1}",
                   "01", f"Facility {i}", "PONDERANO" if i == 0 else "BIELLA", level])
    ws.append(["2025", "020", "020001", "01", "Aosta DEA", "AOSTA", "DEA2"])
    wb.save(path)


def test_filters_piemonte_dea_and_preserves_codes(tmp_path):
    path = tmp_path / "official.xlsx"
    make_book(path)
    rows, report = MODULE.extract(path)
    assert len(rows) == 2
    assert report["piemonte_rows"] == 3
    assert report["piemonte_levels"]["PS"] == 1
    assert rows[0]["municipality"] == "Ponderano"
    assert "010001" in rows[0]["source"]
    assert report["validated_for_release"] is False
    assert report["route_times_recomputed"] is False


def test_rejects_wrong_year(tmp_path):
    path = tmp_path / "wrong.xlsx"
    make_book(path, years=("2024", "2025", "2025"))
    with pytest.raises(ValueError, match="2025 records"):
        MODULE.extract(path)


def test_rejects_duplicate_facility_code_and_subcode(tmp_path):
    path = tmp_path / "duplicate.xlsx"
    make_book(path, duplicate=True)
    with pytest.raises(ValueError, match="duplicated Ministry facility key"):
        MODULE.extract(path)


def test_csv_contract_is_deterministic(tmp_path):
    path = tmp_path / "official.xlsx"
    make_book(path)
    rows, _ = MODULE.extract(path)
    payload = MODULE.candidate_csv(rows)
    parsed = list(csv.DictReader(io.StringIO(payload.decode("utf-8"))))
    assert len(parsed) == 2
    assert list(parsed[0]) == list(MODULE.FIELDS)
    assert b"\r\n" not in payload
