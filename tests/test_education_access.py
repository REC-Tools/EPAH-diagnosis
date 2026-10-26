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
