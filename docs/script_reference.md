# Comandi principali — EPAH Diagnosis

La cartella [scripts](../scripts/) conserva i comandi: questo indice presenta i **flussi attuali**, senza il vecchio elenco numerico di script che cambiava a ogni PR.

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

## Legacy ed estensioni

Gli script migrate_* servono per migrazioni storiche, non per la matrice attuale. finalize_building_stock.py è disabilitato: il percorso canonico è finalize_building_stock_single_source.py. generate_diagnostic_maps.py è separato/legacy: il builder genera le nove mappe. L'audit nazionale audit_v0_1_dea_national_coverage.py rimane disponibile per **v0.2**, non blocca v0.1.

I moduli opzionali ERA5, SIPEE/APE, impianti e affordability restano per riproducibilità e sviluppo successivo. [Protezione dati](data_change_protection.md).
