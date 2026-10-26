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


def test_parse_real_snai_2020_header_schema():
    workbook = Workbook()
    readme = workbook.active
    readme.title = "LEGGIMI"
    readme.append(["Descrizione dei contenuti del file"])

    sheet = workbook.create_sheet("DATI")
    sheet.append(["Mappa Aree Interne 2020"])
    sheet.append([])
    sheet.append([
        "PROCOM_T",
        "COD_REG",
        "REGIONE",
        "COD_PROV",
        "SIGLA AUTOM.",
        "PROVINCIA/CITTA' METROPOLITANA",
        "COMUNE_30sett20",
        "FLAG CAPOLUOGO",
        "Superficie territoriale (kmq) al 01/01/2019",
        "Popolazione residente censimento 2020",
        "MAPPA AI 2020\n\nCOD_AI_2020",
        "MAPPA AI 2020\n\nDES_AI_2020",
        "MAPPA AI 2020\n\nMEDIA tempi di percorrenza",
    ])
    sheet.append([
        "001007", 1, "Piemonte", 201, "TO", "Torino", "Alpette", 0,
        5.6261, 235, "E", "E - Periferico", 42.2,
    ])
    sheet.append([
        "001008", 1, "Piemonte", 201, "TO", "Torino", "Alpignano", 0,
        11.9193, 16484, "B", "B - Polo intercomunale", 0,
    ])

    payload = io.BytesIO()
    workbook.save(payload)

    records = parse_snai_workbook(payload.getvalue())

    assert len(records) == 2
    assert records[0].municipality == "Alpette"
    assert records[0].snai_class == "E"
    assert records[0].snai_label == "Periferico"
    assert records[1].municipality == "Alpignano"
    assert records[1].snai_class == "B"
