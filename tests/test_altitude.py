import io

from openpyxl import Workbook

from epah_diagnosis.altitude import parse_altitude_workbook


def test_parse_altitude_workbook_detects_mean_altitude():
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Altimetria"
    sheet.append(["Codice", "Comune", "Altitudine media", "Altitudine minima", "Altitudine massima"])
    sheet.append(["001001", "Comune A", 850.5, 500, 1200])

    payload = io.BytesIO()
    workbook.save(payload)

    records = parse_altitude_workbook(payload.getvalue())

    assert len(records) == 1
    assert records[0].municipality == "Comune A"
    assert records[0].mean_altitude_m == 850.5
    assert records[0].min_altitude_m == 500.0
    assert records[0].max_altitude_m == 1200.0
