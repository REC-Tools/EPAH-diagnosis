import io

from openpyxl import Workbook

from epah_diagnosis.snai import parse_snai_workbook


def test_parse_snai_workbook():
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Classificazione"
    sheet.append(["Codice", "Comune", "Classificazione SNAI"])
    sheet.append(["001001", "Comune A", "E"])
    sheet.append(["001002", "Comune B", "F - Ultraperiferico"])

    payload = io.BytesIO()
    workbook.save(payload)

    records = parse_snai_workbook(payload.getvalue())

    assert len(records) == 2
    assert records[0].municipality == "Comune A"
    assert records[0].snai_class == "E"
    assert records[0].snai_label == "Periferico"
    assert records[1].snai_class == "F"
    assert records[1].snai_label == "Ultraperiferico"
