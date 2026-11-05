# Comandi principali — EPAH Diagnosis

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

## Legacy ed estensioni

Gli script migrate_* servono per migrazioni storiche, non per la matrice attuale. finalize_building_stock.py è disabilitato: il percorso canonico è finalize_building_stock_single_source.py. generate_diagnostic_maps.py è separato/legacy: il builder genera le nove mappe. L'audit nazionale audit_v0_1_dea_national_coverage.py rimane disponibile per **v0.2**, non blocca v0.1.

I moduli opzionali ERA5, SIPEE/APE, impianti e affordability restano per riproducibilità e sviluppo successivo. [Protezione dati](data_change_protection.md).
