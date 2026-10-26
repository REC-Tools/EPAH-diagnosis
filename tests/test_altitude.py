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


def test_parse_real_istat_altitude_columns():
    records = parse_altitude_workbook(
        _workbook_bytes(
            [
                ["DATI COMUNALI", "DATI ALTIMETRICI ESPRESSI IN METRI S.L.M"],
                [
                    "COD_RIP", "COD_REG", "COD_UTS", "TIPO_UTS", "PRO_COM",
                    "COMUNE", "COMUNE_A", "AREA_KMQ", "ALT MIN", "ALT MAX",
                    "RANGE", "MEDIA", "MEDIANA", "ALT CENTR MUN", "STD"
                ],
                [
                    1, 1, 201, 3, 1007, "Alpette", None, 5.6311,
                    462, 1642, 1180, 1017.86887590892, 985, 961, 258.6268,
                ],
            ]
        )
    )

    assert len(records) == 1
    assert records[0].municipality == "Alpette"
    assert records[0].mean_altitude_m == 1017.86887590892
    assert records[0].min_altitude_m == 462.0
    assert records[0].max_altitude_m == 1642.0
