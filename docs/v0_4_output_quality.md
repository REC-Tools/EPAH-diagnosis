# v0.4 — Controllo di qualità degli output

Le pipeline v0.4 producono un atlante e un fascicolo HTML/CSV/PDF. L'audit aggiunge un controllo indipendente sulla coerenza dei file, senza approvare le fonti.

Comando PowerShell:

```powershell
$qa = "outputs/quality/v04-output-audit-$(Get-Date -Format yyyyMMdd-HHmmss).json"
uv run --locked python scripts/audit_v0_4_output_quality.py `
  --pack outputs/v0.4-review-esempio `
  --atlas outputs/v0.4-atlas-esempio `
  --json-out $qa
```

Verifiche: SHA-256, presenza di CSV/HTML/PDF/metadati, 27 righe per indicatore, date e unità coerenti, assenze distinte dagli zeri, identità delle osservazioni incorporate nell'HTML e sezioni PDF rilevabili.

Il PDF viene letto con pypdf: **non** è una validazione visiva di impaginazione, accessibilità o stampa. La verifica scientifica degli originali resta indipendente. L'esito positivo indica solo `technical_output_consistency_passed`, con `scientific_approval=false`, `publication_allowed=false` e `visual_review_completed=false`.

La suite usa fixture sintetiche; prima dell'uso istituzionale effettuare ispezione reale di HTML su mobile, grafici e PDF A4, audit fonti e revisione umana.