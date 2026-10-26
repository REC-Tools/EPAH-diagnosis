import io

from openpyxl import Workbook

from epah_diagnosis.altitude import parse_altitude_workbook


def _save(workbook: Workbook) -> bytes:
    payload = io.BytesIO()
    workbook.save(payload)
    return payload.getvalue()


def test_parse_altitude_workbook_detects_mean_altitude():
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Altimetria"
    sheet.append(["Codice", "Comune", "Altitudine media", "Altitudine minima", "Altitudine massima"])
    sheet.append(["001001", "Comune A", 850.5, 500, 1200])

    records = parse_altitude_workbook(_save(workbook))

    assert len(records) == 1
    assert records[0].municipality == "Comune A"
    assert records[0].mean_altitude_m == 850.5
    assert records[0].min_altitude_m == 500.0
    assert records[0].max_altitude_m == 1200.0


def test_parse_altitude_workbook_handles_multiline_headers():
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Comuni 31_12_2021"
    sheet.append(["", "", "Altitudine", "Altitudine", "Altitudine"])
    sheet.append(["Codice comune", "Denominazione del comune", "Media", "Minima", "Massima"])
    sheet.append(["001001", "Comune A", 850.5, 500, 1200])

    records = parse_altitude_workbook(_save(workbook))

    assert len(records) == 1
    assert records[0].municipality == "Comune A"
    assert records[0].mean_altitude_m == 850.5


def test_parse_altitude_workbook_skips_description_rows():
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Comuni 31_12_2021"
    sheet.append(["", "", "Altitudine", "Altitudine", "Altitudine"])
    sheet.append(["Codice comune", "Denominazione del comune", "Media", "Minima", "Massima"])
    sheet.append([
        "",
        "Note",
        "Valore medio della distribuzione (in metri slm)",
        "Valore minimo della distribuzione (in metri slm)",
        "Valore massimo della distribuzione (in metri slm)",
    ])
    sheet.append(["001001", "Comune A", 850.5, 500, 1200])

    records = parse_altitude_workbook(_save(workbook))

    assert len(records) == 1
    assert records[0].municipality == "Comune A"
    assert records[0].mean_altitude_m == 850.5
