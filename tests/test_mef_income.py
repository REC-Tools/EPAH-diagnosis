from epah_diagnosis.mef_income import parse_mef_rows


def test_income_vulnerability_proxy():
    rows = [
        {
            "Codice comune": "001001",
            "Denominazione Comune": "Comune A",
            "Numero contribuenti": "100",
            "Reddito complessivo minore o uguale a zero euro": "5",
            "Reddito complessivo da 0 a 10000 euro": "20",
            "Reddito complessivo da 10000 a 15000 euro": "15",
        }
    ]

    result = parse_mef_rows(rows)

    assert len(result) == 1
    assert result[0].taxpayers_income_le_15000 == 40
    assert result[0].share_income_le_15000 == 40.0
