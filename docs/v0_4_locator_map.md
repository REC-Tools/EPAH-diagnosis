# v0.4 — Tavola di orientamento dei 27 Comuni

La tavola è un elemento grafico **di riferimento**, senza punteggi, colori di vulnerabilità o valori di indicatori. Usa i confini del bundle pilota (o un altro GeoJSON CRS84/WGS84 con gli stessi 27 codici ISTAT), proiettati in **EPSG:32632** per una scala metrica.

## Uso da PowerShell

```powershell
$run = "outputs/v0.4-locator-$(Get-Date -Format yyyyMMdd-HHmmss)"
uv run --locked python scripts/build_v0_4_municipality_locator.py `
  --geojson outputs/v0.1.0-pilot/municipality_profile.geojson `
  --out-dir $run
```

Output in cartella nuova: `municipality_locator.png`, `.svg`, `.pdf` in formato **A4 orizzontale**, `metadata.json` (indice nome–codice) e `manifest.json` (SHA-256).

I 27 poligoni sono contrassegnati da numeri progressivi associati a **nome completo e codice ISTAT** nell'indice laterale; un punto di etichetta viene cercato *all'interno* del poligono, tenendo conto di buchi e multipoligoni. La cartografia non modifica le geometrie originali e non deduce l'esattezza amministrativa dal solo rendering.

L'output resta `technical_draft_do_not_publish`. Prima dell'uso pubblico è necessaria la revisione dell'origine e della data di validità dei confini. Nessuna modifica a catalogo canonico, dati, approvazioni o mappe storiche.
