# EPAH v0.3 — indicatori candidati e nomenclatura armonizzata

**Ambito:** 27 Comuni di Sinergie in Canavese. **Stato:** `technical_draft_do_not_publish`. Questa fase NON modifica `config/indicators.json`, `data/verification_matrix.csv`, né i prodotti canonici v0.2.

## Convenzione editoriale e scientifica

Seguire le **dimensioni tematiche dell'EPAH Handbook 1**, tabella 5 (pp. 24–28), senza suggerire che una misura comunale candidata sia un indicatore europeo ufficiale. Nel progetto gli identificativi `H01–H56` sono **riferimenti interni alla trascrizione** dell'Handbook, non gli ID del portale EPAH. L'etichetta di ciascun indicatore deve contenere:

1. **Titolo comprensibile e specifico**, indicando popolazione/stock di riferimento (non solo «povertà energetica»).
2. **Dimensione** EPAH: Climate, Facilities/Housing, Socio-economic, Mobility oppure Policies/Participation; per indicatori aggiuntivi esplicitare «descrittore territoriale, non indicatore EPAH equivalente».
3. **Tipologia e significato:** esito diretto osservato, proxy di vulnerabilità, descrittore di contesto, risposta/politica oppure benchmark.
4. **Numeratore, denominatore, unità, periodo, scala geografica, fonte e versione**; citare limitazioni di copertura, classi mancanti e bias.
5. **Stato di evidenza:** `source_identified` → `data_acquired` → `data_qa_passed` → `human_approved`. Il passaggio di stato richiede fascicoli e approvazione separata. `technical_draft_do_not_publish` resta obbligatorio per gli output sperimentali.

Non attribuire ai singoli Comuni misure EU-SILC NUTS 2, né sommare proxy e dati diretti in una graduatoria o indice di povertà energetica. Tutte le quote riportano **il proprio denominatore**. Non modificare la semantica della v0.2 per rendere apparentemente confrontabili serie diverse.

## Tre candidati selezionati

| ID | Etichetta armonizzata | Dimensione EPAH | Tipologia | Fonte originale candidata | Valore |
| --- | --- | --- | --- | --- | --- |
| H05 (interno) | Quota di attestati di prestazione energetica residenziali validi in classe F o G | Facilities/Housing | Proxy prestazionale su campione certificato | Regione Piemonte / SICEE e ENEA SIAPE | 100 × (APE F + APE G) / tutti gli APE residenziali validi |
| ADD-HOUSING-01 | Quota di abitazioni non occupate da persone residenti | Facilities/Housing — descrittore aggiuntivo | Contesto territoriale (non povertà energetica) | ISTAT, dati per sezioni di censimento 2023 | 100 × abitazioni non occupate da residenti / totale abitazioni |
| H04 (interno) | Gradi-giorno annui di raffrescamento stimati da griglia climatica (CDD) | Climate | Esposizione climatica, non comfort interno | ARPA Piemonte NWIOI Tmin/Tmax | Somma giornaliera Eurostat: con Tmean ≥24 °C, CDD=Tmean−21 °C; altrimenti 0 |

**H05:** gli APE di **tutti gli usi** non soddisfano il denominatore residenziale; un report che includa certificati commerciali deve essere denominato diversamente e mantenuto separato. I certificati non equivalgono a edifici o abitazioni uniche e presentano bias di copertura. I gruppi A4, A3, A2, A1, B, C, D, E, F, G devono essere esclusivi, riconciliati col totale; definire la validità e deduplicare sulla fonte originaria quando possibile.

**ADD-HOUSING-01:** «non occupata da persone residenti» **non** equivale a seconda casa, immobile vuoto tutto l'anno o abitazione inutilizzata. La fonte deve attestare esattamente quel concetto e l'unità «abitazione». L'esistenza delle variabili di sezione non prova ancora la copertura 27/27; aggregare su codici coerenti, escludere duplicati e gestire le sezioni speciali con regole dichiarate.

**H04:** l'input è la **stessa** tabella giornaliera già sottoposta ai controlli H03: un anno intero, 27 Comuni, un'associazione cella-Comune stabile, temperature in °C. La media giornaliera qui è la stima (Tmin + Tmax)/2, non un'osservazione oraria. Non presentare una cella di griglia come media areale comunale o un CDD come disagio domestico. La validazione spaziale/altimetrica resta una verifica distinta.

## Contratti input dei tre candidati

### H05 e ADD-HOUSING-01

Script: `scripts/prepare_v0_3_housing_candidates.py`.

CSV normalizzato: `municipality_code,municipality,reference_date,data_scope,group,count`.
Codice ISTAT di 6 cifre, nome coerente con `data/municipalities.csv`, data ISO e conteggi interi non negativi. Tutte le categorie incluse, **anche gli zeri effettivamente attestati**. Non riempire arbitrariamente classi mancanti/soppresse. Il parser blocca annualità multiple e discordanza tra somma categorie e totale.

- H05: `data_scope=valid_residential_ape`; gruppi `A4,A3,A2,A1,B,C,D,E,F,G,total`; periodo unico esplicito del campione.
- Abitazioni: `data_scope=all_census_dwellings`; `reference_date=2023-12-31`; gruppi `occupied_by_residents,not_occupied_by_residents,total`.

Esempi di esecuzione PowerShell (file originali conservati localmente fuori da Git):

```powershell
$run = "outputs/quality/h05_$(Get-Date -Format yyyyMMdd-HHmmss)"
uv run --locked python scripts/prepare_v0_3_housing_candidates.py `
  --indicator h05_ape_fg `
  --original-export data/downloads/ape_residential_original.csv `
  --normalized-csv outputs/quality/h05_input/ape_residential_normalized.csv `
  --out-dir "$run"
```

```powershell
$run = "outputs/quality/housing_$(Get-Date -Format yyyyMMdd-HHmmss)"
uv run --locked python scripts/prepare_v0_3_housing_candidates.py `
  --indicator dwellings_not_occupied_by_residents `
  --original-export data/downloads/istat_census_sections_2023_original.zip `
  --normalized-csv outputs/quality/housing_input/dwellings_2023_normalized.csv `
  --out-dir "$run"
```

### H04

Script: `scripts/prepare_cdd_eurostat_2025_v0_3.py`. Richiede lo stesso CSV normalizzato giornaliero H03, non solo un file di gradi giorno già calcolati.

```powershell
$run = "outputs/quality/h04_$(Get-Date -Format yyyyMMdd-HHmmss)"
uv run --locked python scripts/prepare_cdd_eurostat_2025_v0_3.py `
  --original-tmin-netcdf data/downloads/NWIOItminDAY.nc `
  --original-tmax-netcdf data/downloads/NWIOItmaxDAY.nc `
  --normalized-daily-csv outputs/quality/h03_input/nwioi_2025_municipal_daily.csv `
  --reference-year 2025 `
  --out-dir "$run"
```

Tutti gli script producono 27 righe di **anteprima**, `qa.json` e `manifest.json` SHA-256, in directory nuove e non sovrascrivibili. Non certificano il mapping originale → normalizzato, l'esattezza di filtri APE o dell'estrazione/associazione spaziale ARPA.

## Gate necessari prima dell'integrazione nella release v0.3

- H05: verificare provenienza, data, destinazione d'uso residenziale, **validità** APE, filtri, duplicati ed esaustività delle classi. Se il dato è solo «tutti gli usi», bloccare H05.
- Abitazioni: scaricare il file originale ISTAT per sezioni 2023, verificare dizionario e somma per Comune; distinguere non residenti da immobili sfitti o seconde case.
- H04: acquisire Tmin/Tmax NetCDF, dimostrare georeferenziazione/celle scelte, controllare tutte le 9.855 osservazioni del 2025 e la sensibilità al rilievo montano.
- Per tutti: assicurare 27/27, unità/periodo coerenti, record originali e checksum, verifiche campionarie indipendenti, revisione umana prima di `human_approved`.

## Fonti primarie

- EPAH Handbook 1: https://energy-poverty.ec.europa.eu/system/files/2024-05/EPAHhandbook_diagnosis_finalpdf.pdf
- Eurostat metadata climatici: https://ec.europa.eu/eurostat/cache/metadata/EN/nrg_chdd_esms.htm
- ARPA NWIOI: https://www.arpa.piemonte.it/scheda-informativa/dataset-griglia-nwioi
- ISTAT dati per sezioni: https://www.istat.it/notizia/dati-per-sezioni-di-censimento/
- ENEA SIAPE: https://siape.enea.it/filtro-dati
- Piemonte APE per Comune: https://www.dati.gov.it/node/view-dataset/dataset?id=63401619-1a9f-4382-8399-84c20c59dad0
