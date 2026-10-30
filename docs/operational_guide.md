# Guida operativa — EPAH Diagnosis

I comandi vanno eseguiti dalla root della repository. Gli output e gli originali locali non devono essere cancellati o committati per errore.

## Pilota tecnico v0.1.0 (procedura corrente)

Preparazione ambiente con Python 3.11+:

    py -3.11 -m venv .venv
    .venv\Scripts\Activate.ps1
    python -m pip install -e .
    python -m pip install pytest

Un unico comando genera 27 profili, 9 mappe, CSV, GeoJSON, Excel, PDF e manifest:

    python scripts/build_v0_1_owner_accepted.py

Usa 162 osservazioni della matrice e 81 delle bozze QA in una **copia temporanea**, con il risultato 9/9 del campionamento ISTAT. Non altera i file canonici.

Originali e bozze richiesti:
- outputs/quality/dea_accessibility_2025_v03/
- outputs/quality/rail_accessibility_v01/
- outputs/quality/upper_secondary_accessibility_v01/
- outputs/quality/v0_1_pilot_route_samples_v01/samples.json
- data/downloads/Limiti01012026_g.zip

Output: outputs/v0.1.0-pilot/ e outputs/epah_diagnosis_v0.1.0_pilot.zip. Se esistono, scegliere nuovi --output-dir e --archive. Approvazione tecnica dell'esperto già registrata; valutazione istituzionale dell'Unione Montana successiva. [Dettagli](v0_1_owner_accepted_release.md) e [limiti](release_v0_1_scope_27.md).

## Controlli ordinari non distruttivi

    python -m pytest -q
    python scripts/check_documentation.py
    python scripts/check_framework.py
    python scripts/check_municipality_registry.py
    python scripts/report_completeness.py
    python scripts/export_completeness.py
    python scripts/check_v0_1_readiness.py --phase inputs --report-only

Report-only mostra i blocchi del percorso **canonico**; non ne implica l'approvazione.

## Percorso canonico (per futuri aggiornamenti)

Nuova fonte → originale → prepare → QA → decisione documentata → finalize → PR protetta. Il builder build_v0_1_bundle.py richiede la promozione della matrice 243/243 e nove review metodologiche, non per il pacchetto pilota.

- [Script](script_reference.md)
- [Protezione dei dati](data_change_protection.md)
- [Approvazioni canoniche](human_approval_workflow_v0_1.md)
- [Release canonica](release_v0_1.md)

Gli audit nazionali DEA e gli aggiornamenti esaustivi di treni e scuole restano in **v0.2**.

## Sicurezza e cartografia

GeoJSON CRS84/WGS84 e PNG EPSG:32632. [Documentazione mappe](diagnostic_maps.md).

Non usare git clean -fd, git reset --hard, git add . o cancellazioni massive dei file originali. I rapporti datati sono nell'[archivio](archive/README.md).
