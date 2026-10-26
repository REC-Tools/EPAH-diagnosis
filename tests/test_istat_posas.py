from epah_diagnosis.istat_posas import calculate_65_plus_from_rows


def test_calculates_share_65_plus_and_ignores_total_row():
    rows = [
        {"codice": "001001", "comune": "Comune A", "eta": "64", "totale": "60"},
        {"codice": "001001", "comune": "Comune A", "eta": "65", "totale": "20"},
        {"codice": "001001", "comune": "Comune A", "eta": "80", "totale": "20"},
        {"codice": "001001", "comune": "Comune A", "eta": "999", "totale": "100"},
    ]

    result = calculate_65_plus_from_rows(rows)

    assert len(result) == 1
    assert result[0].population_total == 100
    assert result[0].population_65_plus == 40
    assert result[0].share_65_plus == 40.0
