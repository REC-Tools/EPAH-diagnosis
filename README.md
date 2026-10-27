# EPAH Diagnosis — Sinergie in Canavese

Strumento open-data per supportare la diagnosi territoriale della povertà energetica nei **27 Comuni** della Green Community. Usa dati aggregati e proxy: **non identifica famiglie in povertà energetica** e non produce un indice EPAH certificato.

## Iniziare
Installazione in un ambiente Python 3.11+:
```bash
python -m pip install -e .
python -m pip install pytest
pytest -q
python scripts/check_framework.py
python -m epah_diagnosis.cli validate-matrix data/verification_matrix.csv --catalog config/indicators.json
```

## Stato e limiti
- Il **core v0.1** contiene **9** dimensioni integrate e validate: vulnerabilità, contesto e accessibilità. Le pipeline #10–#15 sono estensioni non bloccanti e sono tracciate in `config/release_v0_1.json`.
- `data/verification_matrix.csv` include **243 combinazioni** (27 × 9); la presenza di una riga non implica la disponibilità del valore. Per ogni indicatore va controllato il campo `status`.
- Le 81 osservazioni storiche sono conservate in `data/reference/verification_matrix_baseline_81.csv`.
- I dati climatici presenti derivano da uno snapshot locale; l'acquisizione non equivale alla validazione indipendente della fonte normativa.
- Le ulteriori schede su impianti di riscaldamento e SIPEE/APE sono **sperimentali** e non sono ancora parte del catalogo a nove indicatori.
- Alcuni script dipendono da download di fonte ufficiale, non esercitati nella CI offline.
- `model.py` e l'inizializzazione CLI senza catalogo supportano soltanto il vecchio schema a tre indicatori: **non usare `init-matrix` per sovrascrivere la matrice corrente**.

## Controlli e profili
```bash
python scripts/check_framework.py
python -m epah_diagnosis.cli validate-matrix data/verification_matrix.csv --catalog config/indicators.json
python scripts/check_integrated_profile_readiness.py
```
Il controllo di readiness termina con errore finché non risultano disponibili e validati i nove indicatori per tutti i 27 Comuni. Non è un errore della CI: è un'indicazione di incompletezza della diagnosi. I profili completi si generano con `scripts/build_municipality_profile.py` **solo dopo** tale verifica.

## Documentazione
- [Framework metodologico](docs/framework.md), [catalogo](docs/indicator_catalog.md), [criteri di completamento](docs/indicator_completion_criteria.md).
- [Flusso dati](docs/pipeline.md), [contratto degli artefatti](docs/data_contract.md), [provenienza](docs/provenance.md).
- [Governance](docs/governance.md) e [audit generale](docs/repository_quality_audit.md).
- [Acquisizione edilizia](docs/building_stock_finalization.md), [stato clima](docs/indicator_04_completion_status.md).
- [Schema accessibilità](docs/indicator_07_dea_accessibility.md), [scuole](docs/indicator_08_upper_secondary_accessibility.md), [ferrovia](docs/indicator_09_rail_accessibility.md).

## Principio operativo
Ogni pubblicazione deve separare indicatore, fonte, anno, stato di verifica e limitazioni. Le mappe e il report rappresentano dimensioni distinte; nessun punteggio composito automatico.
\n\n## Release v0.1\nLa definizione operativa della prima release è in [docs/release_v0_1.md](docs/release_v0_1.md). Il core resta separato dalle estensioni che dipendono da SIPEE, Copernicus o raccolta locale.\n