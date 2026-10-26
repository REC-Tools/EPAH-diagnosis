from epah_diagnosis.education_access import build_upper_secondary_poles


def test_build_upper_secondary_poles_requires_snai_complete_offer():
    registry = [
        {
            "Regione": "PIEMONTE",
            "CodiceScuola": "A",
            "DescrizioneComune": "Comune Polo",
        },
        {
            "Regione": "PIEMONTE",
            "CodiceScuola": "B",
            "DescrizioneComune": "Comune Polo",
        },
        {
            "Regione": "PIEMONTE",
            "CodiceScuola": "C",
            "DescrizioneComune": "Comune Solo Liceo",
        },
    ]

    pathways = [
        {
            "CodiceScuola": "A",
            "TipoPercorso": "Liceo",
            "Percorso": "Scientifico",
        },
        {
            "CodiceScuola": "B",
            "TipoPercorso": "Tecnico",
            "Percorso": "Tecnologico",
        },
        {
            "CodiceScuola": "C",
            "TipoPercorso": "Liceo",
            "Percorso": "Classico",
        },
    ]

    poles = build_upper_secondary_poles(registry, pathways)
    names = {pole.municipality for pole in poles}

    assert names == {"Comune Polo"}


def test_build_upper_secondary_poles_handles_uppercase_mim_columns():
    registry = [
        {
            "REGIONE": "PIEMONTE",
            "CODICESCUOLA": "A",
            "DESCRIZIONECOMUNE": "Comune Polo",
        },
        {
            "REGIONE": "PIEMONTE",
            "CODICESCUOLA": "B",
            "DESCRIZIONECOMUNE": "Comune Polo",
        },
    ]

    pathways = [
        {
            "CODICESCUOLA": "A",
            "TIPOPERCORSO": "LICEO",
            "PERCORSO": "SCIENTIFICO",
        },
        {
            "CODICESCUOLA": "B",
            "TIPOPERCORSO": "TECNICO",
            "PERCORSO": "TECNOLOGICO",
        },
    ]

    poles = build_upper_secondary_poles(registry, pathways)

    assert [pole.municipality for pole in poles] == ["Comune Polo"]
