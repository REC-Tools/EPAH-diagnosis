import pytest

from epah_diagnosis.local_affordability import (
    MIN_RESPONDENTS,
    filter_municipalities,
    parse_affordability_csv,
)


def test_parse_and_calculate_affordability_shares():
    text = (
        "municipality;respondents;unable_warm_yes;utility_arrears_yes;"
        "unable_cool_yes;reduced_heating_cost_yes\n"
        "Alpette;20;5;2;6;7\n"
    )

    records = parse_affordability_csv(text)
    item = records[0]

    assert item.respondents == 20
    assert item.share("unable_warm_yes") == 25.0
    assert item.share("utility_arrears_yes") == 10.0


def test_small_sample_is_suppressed():
    text = (
        "municipality;respondents;unable_warm_yes;utility_arrears_yes;"
        "unable_cool_yes;reduced_heating_cost_yes\n"
        f"Alpette;{MIN_RESPONDENTS - 1};2;1;2;3\n"
    )

    item = parse_affordability_csv(text)[0]
    assert item.share("unable_warm_yes") is None


def test_yes_counts_cannot_exceed_respondents():
    text = (
        "municipality;respondents;unable_warm_yes;utility_arrears_yes;"
        "unable_cool_yes;reduced_heating_cost_yes\n"
        "Alpette;10;11;0;0;0\n"
    )

    with pytest.raises(ValueError, match="Invalid unable_warm_yes"):
        parse_affordability_csv(text)


def test_all_requested_municipalities_are_required():
    text = (
        "municipality;respondents;unable_warm_yes;utility_arrears_yes;"
        "unable_cool_yes;reduced_heating_cost_yes\n"
        "Alpette;10;1;1;1;1\n"
    )

    records = parse_affordability_csv(text)
    with pytest.raises(ValueError, match="Borgiallo"):
        filter_municipalities(records, {"Alpette", "Borgiallo"})
