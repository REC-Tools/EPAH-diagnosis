from epah_diagnosis.mef_income import parse_mef_rows


def test_income_vulnerability_proxy():
    rows = [
        {
            "Codice Istat Comune": "001001",
            "Denominazione Comune": "Comune A",
            "Regione": "Piemonte",
            "Numero contribuenti": "100",
            "Reddito complessivo - Frequenza": "100",
            "Reddito complessivo - Ammontare in euro": "2500000",
            "Reddito complessivo minore o uguale a zero euro - Frequenza": "5",
            "Reddito complessivo da 0 a 10000 euro - Frequenza": "20",
            "Reddito complessivo da 10000 a 15000 euro - Frequenza": "15",
        }
    ]

    result = parse_mef_rows(rows)

    assert len(result) == 1
    assert result[0].region == "Piemonte"
    assert result[0].taxpayers_income_le_15000 == 40
    assert result[0].share_income_le_15000 == 40.0
    assert result[0].mean_total_income_eur == 25000.0
