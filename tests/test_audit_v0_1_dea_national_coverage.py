"""Synthetic tests: no approval is inferred from national DEA audit."""
import importlib.util
import zipfile
from pathlib import Path
import pytest
from openpyxl import Workbook

FILE = Path(__file__).resolve().parents[1] / "scripts/audit_v0_1_dea_national_coverage.py"
SPEC = importlib.util.spec_from_file_location("national_audit", FILE)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_original_route_values_and_source_location(tmp_path):
    path = tmp_path / "roads.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("R01.csv", "OR_PROCOM;DEST_PROCOM;TEP_TOT;KM_TOT\n001073;007003;22,5;31,3\n001073;001086;71;64,1\n")
    routes = MODULE.read_road(path, {"001073"}, {"007003", "001086"})
    assert routes[("001073", "007003")] == (22.5, 31.3, "R01.csv", 2)
    assert routes[("001073", "001086")] == (71, 64.1, "R01.csv", 3)


def test_duplicate_route_is_rejected(tmp_path):
    path = tmp_path / "roads.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("R01.csv", "OR_PROCOM;DEST_PROCOM;TEP_TOT;KM_TOT\n001073;007003;1;2\n001073;007003;1;2\n")
    with pytest.raises(ValueError, match="Duplicated official road pair"):
        MODULE.read_road(path, {"001073"}, {"007003"})


def test_nan_source_fails_closed(tmp_path):
    path = tmp_path / "roads.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("R01.csv", "OR_PROCOM;DEST_PROCOM;TEP_TOT;KM_TOT\n001073;007003;NaN;2\n")
    with pytest.raises(ValueError, match="Invalid official road time"):
        MODULE.read_road(path, {"001073"}, {"007003"})


def test_ministry_region_alias_and_eligibility(tmp_path):
    source = tmp_path / "ministry.xlsx"
    book = Workbook()
    sheet = book.active
    sheet.title = "Strutture_Emergenza_2025"
    sheet.append(["Anno", "Codice Regione", "Comune", "Livello Emergenza", "Denominazione struttura"])
    for region, town, level in [("010", "IVREA", "DEA1"), ("020", "AOSTA", "DEA2"),
                                 ("041", "BOLZANO", "DEA1"), ("010", "CUORGNE", "PS")]:
        sheet.append(["2025", region, town, level, "Example"])
    book.save(source)
    official = {(1, "ivrea"): {"001125"}, (2, "aosta"): {"007003"}, (4, "bolzanobozen"): {"021008"}}
    sites, missing, summary = MODULE.national_dea(source, official)
    assert not missing
    assert sites["007003"]["region"] == "020"
    assert summary["national_dea_facilities"] == 3
    assert summary["outside_dea_municipalities"] == 2
    assert len(summary["historical_name_aliases_to_review"]) == 1


def test_ambiguous_place_does_not_select_random_code(tmp_path):
    source = tmp_path / "ministry.xlsx"
    book = Workbook()
    sheet = book.active
    sheet.title = "Strutture_Emergenza_2025"
    sheet.append(["Anno", "Codice Regione", "Comune", "Livello Emergenza", "Denominazione struttura"])
    sheet.append(["2025", "010", "IVREA", "DEA1", "Example"])
    book.save(source)
    _, missing, _ = MODULE.national_dea(source, {(1, "ivrea"): {"001125", "001999"}})
    assert len(missing) == 1
