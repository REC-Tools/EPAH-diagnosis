# EPAH Diagnosis | Sinergie in Canavese

**Toolkit open-data per la diagnosi territoriale della povertà energetica nei 27 Comuni della Green Community Sinergie in Canavese.**

Combina proxy di vulnerabilità socioeconomica e abitativa, contesto climatico-territoriale e accessibilità ai servizi. Produce inventari di completezza, tabelle, mappe e, **solo a validazione completa**, un pacchetto diagnostico riproducibile. I risultati sono **aggregati comunali**: non identificano famiglie vulnerabili, non certificano un indice EPAH e non attribuiscono automaticamente un punteggio composito.

## Avvio rapido

Requisiti: **Python 3.11+**, Git e accesso alle fonti ufficiali solo per i moduli che richiedono download. Da PowerShell (Windows):

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e .
python -m pip install pytest
```

Da Linux/macOS: `python3 -m venv .venv` e `source .venv/bin/activate` prima di installare i pacchetti.

**Controllo di qualità e inventario: sicuro, offline e senza modifiche alla matrice.**

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

Aprire `outputs/quality/completeness.json`, `outputs/quality/completeness.xlsx` e `outputs/quality/readiness_inputs.json`. La modalità `--report-only` termina senza errore **anche quando la release non è pronta**: leggere i blocker nel JSON.

**Per capire esattamente cosa eseguire:** [guida operativa passo-passo](docs/operational_guide.md) · [inventario completo degli script, con input e rischi](docs/script_reference.md).

## Stato dei dati (snapshot 29 ottobre 2026)

| Voce | Stato |
| --- | --- |
| Comuni | 27, identificati nel registro `data/municipalities.csv` |
| Indicatori core | 9; catalogo in `config/indicators.json` |
| Matrice | 243 combinazioni Comune × indicatore |
| Osservazioni con stato `Dato validato` | **54/243** |
| Osservazioni `Dato acquisito` | **27/243** |
| Osservazioni `Da verificare` | **162/243** |
| Maturità metodologica | le 9 voci sono `EXPERIMENTAL`; review di release ancora necessarie |
| Release v0.1 | **NOT READY**, correttamente bloccata |

I 54 stati `Dato validato` sono metadati della matrice e **non** equivalgono a una revisione metodologica finale. Le 81 righe interessate dal rollback della PR #80 dispongono ora di [un archivio tecnico separato](docs/priority_81_evidence_recovery.md): non sono state ripromosse. Le fonti e i periodi possono differire tra indicatori. Gli esiti sono da ricalcolare a ogni nuovo commit con i comandi di completeness.

## Come funziona

```text
Fonti ufficiali → file originali e checksum → preparazione non validata
  → controllo tecnico → revisione umana con evidenza → finalizzazione
  → matrice canonica (27 × 9) → release gate
  → mappe + GeoJSON + CSV + Excel + rapporto PDF + manifest
```

**Non esiste un orchestratore che scarica e approva tutto automaticamente.** Alcune fonti necessitano file ZIP/XLSX locali, altre accesso di rete e le estensioni Copernicus richiedono account CDS. Le pipeline `prepare_*` generano bozze senza promozione, mentre alcuni `finalize_*` aggiornano dati versionati: usare branch, approvazione reale e controllo del diff. Non eseguire `init-matrix` sulla matrice esistente.

Per le tre fonti prioritarie (DPR 412/1993, altimetria ISTAT, SNAI) iniziare da `python scripts/audit_priority_sources.py --help` e dal [protocollo di audit](docs/priority_source_audit.md). Per le 162 osservazioni da verificare, consultare le sezioni building stock, DEA, scuole e ferrovia della guida operativa.

## Output e criteri di pubblicazione

L'inventario aggiornabile viene scritto in `outputs/quality/`. La **release finale** si genera con `python scripts/build_v0_1_bundle.py` soltanto dopo il superamento di `python scripts/check_v0_1_readiness.py --phase inputs`, che include 243/243 osservazioni valide e revisioni metodologiche documentate.

Il bundle previsto in `outputs/v0.1/` contiene 9 mappe tematiche, profili/comparazioni CSV, GeoJSON, `completeness.xlsx`, `diagnostic_report.pdf`, note, manifest SHA-256 e readiness. Nessun passaggio deve aggirare il gate o creare valori mancanti sintetici. [Criteri completi](docs/release_v0_1.md).

**Cartografia:** il GeoJSON è in CRS84 (longitudine/latitudine WGS84). Dalla [PR #80](https://github.com/REC-Tools/EPAH-diagnosis/pull/80), i PNG sono disegnati in EPSG:32632 (metri) da un renderer condiviso; resta necessaria la QA visiva prima della pubblicazione. Dettagli in [mappe](docs/diagnostic_maps.md).

## Documentazione

- **Per eseguire:** [Guida operativa](docs/operational_guide.md), [catalogo script](docs/script_reference.md), [pipeline e contratti](docs/pipeline.md).
- **Per verificare:** [Quality review](docs/quality_review_20261029.md), [governance](docs/governance.md), [completezza](docs/completeness_report.md), [provenienza](docs/provenance.md).
- **Per interpretare:** [framework](docs/framework.md), [catalogo indicatori](docs/indicator_catalog.md), [criteri di completamento](docs/indicator_completion_criteria.md).
- **Per pubblicare:** [release v0.1](docs/release_v0_1.md), [geografia](docs/geography.md), [mappe](docs/diagnostic_maps.md).
- **Per ricostruire le decisioni:** [audit priorità](docs/priority_source_audit.md), [archivio tecnico delle 81 osservazioni](docs/priority_81_evidence_recovery.md), recuperato dalla [PR #79](https://github.com/REC-Tools/EPAH-diagnosis/pull/79) senza alterare la matrice.

## Acquisizione ufficiale ISTAT CPA 2011

La [PR #81](https://github.com/REC-Tools/EPAH-diagnosis/pull/81) ha introdotto un audit indipendente delle variabili E3, E8–E16 del patrimonio edilizio 2011, senza promuovere automaticamente le osservazioni.

```bash
python scripts/audit_building_stock_source.py --download
```

In caso di blocco del portale, usare `--source-zip` con l'originale scaricato manualmente. Gli output sono in `outputs/quality/` e richiedono una revisione umana documentata prima della finalizzazione. Consultare la [procedura CPA](docs/building_stock_source_audit.md).

## Integrità dei dati e protezione CI

Le PR che modificano matrice, indicatori, fonti ed evidenze sono verificate automaticamente per diff inattesi, rimozioni, regressioni di stato e dichiarazioni obbligatorie. Gli aggiornamenti programmati MEF e ISTAT 65+ propongono **PR draft** anziché scrivere direttamente su `main`. Il blocco effettivo del merge richiede inoltre le impostazioni GitHub di branch protection e required checks (da configurare a parte): [procedura e limiti](docs/data_change_protection.md).

## Contributi e licenza

Ogni PR deve documentare metodo, anno delle fonti, test, impatto sui dati e approvazione quando necessaria. Vedere [governance](docs/governance.md) e `.github/pull_request_template.md`. Non committare credenziali né dati personali. Licenza del codice: [LICENSE](LICENSE).


## Originali ISTAT/MIM per accessibilità DEA, scuola e ferrovia

Acquisizione non distruttiva della matrice stradale ISTAT (2021, grafo 2020)
e dei confini comunali ISTAT 2026:

```bat
python scripts/acquire_accessibility_inputs.py --download --sources road,boundaries --strict
```

Con file già scaricati: `--road-zip` e `--boundaries-zip`.
Per l'offerta MIM 2024/25: `--download --sources school_registry,school_pathways`
in un **nuovo** `--out-dir`. Il comando registra SHA-256, formato e
provenienza, ma **non** genera tempi stradali, non verifica lo stato
corrente dei DEA/scuole/treni e non modifica la matrice.
[Guida completa](docs/accessibility_original_source_intake.md).
