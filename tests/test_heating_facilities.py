from epah_diagnosis.heating_facilities import parse_section_csv


def test_parse_heating_facilities_from_section_rows():
    text = (
        "PROCOM;SEZ2011;A2;A24\n"
        "001007;1;100;95\n"
        "001007;2;50;45\n"
        "001008;1;40;40\n"
    )

    records = parse_section_csv(text)

    assert len(records) == 2
    alpette = next(item for item in records if item.municipality_code == "001007")
    assert alpette.occupied_dwellings == 150
    assert alpette.occupied_dwellings_with_heating == 140
    assert alpette.heating_gap_pct == 6.67
