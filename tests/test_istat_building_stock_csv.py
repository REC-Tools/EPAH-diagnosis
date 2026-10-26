from epah_diagnosis.istat_building_stock import parse_regional_csv


def test_parse_regional_csv():
    text = (
        "PRO_COM_T;Comune;ANNO;A9;A10\n"
        "001001;Comune A;2001;1,1;12,0\n"
        "001001;Comune A;2011;2,5;18,4\n"
        "001002;Comune B;2011;0,8;9,2\n"
    )

    result = parse_regional_csv(text)

    assert len(result) == 2
    assert result[0].municipality_code == "001001"
    assert result[0].historic_occupied_dwellings_pct == 18.4
    assert result[0].poor_condition_buildings_pct == 2.5
