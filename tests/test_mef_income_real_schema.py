from epah_diagnosis.mef_income import read_mef_csv


def test_mef_parser_with_official_style_headers():
    text = (
        "Anno di imposta;Codice catastale;Codice Istat Comune;"
        "Denominazione Comune;Sigla Provincia;Regione;Codice Istat Regione;"
        "Numero contribuenti;Reddito complessivo - Frequenza;"
        "Reddito complessivo - Ammontare in euro;"
        "Reddito complessivo minore o uguale a zero euro - Frequenza;"
        "Reddito complessivo minore o uguale a zero euro - Ammontare in euro;"
        "Reddito complessivo da 0 a 10000 euro - Frequenza;"
        "Reddito complessivo da 0 a 10000 euro - Ammontare in euro;"
        "Reddito complessivo da 10000 a 15000 euro - Frequenza;"
        "Reddito complessivo da 10000 a 15000 euro - Ammontare in euro\n"
        "2024;A001;001001;Comune A;TO;Piemonte;1;100;"
        "100;2500000;5;-1000;20;100000;15;180000\n"
    )

    result = read_mef_csv(text)

    assert len(result) == 1
    item = result[0]
    assert item.municipality_code == "001001"
    assert item.region == "Piemonte"
    assert item.taxpayers_total == 100
    assert item.taxpayers_income_le_15000 == 40
    assert item.share_income_le_15000 == 40.0
    assert item.mean_total_income_eur == 25000.0
