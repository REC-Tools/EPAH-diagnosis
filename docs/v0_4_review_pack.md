# v0.4 — Fascicolo tecnico unico HTML / CSV / PDF

Questa pipeline produce tre rappresentazioni **dello stesso insieme di osservazioni**, a partire da un atlante v0.3 o v0.4 già verificato, senza cambiare il valore di alcuna misura e senza generare score territoriali.

```powershell
$run = "outputs/v0.4-review-$(Get-Date -Format yyyyMMdd-HHmmss)"
uv run --locked python scripts/build_v0_4_review_pack.py `
  --atlas-dir outputs/atlante-v04-verificato `
  --out-dir $run
```

La cartella **nuova** conterrà:

- `observations.csv`: 27 record per indicatore, valore o motivazione esplicita di mancata acquisizione.
- `review.html`: tabella filtrabile per indicatore e Comune/codice ISTAT, unità/periodo/fonte, accessibile offline.
- `review.pdf`: fascicolo A4 orizzontale, una sezione per indicatore, 27 Comuni in ordine di codice, senza classifiche.
- `metadata.json`, `observations_manifest.json`, `manifest.json` e `README_REVIEW.txt`: limiti e provenienza con hash SHA-256.

**Controllo di integrità:** ogni file dichiarato nel manifest dell'atlante (HTML, dati e grafici) deve essere presente con lo stesso SHA-256. L'esportazione CSV riusa `atlas_observations_v0_4` e i valori risultanti alimentano sia HTML che PDF: i contenuti non vengono ricomputati indipendentemente. Per consultare le mappe, aprire l'`index.html` dell'atlante originale; il fascicolo non altera né replica le geometrie.

Nessuna serie assente è imputata a zero. Numeratori/denominatori non conservati dall'atlante originale rimangono vuoti. Il PDF è **documentazione tecnica**, non attestazione delle fonti. Gli indicatori descrittivi non misurano la prevalenza di povertà energetica familiare e non autorizzano pubblicazione o allocazione delle risorse.

**Stato:** `technical_draft_do_not_publish`; release software ancora v0.3.0. Test riproducibili con fixture sintetiche; uso sui dati reali vincolato a audit e autorizzazioni separate.
