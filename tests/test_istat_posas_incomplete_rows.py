from epah_diagnosis.istat_posas import read_posas_csv


def test_posas_parser_skips_incomplete_rows():
    text = (
        "Popolazione residente per età e sesso al 1° gennaio 2026 (stima);\n"
        "Codice Comune;Comune;Età;Totale\n"
        ";;;;\n"
        "001001;;65;20\n"
        "001001;Comune A;;20\n"
        "001001;Comune A;64;60\n"
        "001001;Comune A;65;20\n"
        "001001;Comune A;80;20\n"
        "001001;Comune A;999;100\n"
    )

    result = read_posas_csv(text)

    assert len(result) == 1
    assert result[0].municipality == "Comune A"
    assert result[0].population_total == 100
    assert result[0].population_65_plus == 40
