from epah_diagnosis.istat_building_stock import filter_municipalities, parse_regional_csv


def test_filter_building_stock_municipalities():
    text = (
        "PRO_COM_T;Comune;ANNO;A9;A10\n"
        "001001;Comune A;2011;2,5;18,4\n"
        "001002;Comune B;2011;0,8;9,2\n"
    )

    parsed = parse_regional_csv(text)
    selected = filter_municipalities(parsed, {"Comune A"})

    assert len(selected) == 1
    assert selected[0].municipality == "Comune A"
    assert selected[0].historic_occupied_dwellings_pct == 18.4
