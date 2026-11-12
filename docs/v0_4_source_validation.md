# v0.4 — Validazione indipendente delle fonti H03/H04 e H05

**Il test automatico non equivale alla validazione scientifica.** Questo audit aggiunge un secondo percorso Python (senza importare i builder originali) per ricostruire i **totali annuali H03/H04** dal CSV giornaliero NWIOI e i **conteggi F/G H05** dall'export residenziale normalizzato. Verifica i checksum SHA-256 degli originali forniti e le ricevute tecniche esistenti, ma **non ripete** la decodifica dei NetCDF né verifica in modo autonomo il filtro degli originali APE. Non aggiorna dati canonici o revisione umana.

## Esecuzione — H03/H04

Richiede i file originali ARPA e i file generati dall'estrattore NWIOI del 2025 e dai builder HDD/CDD. Nessun file di dati reali è incluso nel Git.

```powershell
$run = "outputs/quality/v04-validation-$(Get-Date -Format yyyyMMdd-HHmmss)"
uv run --locked python scripts/validate_v0_4_sources.py `
  --require climate `
  --climate-daily outputs/quality/h03_nwioi_2025_review_01/nwioi_2025_municipal_daily.csv `
  --h03-dir outputs/quality/h03_nwioi_2025_review_01/h03_preview `
  --h04-dir outputs/quality/h04_2025_review_01 `
  --tmin-netcdf data/downloads/NWIOItminDAY.nc `
  --tmax-netcdf data/downloads/NWIOItmaxDAY.nc `
  --mask-netcdf data/downloads/NWIOI_region_mask.nc `
  --boundaries data/geography/municipalities_2026.geojson `
  --extraction-qa outputs/quality/h03_nwioi_2025_review_01/extraction_qa.json `
  --out-dir $run
```

**Criteri di blocco:** 27×365 osservazioni complete nel 2025, un'unica cella per Comune, nessun valore giornaliero incoerente per celle condivise, temperatura fisica, hash esatti di Tmin/Tmax/maschera/GeoJSON/CSV, SHA dei manifest H03 e H04, confronto autonomo delle due formule Eurostat con le 27 anteprime. Lo stato di riproduzione è `technical_replay_passed_review_pending`, **non** `Dato validato`.

## Esecuzione — H05

```powershell
$run = "outputs/quality/v04-h05-validation-$(Get-Date -Format yyyyMMdd-HHmmss)"
uv run --locked python scripts/validate_v0_4_sources.py `
  --require h05 `
  --h05-normalized outputs/quality/h05_input/residential_ape_normalized.csv `
  --h05-original data/downloads/APE_residential_original.csv `
  --h05-dir outputs/quality/h05_technical_preview_01 `
  --out-dir $run
```

Il controllo richiede 27 Comuni × 11 categorie (A4,A3,A2,A1,B–G,total), scope `valid_residential_ape`, un unico periodo, denominatori e classi riconciliati, corrispondenza al preview, SHA degli originali e QA tecnica non approvata. **Non** prova che l'export originale fosse davvero filtrato per usi residenziali, che gli APE siano univoci e validi, o che il campione sia rappresentativo delle abitazioni. Quelle verifiche richiedono originali e revisione metodologica.

Per richiedere entrambi i percorsi in un'unica esecuzione, omettere `--require` e passare tutti i parametri. Se manca una fonte, viene scritto un `validation.json` con stato `blocked_missing_originals` e il comando termina con codice **2**, senza falsi `PASS`. Il risultato salva anche `manifest.json` con checksum; le directory di QA devono essere nuove.

## Gate scientifici ancora aperti

| Gate | Condizione |
| --- | --- |
| Integrità software | Suite CI GitHub e controlli anti-manomissione |
| Riproduzione tecnica da CSV normalizzati | Script presente, eseguirlo con i file locali veri |
| NetCDF ARPA → celle comunali | Conferma indipendente di maschera, selezione e rappresentatività altimetrica |
| Originali APE → residenzialità | Deduplicazione, filtri e periodo certificati indipendentemente |
| Validazione umana / pubblicazione | Provvedimento esplicito, separato dalla release software |

Non trattare H03/H04 come i GG normativi DPR 412/1993, né H05 come percentuale dello stock immobiliare totale. **Non promuovere** candidati nel catalogo canonico sulla base di questo audit.
