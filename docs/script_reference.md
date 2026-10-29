# Inventario degli script e scelta del comando

Riferimento: i **43 script Python** presenti in `scripts/` al 29 ottobre 2026. Tutti i comandi sotto sono da eseguire dalla radice del repository. `python scripts/NOME.py --help` funziona per gli script che dichiarano un parser `argparse`; gli script senza parser spesso avviano subito acquisizioni o scritture: **non** provarli con `--help` alla cieca.

Legenda: **QA** = lettura o report fuori dai dati canonici; **PREP** = genera una bozza da controllare; **PROMO** = può modificare matrice o dati versionati; **BUILD** = crea deliverable; **LEGACY** = non usare nel flusso canonico. Un report QA non certifica automaticamente una fonte.

## Controlli e inventari (10)

| Script | Uso | Comando/condizioni |
| --- | --- | --- |
| `check_framework.py` | QA del catalogo/metodologia, offline | `python scripts/check_framework.py` |
| `check_municipality_registry.py` | QA dei 27 codici ISTAT canonici | `python scripts/check_municipality_registry.py` |
| `check_v0_1_readiness.py` | QA gate input/release, report JSON | `--phase inputs --report-only --json-out outputs/quality/readiness.json` |
| `check_integrated_profile_readiness.py` | QA severa per profili 27×9 | fallisce intenzionalmente finché non completo |
| `verify_heating_degree_days.py` | QA confronto normativo storico; produce report | `python scripts/verify_heating_degree_days.py` |
| `audit_priority_sources.py` | QA originali GG/altitudine/SNAI senza promozione | `--download` oppure `--annex-file`, `--altitude-xlsx`, `--snai-xlsx`; supporta `--strict` |
| `check_sources.py` | QA monitor online delle fonti, report Markdown/JSON | `--json-output`, `--markdown-output`; richiede rete |
| `report_completeness.py` | QA inventario 243 righe JSON | output predefinito `outputs/quality/completeness.json` |
| `export_completeness.py` | QA inventario CSV + XLSX | output predefinito `outputs/quality/` |
| `write_provenance.py` | QA manifest di provenienza di un artefatto | richiede `--artifact`, `--indicator-id`, `--reference-year`, `--output`; **non** approva la fonte |

Per controllare la struttura della matrice esiste anche il comando del modulo (non un file in `scripts/`):
`python -m epah_diagnosis.cli validate-matrix data/verification_matrix.csv --catalog config/indicators.json`.
Per creare **una nuova** matrice, `init-matrix` accetta `--municipalities`, `--output` e il catalogo canonico; non rigenerare la matrice ufficiale esistente.

## Acquisizione e download (4)

| Script | Fonte/dipendenza | Rischio |
| --- | --- | --- |
| `acquire_istat_65plus.py` | ISTAT POSAS, rete | acquisizione; verificare vintage/output |
| `acquire_municipality_boundaries.py` | ZIP geometrie ISTAT 2026, rete | scrive `data/geography/municipalities_2026.geojson` |
| `download_era5_land_daily_temperature.py` | Copernicus CDS, `~/.cdsapirc` e termini accettati | download NetCDF; estensione CDD |
| `download_era5_heat_utci.py` | Copernicus CDS, `~/.cdsapirc` e termini accettati | download NetCDF; estensione UTCI |

Le API CDS possono modificare parametri e rifiutare richieste non autorizzate. I downloader **non** fanno parte della CI offline.

## Preparazione di bozze, senza promozione (4)

| Script | Input principali | Output / procedura |
| --- | --- | --- |
| `prepare_building_stock.py` | `--source-zip` CPA 2011 | CSV + QA sotto `outputs/quality/building_stock_2011/` |
| `prepare_territorial_context.py` | `--indicator mean_altitude` o `snai_classification`, `--source-xlsx` | report e bozza in `--out-dir` |
| `prepare_dea_accessibility.py` | `--road-zip`, `--boundaries-zip` | tabella DEA e QA non validate |
| `prepare_education_rail_access.py` | `--indicator upper_secondary_accessibility` o `rail_accessibility`, ZIP; CSV MIM per scuola | bozza e QA in `--out-dir` |

## Promozione con revisione esplicita (7)

Questi comandi sono **PROMO**: non eseguire su `main` per esplorare l'interfaccia. Preparare una bozza, documentare la fonte, raccogliere evidenza di revisione, usare un branch e ispezionare `git diff`.

| Script | Input essenziali |
| --- | --- |
| `finalize_building_stock_single_source.py` | `--source-zip`, `--draft-dir`, `--approval` |
| `finalize_heating_degree_days.py` | `--official-file` (alias `--official-html`), `--approved-evidence` |
| `finalize_mean_altitude.py` | `--source-xlsx`, `--draft-dir`, `--approval` |
| `finalize_snai_classification.py` | `--source-xlsx`, `--draft-dir`, `--approval` |
| `finalize_dea_accessibility.py` | `--road-zip`, `--boundaries-zip`, `--draft-dir`, `--approval` |
| `finalize_upper_secondary_accessibility.py` | `--road-zip`, `--boundaries-zip`, `--draft-dir`, `--approval`, CSV scuola |
| `finalize_rail_accessibility.py` | `--road-zip`, `--boundaries-zip`, `--draft-dir`, `--approval` |

Le opzioni complete sono riportate da `--help` per questi sette script. La revisione metodologica della release è **aggiuntiva**, registrata in `config/release_reviews_v0_1.json` con evidenza autentica.

## Finalizzatori con dati esterni o estensioni (8)

| Script | Scopo | Cautele |
| --- | --- | --- |
| `finalize_population_65_plus.py` | aggiorna ISTAT POSAS | acquisizione remota e possibili scritture canoniche |
| `finalize_mef_income.py` | aggiorna dati MEF IRPEF | fonte remota, nuovo anno richiede nuovo QA |
| `finalize_heating_facilities_gap.py` | lacuna impianti riscaldamento | estensione non bloccante; input CPA |
| `finalize_sipee_ape_performance.py` | quota APE con classi scarse | estensione; estrazione SIPEE ufficiale necessaria |
| `finalize_cooling_degree_days.py` | CDD da ERA5-Land | richiede NetCDF reale e geometrie |
| `finalize_heat_stress_days.py` | giornate UTCI calde da ERA5-HEAT | richiede NetCDF reale e geometrie |
| `finalize_heating_fuel_mix.py` | combustibili di riscaldamento | richiede CSV ISTAT comunale ufficiale |
| `finalize_local_energy_affordability.py` | affordability e comfort locali | richiede dati aggregati validati, mai personali |

Questi otto script **non** costituiscono una sequenza standard di avvio. Verificarne input, output, schema e impatto prima di eseguirli; non confonderli con il core review-gated.

## Elaborazioni, mappe e deliverable (7)

| Script | Quando usare |
| --- | --- |
| `build_v0_1_bundle.py` | **BUILD canonica** solo dopo il gate `--phase inputs`; 17 artefatti e controlli sul bundle |
| `build_municipality_profile.py` | BUILD separata su 9 dimensioni, richiede matrice completa |
| `build_municipality_comparison.py` | BUILD tabella comparativa, richiede profili pronti |
| `build_municipality_geojson.py` | BUILD join geografico, richiede profili e confini |
| `build_multidimensional_overlap.py` | BUILD sovrapposizioni descrittive; non è un indice EPAH |
| `generate_diagnostic_maps.py` | BUILD **legacy** tre mappe, non sostituisce le nove della release |
| `generate_overlap_map.py` | BUILD **legacy/separata** sulla sovrapposizione già pronta |

Per la mappa canonica la scelta è `build_v0_1_bundle.py`, non la catena legacy. CRS84 nei GeoJSON, proiezione metrica da correggere nel disegno PNG prima di uso pubblico: [guida](operational_guide.md).

## Migrazioni e comando disabilitato (3)

| Script | Stato |
| --- | --- |
| `migrate_matrix_preview.py` | anteprima non distruttiva della migrazione; scegliere `--output` dedicato |
| `migrate_legacy_indicator_ids.py` | **MIGRAZIONE**: non eseguire su matrice corrente senza backup, diff e PR |
| `finalize_building_stock.py` | **DISABILITATO**; usare bozza CPA 2011 + finalizzatore single-source |

### Cosa eseguire normalmente?

1. Ogni modifica di codice: `pytest`, `check_documentation.py`, `check_framework.py`, validazione della matrice e `check_municipality_registry.py`.
2. Per capire cosa manca: `report_completeness.py`, `export_completeness.py`, `check_v0_1_readiness.py --phase inputs --report-only`.
3. Per ogni nuova fonte: acquisizione originale → `prepare_*` → QA indipendente → `finalize_*` protetto → PR.
4. Per la release: `check_v0_1_readiness.py --phase inputs` → `build_v0_1_bundle.py` → `--phase release`; solo con tutti i prerequisiti verificati.
