# Guida operativa — EPAH Diagnosis v0.2

**Riferimento corrente: software v0.2.0.** Questa guida descrive la procedura tecnica riproducibile, **non** la pubblicazione istituzionale dei 27 risultati comunali. I file originali e gli output locali non devono essere cancellati o committati accidentalmente.

## 1. Installazione e controlli

Da `main` con Python 3.11+ e `uv` disponibili:

```powershell
uv sync --python 3.11 --locked --group dev
uv run --locked pytest -q
uv run --locked epah status
uv run --locked epah sources check
uv run --locked epah data validate
python scripts/check_documentation.py
```

I test su dati sintetici non convalidano dati reali né le relative licenze. Il catalogo canonico elenca **nove indicatori/descrittori**; l'inventario EPAH v0.3 è separato.

## 2. Prerequisito: bundle pilota v0.1 verificato

La v0.2 **consuma** un bundle pilota locale con manifest e hash coerenti. Se `outputs/v0.1.0-pilot` non esiste, seguire la [procedura del builder pilota](v0_1_owner_accepted_release.md). I prerequisiti originali/QA della build locale includono:

- `outputs/quality/dea_accessibility_2025_v03/`
- `outputs/quality/rail_accessibility_v01/`
- `outputs/quality/upper_secondary_accessibility_v01/`
- `outputs/quality/v0_1_pilot_route_samples_v01/samples.json`
- `data/downloads/Limiti01012026_g.zip`

Il pilota tecnico storico non corrisponde alla promozione canonica di **243/243** valori. I controlli di readiness canonici e le review metodologiche hanno un gate indipendente. Non inventare input mancanti per eseguire il builder.

## 3. Produzione del pacchetto v0.2

Eseguire in **PowerShell**, dalla root, con il bundle già pronto. Usare sempre percorsi nuovi:

```powershell
$bundle = "outputs/v0.1.0-pilot"
$run = "outputs/v0.2-technical-$(Get-Date -Format yyyyMMdd-HHmmss)"
uv run --locked epah report v0.2 --bundle $bundle --out-dir "$run/report"
uv run --locked epah sheets v0.2 --bundle $bundle --out-dir "$run/sheets"
uv run --locked epah analysis v0.2 --bundle $bundle --out-dir "$run/analysis"
uv run --locked epah dashboard v0.2 --bundle $bundle --analysis-dir "$run/analysis" --out-dir "$run/dashboard"
uv run --locked epah review-pack v0.2 --bundle $bundle --report-dir "$run/report" --sheets-dir "$run/sheets" --analysis-dir "$run/analysis" --dashboard-dir "$run/dashboard" --out-dir "$run/review"
uv run --locked epah audit v0.2 --dir "$run/review"
```

Risultati: rapporto PDF con fatti e manifest, **27 PDF comunali**, analisi descrittiva, dashboard HTML e ZIP tecnico di revisione. Aprire `$run/dashboard/index.html` offline. Tutto il pacchetto è `technical_draft_do_not_publish` finché non siano completate le revisioni scientifica, editoriale e istituzionale.

Guide specifiche: [rapporto](v0_2_territorial_report.md), [schede](v0_2_municipal_sheets.md), [analisi](v0_2_multidimensional_analysis.md), [dashboard](v0_2_offline_dashboard.md), [review e audit](v0_2_review_package.md).

## 4. Controlli non distruttivi e aggiornamenti

```powershell
python scripts/check_framework.py
python scripts/check_municipality_registry.py
python scripts/check_v0_1_readiness.py --phase inputs --report-only
uv run --locked epah local audit
```

`report-only` fotografa i blocchi del percorso canonico senza attestare che la release sia pronta. L'inventario locale separa originali, file versionati modificati e output ignorati. Per aggiornare una fonte seguire **originale → prepare → QA → decisione documentata → finalize → PR protetta**; per i dati validati non saltare mai verifiche e provenance. [Protezione PR](data_change_protection.md).

## 5. Ambiti separati

- **CIT/Pont Canavese:** mantiene il percorso di quarantena e dossier di chiarimento, non alimenta rapporto e dashboard v0.2. [Guida](cit_source_review_packet.md).
- **v0.3:** registro di ricerca e candidato demografico sperimentale, non integrati nel bundle canonico. [Scope](v0_3_scientific_scope.md).
- **Documenti storici:** conservati nell'[archivio](archive/README.md), non utilizzarli come istruzioni operative aggiornate.

La pipeline non misura povertà energetica familiare e non autorizza a identificare beneficiari. Per il significato degli indicatori consultare il [catalogo](indicator_catalog.md); per la storia delle release usare [v0.2.0](releases/v0.2.0.md) e [v0.1.0](release_v0_1_scope_27.md).
