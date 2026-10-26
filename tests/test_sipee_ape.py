from epah_diagnosis.sipee_ape import (
    aggregate_by_municipality,
    parse_sipee_csv,
)


def test_parse_and_aggregate_sipee_export():
    text = (
        "Comune;Classe energetica;EPgl,nren\n"
        "Alpette;G;280,5\n"
        "Alpette;D;140,0\n"
        "Borgiallo;F;210,0\n"
    )

    records = parse_sipee_csv(text)
    summaries = aggregate_by_municipality(
        records,
        {"Alpette", "Borgiallo"},
    )

    alpette = next(item for item in summaries if item.municipality == "Alpette")
    assert alpette.total_apes == 2
    assert alpette.poor_class_apes == 1
    assert alpette.poor_class_share_pct == 50.0
    assert alpette.class_counts["G"] == 1
    assert alpette.class_counts["D"] == 1
    assert alpette.epgl_nren_median == 210.25


def test_semicolon_delimiter_wins_over_decimal_and_header_commas():
    text = (
        "Comune;Classe energetica;EPgl,nren\n"
        "Alpette;G;280,5\n"
    )

    records = parse_sipee_csv(text)

    assert len(records) == 1
    assert records[0].municipality == "Alpette"
    assert records[0].energy_class == "G"
    assert records[0].epgl_nren == 280.5
