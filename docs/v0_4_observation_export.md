# v0.4 — Export tecnico delle osservazioni dell'atlante

Questa PR aggiunge un export **sperimentale** di uno snapshot v0.3 già verificato: una riga per Comune e indicatore, inclusi gli indicatori non acquisiti. Non modifica alcun dato canonico e non produce indici compositi.

Esecuzione da PowerShell:

```powershell
$run = "outputs/v0.4-observations-$(Get-Date -Format yyyyMMdd-HHmmss)"
uv run --locked python scripts/export_v0_4_atlas_observations.py `
  --atlas-dir outputs/atlante-verificato `
  --out-dir $run
```

La directory di output deve essere nuova. Si ottengono `observations.csv`, `metadata.json` e `manifest.json` con SHA-256. Il programma verifica checksum dell'atlante e del registro, esattamente 27 codici ISTAT, presenza/assenza, unità, periodi e valori finiti. Le serie non acquisite riportano `missing_reason=not_acquired` e valore vuoto, mai zero.

**Limiti importanti:** l'atlante conserva i valori di visualizzazione e i periodi, ma non i numeratori, denominatori, l'universo statistico o la versione geografica degli originali. Le relative colonne restano **vuote**, senza ricostruzione né falsa certificazione. La serializzazione float non garantisce il recupero della precisione testuale dell'originale ISTAT: per un contratto realmente lossless serve un adapter a monte dalle sorgenti auditati H46/H50/H47.

Questo export non esegue una nuova verifica indipendente delle fonti. Il suo stato resta `technical_draft_do_not_publish`; nessuna approvazione scientifica o istituzionale è implicita.

Test mirati:

```powershell
uv run --locked pytest -q tests/test_atlas_observations_v0_4.py
```
