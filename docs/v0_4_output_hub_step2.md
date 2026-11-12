# Step 2 v0.4 — Output integrati per tecnici e amministratori

**Decisione adottata:** l'atlante HTML è l'interfaccia principale; una sintesi PDF di due pagine orienta amministratori e tecnici; il PDF tecnico, CSV e i metadati costituiscono il livello di audit. Si conferma il pubblico prioritario dello Step 1: **tecnici e amministratori locali**.

Questo passaggio **non costruisce nuove osservazioni**: richiede un atlante verificato e il fascicolo tecnico creato a partire esattamente da quell'atlante. Controlla gli hash SHA-256 e i contratti di disponibilità prima di confezionare copie byte-per-byte degli originali.

## Esecuzione PowerShell

```powershell
$atlas = "outputs/v0.4-atlas-verificato"
$review = "outputs/v0.4-review-verificato"
$out = "outputs/v0.4-output-hub-$(Get-Date -Format yyyyMMdd-HHmmss)"
uv run --locked python scripts/build_v0_4_output_hub.py `
  --atlas-dir $atlas `
  --review-dir $review `
  --out-dir $out
```

Aprire **`index.html`** nella nuova cartella: contiene collegamenti relativi e offline a:

- `atlas/index.html` — mappe e indicatori interattivi (prodotto principale);
- `sintesi.pdf` — breve guida di due pagine con inventario di evidenza e caveat, senza valori comunali;
- `review/review.pdf` e `review/review.html` — fascicolo tecnico integrale;
- `review/observations.csv`, `review/metadata.json` — valori, periodi, universi disponibili;
- `manifest.json` — hash di tutti i file inclusi nel pacchetto.

L'atlante e il fascicolo sono **copiati senza ricalcolo**; non viene sovrascritto né modificato alcun file originale. Output in cartella nuova, fuori dalle directory di input. Il generatore blocca file fuori manifest, symlink, checksum incoerenti, differenze tra i due inventari e snapshot non corrispondenti.

**Stato:** `technical_draft_do_not_publish`. La sintesi non misura povertà energetica familiare e non attribuisce punteggi o approvazioni. Tutti i test automatici usano fixture sintetiche; la verifica del PDF generato su dati reali e della navigazione offline su mobile deve essere effettuata prima di qualsiasi diffusione.

## Accettazione dello Step 2

1. I link del portale aprono i file nell'archivio spostato/coperto, senza internet.
2. I 27 Comuni e i metadati coincidono tra atlante e review-pack.
3. Il PDF di sintesi contiene due pagine con l'elenco degli indicatori e lo stato di acquisizione, non i valori né graduatorie.
4. La CI passa e un lettore verifica leggibilità di portale, PDF A4 e contenuti sul proprio computer.

## Passaggio allo Step 3

La decisione successiva riguarda **la struttura delle 27 schede comunali**: un profilo breve 1–2 pagine, con valori e fonti disponibili, collegato al portale e senza indice composito.