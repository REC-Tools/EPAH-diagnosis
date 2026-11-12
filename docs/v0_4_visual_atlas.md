# v0.4 — Atlante esteso (H04, H05 e abitazioni non occupate da residenti)

L'atlante v0.4 estende **senza alterare** il builder stabile v0.3. Riutilizza e verifica la pipeline storica del bundle pilota, poi aggiunge tre posizioni: **H04** CDD climatici annuali stimati 2025, **H05** quota di attestati APE residenziali validi in F/G e **ADD-HOUSING-01** abitazioni non occupate da residenti (non sinonimo di case vuote).

Il totale è **16 slot** (nove indicatori del pilota, quattro candidati già supportati v0.3 e tre nuovi). Quelli senza anteprime restano marcati `DATI ASSENTI`: nessuna simulazione di osservazioni.

## Comando PowerShell

```powershell
$run = "outputs/v0.4-atlas-$(Get-Date -Format yyyyMMdd-HHmmss)"
uv run --locked python scripts/build_v0_4_visual_atlas.py `
  --bundle outputs/v0.1.0-pilot `
  --h03-dir outputs/quality/h03_2025/h03_preview `
  --h04-dir outputs/quality/h04_2025 `
  --out-dir $run
```

Usare `--h04-dir` **solo insieme** a `--h03-dir`, prodotti dal **medesimo CSV giornaliero originale** e dagli stessi NetCDF Tmin/Tmax. Gli SHA-256 dei tre input e, per ogni Comune, periodo, cella e 365 giornate devono coincidere. Se mancano originali ARPA, **omettere entrambi i parametri**: il risultato mostra esplicitamente l'assenza.

Parametri ulteriori facoltativi: `--h47-zip`, `--h50-dir`, `--h46-dir` (come v0.3), `--h05-dir`, `--housing-dir`. Per H05 e il descrittore abitativo usare soltanto le rispettive anteprime di `scripts/prepare_v0_3_housing_candidates.py`, dopo acquisizione e normalizzazione degli originali: l'algoritmo verifica registro, hash, conteggi, percentuali, data e flag di mancata approvazione. **H05 non può essere ottenuto dagli APE di tutti gli usi.**

Output: HTML offline, PNG/SVG tematici disponibili, `atlas_data.json`, `atlas_manifest.json` e istruzioni di revisione. La serie APE descrive il **campione di certificati validi**, non la prestazione dell'intero stock; la voce abitativa non misura automaticamente immobili inutilizzati. Gli HDD normativi del pilota restano separati da H03/H04. Tutti gli output sono `technical_draft_do_not_publish`, senza promozione canonica, compositi o autorizzazioni istituzionali.

La verifica degli hash confronta le anteprime con il rispettivo manifest, **non sostituisce** audit indipendente degli originali o approvazione scientifica. Il rendering deve essere ispezionato con la geometria effettiva prima di un eventuale uso istituzionale.

## Step 4 — Definizioni armonizzate

Gli atlanti **v0.4 prodotti dopo lo Step 4** contengono `catalogo_editoriale.json` e i campi `editorial` in `atlas_data.json`. Le definizioni non cambiano valore, ID, fonte o anno degli indicatori. I vecchi snapshot non vengono riscritti; la v0.3 resta invariata. Consultare [Step 4](v0_4_editorial_catalog_step4.md).

## Step 5 — Etichette cartografiche selettive

I nuovi output v0.4 riportano **fino a cinque nomi** sulle mappe dei Comuni con poligoni più estesi, senza sovrapposizioni. Tutti i 27 nomi restano disponibili nella tabella HTML e nei dot plot di distribuzione; questa scelta grafica non rappresenta un indicatore o una priorità. [Procedura e contratto Step 5](v0_4_thematic_map_labels_step5.md).

## Step 6 — Grafici comunali ordinati per codice ISTAT

I grafici numerici v0.4 riportano tutti i **27 nomi** su righe separate, in ordine ISTAT, non per valori. Le barre SNAI mostrano solo conteggi per categoria. Le scelte grafiche sono documentate in `distribution_policy` e in [Step 6](v0_4_distribution_charts_step6.md).
