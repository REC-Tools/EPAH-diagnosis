# Comandi principali — EPAH Diagnosis

**Percorso corrente: software v0.2.0.** Per una sequenza completa e il significato dei risultati iniziare dalla [guida operativa v0.2](operational_guide.md). I percorsi v0.1 e i finalizzatori rimangono come prerequisiti, strumenti legacy o pipeline canoniche separate; i dati v0.3 non sono ancora parte del bundle v0.2.

La cartella [scripts](../scripts/) conserva i comandi: questo indice presenta i **flussi attuali**, senza il vecchio elenco numerico di script che cambiava a ogni PR.

## CLI unificata (fase 1)

Usare `epah status`, `epah sources check`, `epah data validate` e
`epah build --profile pilot` oppure `--profile canonical`.
La CLI richiama gli script esistenti senza modificare i gate.
[Comandi, installazione e limitazioni](unified_cli.md).

## V0.1.0 pilota

| Script | Ruolo |
| --- | --- |
| **build_v0_1_owner_accepted.py** | **BUILD** pilota 27×9, ZIP, mappe, CSV, Excel, PDF; non modifica i file versionati. |
| **audit_v0_1_pilot_route_samples.py** | **QA** campioni originali ISTAT, 9/9 già passati. |
| **check_documentation.py** | **QA** link delle guide attive. |
| **check_framework.py**, **check_municipality_registry.py** | **QA** catalogo e 27 Comuni. |
| **report_completeness.py**, **export_completeness.py** | **QA** inventario di completezza. |

Avvio: python scripts/build_v0_1_owner_accepted.py. [Guida](v0_1_owner_accepted_release.md).

## Pipeline canonica avanzata

- **Acquisizione:** acquire_accessibility_inputs.py, acquire_municipality_boundaries.py.
- **Bozze:** prepare_dea_accessibility.py, prepare_education_rail_access.py, prepare_building_stock.py, prepare_territorial_context.py.
- **QA fonti:** audit_priority_sources.py, audit_dea_2025_source.py, audit_building_stock_source.py.
- **Promozione protetta:** finalize_dea_accessibility.py, finalize_rail_accessibility.py, finalize_upper_secondary_accessibility.py (richiedono evidenza di approvazione, possono modificare matrice e CSV).
- **Build canonica:** check_v0_1_readiness.py e build_v0_1_bundle.py (243/243 e nove review).

prepare_v0_1_review_packets.py genera bozze di approvazione, **non firme**: non serve al pilota tecnico già approvato.

## Pipeline di intake e QA (PR #120)

`epah pipeline plan` e `epah pipeline run` supportano
`--profile cit-quarantine` (parsing e confronto tecnico 26/27)
oppure `--profile accessibility-intake` (sola acquisizione/preflight).
Output nuovi in `outputs/quality/`; nessuna promozione.
[Guida e comandi](automated_technical_pipeline.md).

## Dossier umano di chiarimento CIT

`epah cit review-packet --run-dir ... --out-dir ...` prepara il
dossier su Pont Canavese a partire da una run CIT QA già verificata.
[Guida al dossier](cit_source_review_packet.md).
Non modifica la matrice, non scioglie i duplicati e non approva il rilascio.

## Rapporto territoriale v0.2 (indipendente dal CIT)

`epah report v0.2` usa solo un bundle v0.1 con
hash verificati, senza correggere o promuovere osservazioni.
Genera PDF v0.2, fatti e manifest JSON in una cartella
nuova. [Uso, limiti e QA](v0_2_territorial_report.md).

## Schede comunali v0.2

`epah sheets v0.2` produce 27 PDF A4 e un indice SHA-256,
senza nuovi dati o approvazioni. [Guida](v0_2_municipal_sheets.md).

## Analisi multidimensionale v0.2

`epah analysis v0.2` crea i confronti degli otto indicatori,
28 co-occorrenze e un manifest. [Metodologia](v0_2_multidimensional_analysis.md).

## Dashboard offline v0.2

`epah dashboard v0.2` costruisce HTML e dati locali
dall'analisi verificata, senza rete. [Guida](v0_2_offline_dashboard.md).

## Pacchetto interno di revisione v0.2

`epah review-pack v0.2` produce un ZIP tecnico
con 27 schede, rapporto, analisi, dashboard e
checklist non approvata.
[Guida](v0_2_review_package.md).

## Audit e manutenzione delle dipendenze

L'inventario non distruttivo degli script, dei riferimenti testuali e dei derivati
versionati si esegue con `python scripts/audit_repository_hygiene.py --check`.
Il report JSON serve **solo per il triage**, non autorizza cancellazioni.
[Metodologia e risultati della ricognizione](repository_hygiene.md).

## Legacy ed estensioni

I tre entrypoint storici di confronto e overlap sono ora in
[`scripts/legacy/`](../scripts/legacy/README.md):
`build_municipality_comparison.py`, `build_multidimensional_overlap.py`
e `generate_overlap_map.py`. Sono **anteprime storiche**, non output v0.2;
non hanno alcun ruolo nel percorso di release istituzionale.


Gli script migrate_* servono per migrazioni storiche, non per la matrice attuale. finalize_building_stock.py è disabilitato: il percorso canonico è finalize_building_stock_single_source.py. generate_diagnostic_maps.py è separato/legacy: il builder genera le nove mappe. L'audit nazionale audit_v0_1_dea_national_coverage.py rimane disponibile per **v0.2**, non blocca v0.1.

I moduli opzionali ERA5, SIPEE/APE, impianti e affordability restano per riproducibilità e sviluppo successivo. [Protezione dati](data_change_protection.md).
