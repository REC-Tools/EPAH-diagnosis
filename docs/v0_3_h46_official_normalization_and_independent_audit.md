# H46 (v0.3) — normalizzazione ISTAT 2024 e audit indipendente

**Stato:** `technical_draft_do_not_publish`. **Ambito:** 27 Comuni di Sinergie in Canavese. **Dati canonici:** nessuna modifica. L'esecuzione degli script non costituisce approvazione scientifica.

## Fonte, definizione e categorie

Dataflow censuario ISTAT `IT1,DF_DCSS_ISTR_LAV_PEN_2_TV_3,1.0`, anno 2024, residenti di almeno 15 anni (`AGE_NOCLASS=Y_GE15`), sesso totale (`GENDER=T`), indicatore `RESPOP_AV`, cittadinanza totale, istruzione tutte, altre dimensioni `ALL`. I metadati SDMX originali contengono il codebook `CL_FORZE_LAV` con le relazioni gerarchiche: `1` occupato e `12` in cerca di occupazione appartengono a `22` forze di lavoro; `24`, `4`, `5`, `7` sono sottocategorie di `23` non forze di lavoro; `99` è il totale 15+.

`Tasso H46 = 100 × valore ISTAT CUR_ACT_STAT=12 / valore ISTAT CUR_ACT_STAT=22`.

I dati 2024 di lavoro sono **stime decimali**, non conteggi interi da arrotondare. `unknown=0` non è una modalità rilevata nella fonte: la normalizzazione lo scrive soltanto dopo aver verificato in ciascun Comune `22+23=99`, `1+12=22` e `24+4+5+7=23`, con tolleranza assoluta non superiore a `0.000001` persone. Le percentuali finali sono arrotondate a due decimali; i valori fonte restano invariati. Un tasso di disoccupazione comunale è una **proxy socioeconomica**, non un indicatore diretto di povertà energetica.

## Esecuzione PowerShell

Per prima cosa, recuperare la PR che contiene questi due script, senza eliminare i file locali non tracciati. Eseguire dalla radice del progetto e usare cartelle di output **sempre nuove**:

```powershell
$src = "outputs/quality/h46_api_20261106-161656"
$run = "outputs/quality/h46_normalized_$(Get-Date -Format yyyyMMdd-HHmmss)"

uv run --locked python scripts/normalize_h46_istat_sdmx_v0_3.py `
  --original-export "$src/ISTAT_censimento_2024_lavoro_original.csv" `
  --metadata-xml "$src/ISTAT_H46_dataflow_metadata.xml" `
  --registry data/municipalities.csv `
  --expected-original-sha256 264191619b7c8206a8cbf584e427744f407d52d2f457cdf848067febb1af5116 `
  --out-dir "$run"

$preview = "outputs/quality/h46_preview_$(Get-Date -Format yyyyMMdd-HHmmss)"
uv run --locked python scripts/prepare_unemployment_15_plus_v0_3.py `
  --original-export "$src/ISTAT_censimento_2024_lavoro_original.csv" `
  --normalized-csv "$run/labour_2024_normalized.csv" `
  --registry data/municipalities.csv `
  --out-dir "$preview"

uv run --locked python scripts/audit_h46_istat_independent_v0_3.py `
  --original-export "$src/ISTAT_censimento_2024_lavoro_original.csv" `
  --metadata-xml "$src/ISTAT_H46_dataflow_metadata.xml" `
  --normalized-csv "$run/labour_2024_normalized.csv" `
  --normalization-manifest "$run/normalization_manifest.json" `
  --registry data/municipalities.csv `
  --preview-csv "$preview/unemployment_15_plus_preview.csv" `
  --out-file "$run/independent_audit.json"
```

Il normalizzatore produce `labour_2024_normalized.csv` (27×6 = **162 righe**), `normalization_qa.json`, `normalization_manifest.json`. Il builder H46 esistente produce le 27 percentuali, il QA e gli hash. L'auditor **non importa nessuno dei due script precedenti**: legge nuovamente l'export originale, controlla metadati e categorie, riproduce i 162 valori e le 27 percentuali, confronta gli hash e verifica 243 riconciliazioni per sesso e 243 per età. Le celle per fascia d'età omesse sono interpretate come zero **solo dopo la verifica delle somme con il totale pubblicato**, mai immesse nel tasso H46.

## Checkpoint sull'originale del 6 novembre 2026

- Export originale SHA-256: `264191619b7c8206a8cbf584e427744f407d52d2f457cdf848067febb1af5116`.
- XML metadati SHA-256: `af4a60465e822d0bffcdc0d68f6af8a575caf06ad57009d9092fa7f2aff9e151`.
- Registry SHA-256: `e7af9959a64200e2278f3c48c48a417aff8d09aea018622ed6b59a6c85505d27`.
- Nel test tecnico su quei file: 27/27 Comuni; 162 righe normalizzate; 243 verifiche per sesso, 243 per età; 11 celle d'età omesse e conciliabili a zero; tasso territoriale ponderato provvisorio **7,27%**.

Questi dati sono un riferimento per la revisione e non entrano nella repository: conservare gli originali e gli output sotto cartelle ignorate da Git. Non copiare la preview nella matrice canonica finché una persona responsabile non approva il mapping, la comparabilità e i limiti di disaggregazione.

## Verifiche prima della promozione

```powershell
uv run --locked pytest -q tests/test_h46_sdmx_normalization_and_audit_v0_3.py tests/test_unemployment_15_plus_v0_3.py
uv run --locked pytest -q
uv run --locked python scripts/check_documentation.py
```

Fonti: [metadati SDMX ISTAT](https://esploradati.istat.it/SDMXWS/rest/dataflow/IT1/DF_DCSS_ISTR_LAV_PEN_2_TV_3/1.0/?detail=Full&references=Descendants), [tavola del Censimento permanente](https://esploradati.istat.it/databrowser/#/it/censpop/categories/CPA_POP/DCSS_ISTR_LAV_PEN_2_TV/IT1,DF_DCSS_ISTR_LAV_PEN_2_TV_3,1.0).
