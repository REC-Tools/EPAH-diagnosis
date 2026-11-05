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

## CLI unificata (per nuovi flussi)

Con l'ambiente bloccato e la repository installata in modalità editable:

    uv sync --python 3.11 --locked --group dev
    uv run --locked epah status
    uv run --locked epah sources check
    uv run --locked epah data validate

La build richiede una scelta esplicita (`epah build --profile pilot` oppure
`--profile canonical`). I builder e i gate di revisione originali restano
attivi; nessun comando promuove automaticamente dati. [Guida CLI](docs/unified_cli.md).

## Inventario dei file locali

Per controllare dati non tracciati, archivi originali e artefatti di lavoro
senza modificarli:

    uv run --locked epah local audit

Il controllo distingue percorsi ignorati, non tracciati e file versionati
modificati; non autorizza pubblicazione o promozione nella matrice canonica.
[Guida all'inventario locale](docs/local_artifact_inventory.md).

## Pipeline tecnica (senza pubblicazione)

`epah pipeline plan --profile cit-quarantine ...` mostra la sequenza
di verifica degli originali, preparazione CIT e QA interna 26/27.
`epah pipeline run ...` la esegue **solo** verso una cartella nuova
in `outputs/quality/`. Per l'accessibilità è disponibile il solo
profilo di acquisizione/audit `accessibility-intake`, con eventuali
download esclusivamente su richiesta esplicita.

Pont Canavese rimane escluso dai valori CIT in conflitto; nessuna
revisione umana è sostituita dall'automazione.
[Comandi ed esempi](docs/automated_technical_pipeline.md).

## Dossier di revisione CIT Pont Canavese

Da una run CIT tecnica verificata si può generare un dossier interno
con righe originali discordanti, hash QA e bozza di richiesta ufficiale:

    uv run --locked epah cit review-packet --run-dir outputs/quality/RUN_CIT --out-dir outputs/quality/NUOVO_DOSSIER

Il comando non risolve il conflitto, non invia email e non promuove dati.
[Guida alla revisione della fonte](docs/cit_source_review_packet.md).

## Diagnosi territoriale v0.2 - rapporto tecnico

Senza attendere le fonti CIT ancora da chiarire, è disponibile
un renderer v0.2 separato dal bundle v0.1 accettato tecnicamente:

    uv run --locked epah report v0.2 --bundle outputs/v0.1.0-pilot --out-dir outputs/v0.2-territorial-technical

Produce PDF, statistiche JSON e manifest di provenienza,
con due mappe del pilota integrate e lettura incrociata
non causale. Output `technical_draft_do_not_publish`,
non una release istituzionale.
[Guida completa](docs/v0_2_territorial_report.md).

## Schede comunali v0.2

Una pagina PDF per ciascuno dei 27 Comuni, con nove indicatori
separati, mediana comunale, anni e cautele interpretative:

    uv run --locked epah sheets v0.2 --bundle outputs/v0.1.0-pilot --out-dir outputs/v0.2-municipal-sheets

[Guida e limiti](docs/v0_2_municipal_sheets.md).

## Analisi multidimensionale v0.2

Confronto dei singoli indicatori e 28 co-occorrenze
descrittive fra coppie, senza indice cumulativo:

    uv run --locked epah analysis v0.2 --bundle outputs/v0.1.0-pilot --out-dir outputs/v0.2-multidimensional-analysis

[Guida metodologica](docs/v0_2_multidimensional_analysis.md).

## Dashboard offline v0.2

Cruscotto HTML consultabile senza server e senza dati personali,
alimentato dall'analisi multidimensionale verificata:

    uv run --locked epah dashboard v0.2 --analysis-dir outputs/v0.2-multidimensional-analysis --out-dir outputs/v0.2-offline-dashboard

Aprire `outputs/v0.2-offline-dashboard/index.html`.
[Guida dashboard](docs/v0_2_offline_dashboard.md).

## Pacchetto di revisione tecnica v0.2

Dopo aver generato il rapporto v0.2, le 27 schede,
l'analisi e la dashboard offline:

    uv run --locked epah review-pack v0.2

Il programma controlla gli hash e raccoglie gli artefatti
in un dossier **non autorizzato alla pubblicazione**.
Ogni approvazione scientifica, istituzionale ed editoriale
resta esplicitamente in attesa.
[Guida alla review v0.2](docs/v0_2_review_package.md).

## Audit integrità pacchetto v0.2

Dopo `epah review-pack v0.2`, verificare il pacchetto e il suo ZIP:

    uv run --locked epah audit v0.2 --dir outputs/v0.2-review-candidate

Il comando non modifica alcun file e non sostituisce la revisione
scientifica, visiva e istituzionale.
[Protocollo di QA v0.2](docs/v0_2_review_package.md).

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
