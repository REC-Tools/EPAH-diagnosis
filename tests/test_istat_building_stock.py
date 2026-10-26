from epah_diagnosis.istat_building_stock import (
    filter_by_codes,
    parse_section_csv,
    weighted_share_pre_1981,
)


def test_aggregate_sections_to_municipality():
    text = (
        "PRO_COM;SEZ2011;E3;E8;E9;E10;E11;E12;E13;E14;E15;E16\n"
        "001001;0010010000001;10;1;1;1;1;1;2;1;1;1\n"
        "001001;0010010000002;20;2;2;2;2;2;4;2;2;2\n"
        "001002;0010020000001;10;0;0;0;1;1;2;2;2;2\n"
    )

    result = parse_section_csv(text)
    selected = filter_by_codes(result, {"001001"})

    assert len(result) == 2
    assert len(selected) == 1
    item = selected[0]
    assert item.residential_buildings_total == 30
    assert item.buildings_pre_1981 == 15
    assert item.share_pre_1981 == 50.0
    assert weighted_share_pre_1981(selected) == 50.0
