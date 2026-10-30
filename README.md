# EPAH Diagnosis — Sinergie in Canavese

Toolkit open-data per la diagnosi territoriale della povertà energetica nei **27 Comuni** della Green Community. Nove indicatori distinti su vulnerabilità socioeconomica, patrimonio edilizio, clima, territorio e accessibilità. I dati sono comunali: non identificano famiglie in povertà energetica e non costituiscono un indice EPAH certificato.

## V0.1.0 pilota tecnico

La [decisione tecnica dell'esperto](docs/reviews/v0_1_owner_acceptance_20261030.md) è del **30 ottobre 2026**; la valutazione istituzionale dell'Unione Montana sarà successiva. La release pilota include **27 Comuni × 9 indicatori (243 osservazioni)**, con tempi stradali ISTAT verso elenchi selezionati di servizi e **9/9 controlli campione** corrispondenti all'originale ISTAT. Non sono stime porta-a-porta né minimi nazionali garantiti.

Dalla root del repository, con Python 3.11+ e originali/bozze QA già disponibili localmente:

    git switch main
    git pull --ff-only origin main
    python -m pip install -e .
    python scripts/build_v0_1_owner_accepted.py

Risultati:
- **outputs/v0.1.0-pilot/**: CSV, GeoJSON, nove mappe, XLSX, rapporto PDF, manifest.
- **outputs/epah_diagnosis_v0.1.0_pilot.zip**: archivio condivisibile.

Il builder pilota non modifica la matrice o il catalogo versionati. Se il bundle esiste già, il programma lo preserva e richiede nomi di output nuovi. [Istruzioni e prerequisiti](docs/v0_1_owner_accepted_release.md).

**Due percorsi distinti:** l'approvazione tecnica del pilota non equivale alla promozione nella matrice canonica. Su Git restano **162/243** osservazioni con stato Dato validato, 81 da verificare e nove review metodologiche canoniche non registrate. Il builder canonico mantiene il proprio gate. Non risulta ancora una GitHub Release pubblicata con asset scaricabili.

## Qualità e manutenzione

    python -m pytest -q
    python scripts/check_documentation.py
    python scripts/check_framework.py
    python scripts/check_municipality_registry.py
    python scripts/check_v0_1_readiness.py --phase inputs --report-only

La modalità report-only non attesta che la release canonica sia pronta. Le estensioni APE, ERA5 e affordability non bloccano il pilota.

## Documentazione da usare

- [Guida operativa](docs/operational_guide.md) · [Script e comandi](docs/script_reference.md)
- [Perimetro e limiti](docs/release_v0_1_scope_27.md) · [Builder pilota](docs/v0_1_owner_accepted_release.md)
- [Metodologia](docs/framework.md) · [Nove indicatori](docs/indicator_catalog.md)
- [Mappe](docs/diagnostic_maps.md) · [Geografia](docs/geography.md)
- [Gate canonico](docs/release_v0_1.md) · [Protezione PR e dati](docs/data_change_protection.md)
- [Storico degli audit](docs/archive/README.md)

GeoJSON in **CRS84/WGS84**, rendering PNG in **EPSG:32632** (metri) per preservare le proporzioni. Non pubblicare archivi originali, token o dati personali. [Licenza](LICENSE).
