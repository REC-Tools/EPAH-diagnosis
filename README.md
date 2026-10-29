# EPAH Diagnosis — Sinergie in Canavese

Strumento open-data per supportare la diagnosi territoriale della povertà energetica nei **27 Comuni** della Green Community. Usa dati aggregati e proxy: **non identifica famiglie in povertà energetica** e non produce un indice EPAH certificato.

## Iniziare
Installazione in un ambiente Python 3.11+:
```bash
python -m pip install -e .
python -m pip install pytest
pytest -q
python scripts/check_framework.py
python -m epah_diagnosis.cli validate-matrix data/verification_matrix.csv --catalog config/indicators.json
```

## Stato e limiti
- Il **core v0.1** prevede **9** dimensioni integrate, non tutte validate: vulnerabilità, contesto e accessibilità. Le pipeline #10–#15 sono estensioni non bloccanti e sono tracciate in `config/release_v0_1.json`.
- `data/verification_matrix.csv` include **243 combinazioni** (27 × 9); la presenza di una riga non implica la disponibilità del valore. Per ogni indicatore va controllato il campo `status`.
- Le 81 osservazioni storiche sono conservate in `data/reference/verification_matrix_baseline_81.csv`.
- I dati climatici presenti derivano da uno snapshot locale; l'acquisizione non equivale alla validazione indipendente della fonte normativa.
- Le ulteriori schede su impianti di riscaldamento e SIPEE/APE sono **sperimentali** e non sono ancora parte del catalogo a nove indicatori.
- Alcuni script dipendono da download di fonte ufficiale, non esercitati nella CI offline.
- `model.py` e l'inizializzazione CLI senza catalogo supportano soltanto il vecchio schema a tre indicatori: **non usare `init-matrix` per sovrascrivere la matrice corrente**.

## Controlli e profili
```bash
python scripts/check_framework.py
python -m epah_diagnosis.cli validate-matrix data/verification_matrix.csv --catalog config/indicators.json
python scripts/check_integrated_profile_readiness.py
```
Il controllo di readiness termina con errore finché non risultano disponibili e validati i nove indicatori per tutti i 27 Comuni. Non è un errore della CI: è un'indicazione di incompletezza della diagnosi. I profili completi si generano con `scripts/build_municipality_profile.py` **solo dopo** tale verifica.

## Documentazione
- [Framework metodologico](docs/framework.md), [catalogo](docs/indicator_catalog.md), [criteri di completamento](docs/indicator_completion_criteria.md).
- [Flusso dati](docs/pipeline.md), [contratto degli artefatti](docs/data_contract.md), [provenienza](docs/provenance.md).
- [Governance](docs/governance.md) e [audit generale](docs/repository_quality_audit.md).
- [Acquisizione edilizia](docs/building_stock_finalization.md), [stato clima](docs/indicator_04_completion_status.md).
- [Schema accessibilità](docs/indicator_07_dea_accessibility.md), [scuole](docs/indicator_08_upper_secondary_accessibility.md), [ferrovia](docs/indicator_09_rail_accessibility.md).

## Principio operativo
Ogni pubblicazione deve separare indicatore, fonte, anno, stato di verifica e limitazioni. Le mappe e il report rappresentano dimensioni distinte; nessun punteggio composito automatico.
\n\n## Release v0.1\nLa definizione operativa della prima release è in [docs/release_v0_1.md](docs/release_v0_1.md). Il core resta separato dalle estensioni che dipendono da SIPEE, Copernicus o raccolta locale.\n

## PR-02 - Canonical municipality registry and provenance

- `data/municipalities.csv` contains 27 unique six-digit `istat_code`
  identifiers alongside legacy municipality names (the existing matrix remains
  unchanged). Codes sourced from an ISTAT-derived 2026 CC BY 4.0 dataset;
  independent comparison with official ISTAT SITUAS is still pending.
- `python scripts/check_municipality_registry.py` validates code format,
  uniqueness and coverage.
- `python -m epah_diagnosis.cli init-matrix --municipalities data/municipalities.csv --output /tmp/new_epah_matrix.csv`
  initializes a **new** nine-indicator matrix, refuses to overwrite existing
  files, and never rewrites `data/verification_matrix.csv`.
- `python scripts/write_provenance.py --artifact data/indicators/income_vulnerability_2024.csv --indicator-id income_vulnerability --reference-year 2024 --output outputs/quality/income_provenance.json`
  creates an offline, QA-unassessed manifest with real file SHA-256 hashes.

## PR-03: verifica gradi-giorno

`python scripts/verify_heating_degree_days.py` confronta i 27 valori con una trascrizione della tabella normativa storica ufficiale e produce un report QA senza modificare la matrice. Tutti i GG e le zone coincidono, ma la quota accessoria di Pratiglione differisce (711 m tabella storica, 611 m snapshot). Il finalizzatore ora richiede `--approved-evidence` per un'effettiva revisione della versione normativa vigente; le 27 osservazioni restano `Dato acquisito`.

## PR-04: ISTAT 2011 building-stock acquisition

The old building-stock finalizer that could directly mark rows validated is
disabled. To prepare *unvalidated*, auditable 27-municipality outputs, run
`python scripts/prepare_building_stock.py --source-zip /local/dati-cpa_2011.zip`.
The ZIP is a real download from ISTAT, not generated by this repository.
It produces CSV tables, building-count-weighted benchmarks and SHA-256 QA
metadata under `outputs/quality/building_stock_2011/`, without changing the
verification matrix. Promotion requires genuine independent review evidence
and `scripts/finalize_building_stock_single_source.py --approval FILE ...`.
See `docs/building_stock_finalization.md`.

## PR-05: altitudine media ISTAT 2021 e classificazione SNAI 2020

Le due vecchie pipeline che promuovevano automaticamente dati scaricati
ora richiedono una preparazione offline e revisione documentata.
Per generare bozze da **XLSX ufficiali locali** senza sovrascrivere dati:

```bash
python scripts/prepare_territorial_context.py --indicator mean_altitude --source-xlsx /local/altimetria.xlsx
python scripts/prepare_territorial_context.py --indicator snai_classification --source-xlsx /local/snai.xlsx
```

I dati vengono collegati sui codici ISTAT a sei cifre, includendo controlli
di range altimetrico, classe SNAI A-F, 27/27 Comuni, copertura nazionale
e checksum. La promozione in matrice richiede `--approval` con evidenze
di verifica umana reale. Nessun valore sintetico e stato inserito
nella matrice, che resta incompleta fino alla revisione.

## PR-06: accessibilità sanitaria DEA I/II

Calcolo offline del minimo tempo ISTAT **TEP_TOT** (geografia 2021, grafo
stradale 2020) verso un Comune con DEA I/II nello **snapshot piemontese**
da verificare (fonti miste 2023/2025). Non equivale necessariamente al
DEA nazionale più vicino, né a tempi casa–ospedale.

```bash
python scripts/prepare_dea_accessibility.py \
  --road-zip /local/Piemonte.zip \
  --boundaries-zip /local/Limiti01012026_g.zip
```

Il generatore controlla 27 origini, la completezza 27×N dei tempi verso
tutte le destinazioni ammissibili, i codici ISTAT e gli hash. Non modifica
la matrice. [Procedura QA e approvazione](docs/dea_accessibility_qa.md).

## PR-07: accessibilità alle scuole superiori e alla ferrovia

Ultime due pipeline del core territoriale v0.1:
\`upper_secondary_accessibility\` (MIM 2024/25) e
\`rail_accessibility\` (snapshot SFM/RFI, operatività da ricontrollare).
La scelta della destinazione si basa su requisiti di servizio distinti,
e sul minimo tempo \`TEP_TOT\` ISTAT 2021 entro il catalogo regionale.
Non è la misura porta a porta, e non è garantito che l'insieme delle
destinazioni sia esaustivo sul territorio nazionale.

Per preparare i dati senza toccare la matrice:
\`python scripts/prepare_education_rail_access.py --help\`.
I nuovi finalizzatori
\`scripts/finalize_upper_secondary_accessibility.py\` e
\`scripts/finalize_rail_accessibility.py\`
richiedono \`--approval\` con verifiche indipendenti reali.
Nessuna osservazione è promossa automaticamente.
Dettagli nelle schede 08 e 09 di \`docs/\`.

## PR-08 — pacchetto diagnostico v0.1 (17 file)

Quando tutte le nove dimensioni sono realmente validate (243/243),
il catalogo e approvato da un revisore e i confini ISTAT sono disponibili:

```bash
python scripts/build_v0_1_bundle.py
```

La build genera **9 mappe PNG**, tabella comparativa, profili per
27 Comuni, GeoJSON, `completeness.xlsx` (5 fogli con provenance)
e `diagnostic_report.pdf`, oltre a `readiness.json`, note e manifest
con SHA-256. Tutti i risultati sono valutati in una cartella
temporanea e pubblicati soltanto al superamento dei test di struttura,
geometria, file e checksum. SNAI resta una classificazione A–F, non
uno score. **Con la matrice attuale il comando fallisce correttamente**:
non aggira il blocco di dati non validati. Dettagli:
[criteri release v0.1](docs/release_v0_1.md).

## Audit fonti ufficiali prioritarie — gradi-giorno, altitudine, SNAI

Per acquisire/controllare i file originali istituzionali e generare
un report tecnico per 81 osservazioni, senza alterare la matrice:

```bat
python scripts/audit_priority_sources.py --download
```

Se uno dei portali blocca il download automatizzato, scaricare manualmente
i due XLSX e salvare la pagina completa HTML dell'Allegato A **2016**.
Il comando supporta `--altitude-xlsx`, `--snai-xlsx`
e `--annex-html`. Conserva gli hash e indica i 27 Comuni
trovati o le anomalie. **Non promuove automaticamente osservazioni**.
Consultare [la procedura completa](docs/priority_source_audit.md).

### PR-08b: diagnosi del blocco HTML gradi-giorno

Il confronto dei 27 Comuni viene ora eseguito anche se il download
dell'Allegato A non include il marcatore di versione. In tal caso la
verifica resta \`blocked\`, ma registra righe lette, differenze e causa
esatta; non vengono applicati override di validazione. Si possono
riutilizzare gli originali presenti in
\`outputs/quality/priority_source_audit/raw/\` con \`--annex-html\`,
\`--altitude-xlsx\`, \`--snai-xlsx\` e una nuova \`--out-dir\`.
Vedere [docs/priority_source_audit.md](docs/priority_source_audit.md).


### Audit gradi-giorno: sorgente ufficiale stampabile

Una risposta HTML senza titolo e senza righe (\`rows 0/27\`) non indica
un errore nei GG ma un'acquisizione della pagina sbagliata. Il comando
\`audit_priority_sources.py --download\` usa ora l'endpoint
\`executePrintArticolo.do\` del Dipartimento delle Finanze e rifiuta
i documenti senza tabella. Riutilizzare gli XLSX gia scaricati con
\`--altitude-xlsx\` e \`--snai-xlsx\` e scegliere un nuovo \`--out-dir\`
per un audit HDD isolato. I dettagli sono in
[docs/priority_source_audit.md](docs/priority_source_audit.md).



### Diagnostica sorgente normativa (PR-08d)

L'endpoint di stampa ufficiale puo distribuire PDF, HTML o testo.
L'audit legge tutti e tre, rifiuta pagine di blocco e registra formato,
HTTP, MIME e hash, senza alcuna promozione automatica. Per file
scaricati tramite browser, usare
\`python scripts/audit_priority_sources.py --annex-file PATH\`;
per l'acquisizione online, mantenere \`--download\` e una directory nuova.
Dopo il merge aggiornare le dipendenze con \`python -m pip install -e .\`.
