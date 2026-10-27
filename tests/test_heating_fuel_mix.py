from epah_diagnosis.heating_fuel_mix import (
    filter_municipalities,
    parse_heating_fuel_mix_csv,
)


def test_parse_heating_fuel_mix_and_non_gas_share():
    text = (
        "Comune;Metano;Gasolio;GPL;Combustibile solido;"
        "Olio combustibile;Energia elettrica;Altro\n"
        "Alpette;40;10;20;20;0;5;5\n"
        "Borgiallo;80;5;5;5;0;5;0\n"
    )

    records = parse_heating_fuel_mix_csv(text)
    selected = filter_municipalities(records, {"Alpette", "Borgiallo"})

    alpette = next(item for item in selected if item.municipality == "Alpette")

    assert alpette.heated_dwellings_total == 100
    assert alpette.natural_gas == 40
    assert alpette.non_natural_gas_share_pct == 60.0


def test_italian_semicolon_export_is_not_confused_by_labels():
    text = (
        "Denominazione comune;Gas naturale;Gasolio;GPL;Legna/Carbone;"
        "Olio combustibile;Elettricita;Altro combustibile o energia\n"
        "Alpette;10;2;3;20;0;5;1\n"
    )

    records = parse_heating_fuel_mix_csv(text)

    assert len(records) == 1
    assert records[0].municipality == "Alpette"
    assert records[0].solid_fuel == 20
