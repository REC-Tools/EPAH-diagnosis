import io

from openpyxl import Workbook

from epah_diagnosis.altitude import parse_altitude_workbook


def _workbook_bytes(rows):
    workbook = Workbook()
    sheet = workbook.active
    for row in rows:
        sheet.append(row)
    payload = io.BytesIO()
    workbook.save(payload)
    return payload.getvalue()


def test_parse_altitude_workbook_with_flat_header():
    records = parse_altitude_workbook(
        _workbook_bytes(
            [
                ["Comune", "Altitudine media", "Altitudine minima", "Altitudine massima"],
                ["Comune A", 700, 500, 1000],
            ]
        )
    )

    assert len(records) == 1
    assert records[0].mean_altitude_m == 700.0


def test_parse_altitude_workbook_with_multiline_header():
    records = parse_altitude_workbook(
        _workbook_bytes(
            [
                ["", "", "Altitudine", "Altitudine", "Altitudine"],
                ["Codice comune", "Denominazione del comune", "Media", "Minima", "Massima"],
                ["001001", "Comune A", 700, 500, 1000],
            ]
        )
    )

    assert records[0].municipality == "Comune A"
    assert records[0].mean_altitude_m == 700.0


def test_parse_altitude_workbook_skips_descriptive_rows():
    records = parse_altitude_workbook(
        _workbook_bytes(
            [
                ["Codice comune", "Denominazione del comune", "Valore medio", "Valore minimo", "Valore massimo"],
                ["", "Note", "Valore medio della distribuzione (in metri slm)", "Valore minimo della distribuzione (in metri slm)", "Valore massimo della distribuzione (in metri slm)"],
                ["001001", "Comune A", 700, 500, 1000],
            ]
        )
    )

    assert len(records) == 1
    assert records[0].municipality == "Comune A"


def test_parser_distinguishes_mean_from_median_real_istat_labels():
    records = parse_altitude_workbook(
        _workbook_bytes(
            [
                [
                    "Codice comune",
                    "Denominazione del comune",
                    "Valore medio della distribuzione (in metri slm)",
                    "Valore mediano della distribuzione (in metri slm)",
                    "Valore minimo della distribuzione (in metri slm)",
                    "Valore massimo della distribuzione (in metri slm)",
                ],
                ["001001", "Comune A", 710, 650, 500, 1000],
            ]
        )
    )

    assert len(records) == 1
    assert records[0].mean_altitude_m == 710.0
    assert records[0].min_altitude_m == 500.0
    assert records[0].max_altitude_m == 1000.0
