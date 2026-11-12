# EPAH v0.4 — Step 3: schede comunali di due pagine

**Decisione:** per i 27 Comuni realizziamo una **scheda A4 verticale di due pagine**, destinata a tecnici e amministratori. La prima pagina è una sintesi leggibile durante gli incontri; la seconda è il registro completo delle misure e delle relative fonti.

## Struttura delle due pagine

**Pagina 1 — Profilo.** Nome completo e codice ISTAT, conteggio delle serie disponibili/non acquisite, prime sei osservazioni in ordine del catalogo (non scelte per valore o rango), anno, unità e tre cautele metodologiche. Se non ci sono valori, compare una dicitura esplicita: *nessun dato acquisito*.

**Pagina 2 — Tracciabilità.** Tutti gli indicatori previsti (fino a 16 nell'atlante v0.4), compresi quelli assenti, in due colonne. Per ciascuno: ID, denominazione, valore/unità quando disponibile, periodo, fonte e numeratore/denominatore se conservati nell'export. Nessuna stima, ranking, somma di proxy o classificazione di rischio.

## Output e comandi

Da PowerShell, con atlante e fascicolo tecnico **già verificati e collegati allo stesso snapshot**:

```powershell
$run = "outputs/v0.4-schede-$(Get-Date -Format yyyyMMdd-HHmmss)"
uv run --locked python scripts/build_v0_4_municipal_sheets.py `
  --atlas-dir outputs/v0.4-atlas-verificato `
  --review-dir outputs/v0.4-review-verificato `
  --out-dir $run
```

La cartella contiene `pdf/001001.pdf` e gli altri 26 file nominati con i codici ISTAT effettivi del registro, `index.html` (indice accessibile con nomi), `schede_27_comuni.pdf` (54 pagine), `metadata.json` e `manifest.json` con gli hash SHA-256. Se i file originali non sono presenti, non vengono creati risultati reali.

**Integrazione automatica:** `scripts/build_v0_4_output_hub.py` (Step 2) crea ora anche la sottocartella `sheets/` e collega le schede dal portale HTML, senza modificare le copie dell'atlante o del fascicolo tecnico.

## Condizioni di accettazione

- 27 documenti PDF, ciascuno **esattamente di due pagine A4**; un volume aggregato di 54 pagine.
- Stessi valori, periodi, nomi, fonti e flag `not_acquired` del CSV originale. Zero non è mai sostituito alla mancanza.
- Hash e legame atlas/review verificati prima dell'export, con errore in caso di manomissione o input di un altro snapshot.
- Il layout è verificato nei test sintetici per formato e struttura. **Non è ancora validato visivamente sui nomi e gli input locali reali**: rendere le pagine in PNG e ispezionare caratteri, salti, linee e leggibilità prima dell'uso istituzionale.

## Governance

Le schede mantengono `technical_draft_do_not_publish`, `scientific_approval=false` e `publication_allowed=false`. Non sono prova di povertà energetica delle famiglie, non costituiscono analisi causale, non assegnano graduatorie e non modificano i dati canonici. La v0.3.0 rimane la release stabile.

**Passo successivo (Step 4):** armonizzare etichette, definizioni e universi statistici nell'atlante, nel PDF e nelle schede, con catalogo editoriale separato e controllato.
