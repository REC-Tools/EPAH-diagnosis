# Guida operativa: cosa eseguire e in quale ordine

Questa è la guida di esecuzione per **EPAH Diagnosis — Sinergie in Canavese**. Eseguire i comandi dalla **radice della repository**. La pipeline lavora su 27 Comuni e 9 dimensioni del core v0.1; non produce una misura individuale di povertà energetica. Per trovare tutti gli script, consultare il [catalogo dei comandi](script_reference.md).

## 1. Installazione e ambiente

Requisiti: Python >= 3.11, Git, accesso alle fonti solo per gli script che scaricano dati. Per i pacchetti Python, il riferimento è `pyproject.toml`. Esempio PowerShell:

```powershell
git clone https://github.com/REC-Tools/EPAH-diagnosis.git
cd EPAH-diagnosis
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e .
python -m pip install pytest
```

Su Linux/macOS, creare l'ambiente con `python3 -m venv .venv`, attivarlo con `source .venv/bin/activate` e usare `python` nei comandi seguenti. Per un repository privato occorre accesso GitHub autorizzato. Non committare token, `.cdsapirc`, download riservati o dati personali.

## 2. Routine consigliata (offline, non modifica la matrice)

```bash
python -m pytest -q
python scripts/check_documentation.py
python scripts/check_framework.py
python scripts/check_municipality_registry.py
python -m epah_diagnosis.cli validate-matrix data/verification_matrix.csv --catalog config/indicators.json
python scripts/report_completeness.py
python scripts/export_completeness.py
python scripts/check_v0_1_readiness.py --phase inputs --report-only --json-out outputs/quality/readiness_inputs.json
```

Output: riepiloghi sotto `outputs/quality/` (non pubblicati né committati). `pytest` verifica codice e fixture, **non** effettua una verifica scientifica delle fonti originali. `check_framework.py` verifica coerenza del registro, non dati sul campo. `validate-matrix` è strutturale; non sostituisce il controllo contro l'elenco canonico dei 27 Comuni né il release gate. `--report-only` conserva i blocker nel JSON ma termina con exit code 0: leggere sempre `inputs_ready`, `blockers` e `review_blockers`.

**Non** inserire `check_integrated_profile_readiness.py` in una routine che richiede exit code 0 finché la matrice è incompleta: questo comando deve fallire se mancano osservazioni validate. Non usare `build_v0_1_bundle.py` come semplice smoke test.

## 3. Acquisire e verificare le tre fonti prioritarie

Con originali istituzionali locali già scaricati (consigliato quando i siti limitano gli accessi automatici):

```bash
python scripts/audit_priority_sources.py --annex-file "PATH/Allegato_A_2016.pdf" --altitude-xlsx "PATH/altimetria_2021.xlsx" --snai-xlsx "PATH/snai_2020.xlsx" --out-dir outputs/quality/priority_source_audit_manual --strict
```

In alternativa `python scripts/audit_priority_sources.py --download --out-dir outputs/quality/priority_source_audit_online` tenta l'acquisizione istituzionale. I nomi in `PATH/` sono segnaposto: usare file ufficiali reali. `audit.json` espone `technical_pass` o il blocco effettivo; **non** approva né modifica `data/verification_matrix.csv`. Vedere [audit ufficiale](priority_source_audit.md) e [archivio tecnico recuperato dalla PR #79](priority_81_evidence_recovery.md); non utilizzare le copie archiviate come dati approvati.

## 4. Preparare un nuovo indicatore: bozza → QA umana → promozione

**Patrimonio edilizio ISTAT CPA 2011**

La pipeline più recente permette anche un audit indipendente, senza scrivere dati canonici: `python scripts/audit_building_stock_source.py --download` oppure `--source-zip PATH`. Vedere [audit edilizio](building_stock_source_audit.md).

```bash
python scripts/prepare_building_stock.py --source-zip "PATH/dati-cpa_2011.zip" --out-dir outputs/quality/building_stock_2011
```

Esaminare CSV e `building_stock_qa.json`, origine, licenza, crosswalk ISTAT e comparabilità. **Solo dopo** una revisione persistente con approvazione verificabile:

```bash
python scripts/finalize_building_stock_single_source.py --source-zip "PATH/dati-cpa_2011.zip" --draft-dir outputs/quality/building_stock_2011 --approval "PATH/approval.json"
```

**Altimetria o SNAI** (sostituire `mean_altitude` con `snai_classification` quando appropriato):

```bash
python scripts/prepare_territorial_context.py --indicator mean_altitude --source-xlsx "PATH/altimetria_2021.xlsx" --out-dir outputs/quality/altitude_draft
python scripts/finalize_mean_altitude.py --source-xlsx "PATH/altimetria_2021.xlsx" --draft-dir outputs/quality/altitude_draft --approval "PATH/approval.json"
```

**Accessibilità DEA**:

```bash
python scripts/prepare_dea_accessibility.py --road-zip "PATH/Piemonte.zip" --boundaries-zip "PATH/Limiti01012026_g.zip" --out-dir outputs/quality/dea_draft
```

Per scuola/ferrovia usare `prepare_education_rail_access.py --help`: servono `--indicator`, gli ZIP stradali e dei confini e, per le scuole, i due CSV MIM. Consultare le schede [DEA](dea_accessibility_qa.md), [scuole](indicator_08_upper_secondary_accessibility.md), [ferrovia](indicator_09_rail_accessibility.md). I finalizzatori `finalize_dea_accessibility.py`, `finalize_upper_secondary_accessibility.py` e `finalize_rail_accessibility.py` richiedono `--approval` effettivo. La presenza del parametro non costituisce approvazione.

I finalizzatori possono aggiornare `data/verification_matrix.csv` e `data/indicators/`: operare su un **branch Git**, controllare il diff e preservare tutte le altre righe. Le pipeline già finalizzate non devono essere rilanciate solo per produrre un report.

### Revisione incrociata delle tre bozze di accessibilita

Una volta preparate le tre bozze (DEA, ferrovia, scuole) e acquisiti entrambi i CSV MIM, confrontare SHA-256, copertura dei 27 Comuni e possibili coincidenze delle destinazioni con il controllo **non distruttivo**:

```bash
python scripts/audit_accessibility_candidates.py --quality-dir outputs/quality --strict
```

Genera `outputs/quality/accessibility_candidate_review/review_packet.json` e `review_packet.md`. **Non approva i servizi e non modifica la matrice**; gli output possono rivelare una coincidenza tra i minimi scuola-ferrovia senza attribuirle automaticamente una causa. Procedura ed esiti storici in [QA accessibilita ottobre 2026](accessibility_candidate_review_20261030.md).

### Preparazione delle approvazioni umane (non firmate)

Con le tre bozze tecniche e gli originali locali disponibili,
generare tre JSON di approvazione PENDING, le checklist di
accessibilita e nove schede metodologiche, senza promuovere valori:

```powershell
python scripts/prepare_v0_1_review_packets.py --out-dir outputs/quality/human_review_packets_v01
```

Procedura: [approvazioni umane v0.1](human_approval_workflow_v0_1.md).

## 5. Geografia, mappe e pacchetto v0.1

```bash
python scripts/acquire_municipality_boundaries.py
python scripts/check_v0_1_readiness.py --phase inputs
python scripts/build_v0_1_bundle.py --boundaries data/geography/municipalities_2026.geojson
python scripts/check_v0_1_readiness.py --phase release
```

Questa sequenza è **condizionale**: la build finale si esegue solo con **243/243 osservazioni validate**, nove revisioni metodologiche effettive, catalogo con maturità adeguata e geometrie ISTAT disponibili. Il comando della build non scarica dataset, non genera valori fittizi e non aggira il gate. La directory `outputs/v0.1/` contiene mappe PNG, GeoJSON, CSV, Excel, PDF, note e manifest se la build riesce. `--replace` sostituisce una release esistente: usare solo dopo verifica del bundle precedente. Vedere [criteri release](release_v0_1.md).

Gli script `build_municipality_profile.py`, `build_municipality_geojson.py`, `generate_diagnostic_maps.py` e `generate_overlap_map.py` sono **percorsi separati/legacy** e non sostituiscono la release a nove mappe. Non lanciarli prima che gli input richiesti siano completi.

**CRS delle mappe:** il GeoJSON istituzionale resta in **CRS84 (lon/lat WGS84)**. La PR #80 ha introdotto la proiezione in memoria **EPSG:32632** per disegnare tutti i PNG in metri, con renderer condiviso e test geometrici. Verificare visivamente gli output prima della pubblicazione. Vedere [geografia](geography.md) e [mappe](diagnostic_maps.md).

## 6. Esiti, problemi comuni e regole

| Esito | Interpretazione | Azione |
| --- | --- | --- |
| `pytest` fallisce | regressione software o fixture | correggere codice/test, non promuovere dati |
| `technical_pass` | verifica automatica del formato/valori | richiede comunque revisione delle fonti e metodo |
| `inputs_ready: false` | dati o review insufficienti | leggere il report JSON, non lanciare la build |
| `NOT READY` | blocco previsto con matrice incompleta | lavorare per indicatore, non alterare i gate |
| Errore download/CDS | rete, schema API, licenza o credenziali | usare originale locale o riesaminare provider; mai simulare output |
| Mappa apparentemente deformata | controllare quale versione del renderer è in uso e il CRS | aggiornare a `main`, verificare con QGIS e aprire issue con il PNG e lo SHA del commit |

I comandi si dividono in **lettura/QA**, **produzione di bozze**, **promozione con modifica di dati canonici**, **build finale**. Eseguire sempre `git status` e `git diff` prima di committare. Non pubblicare automaticamente risultati tecnicamente coerenti ma scientificamente non autorizzati.
