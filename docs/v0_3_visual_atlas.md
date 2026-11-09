# EPAH v0.3 — Atlante esplorativo (NON pubblicabile)

**Questo è il nuovo percorso di visualizzazione v0.3**, separato da
`epah dashboard v0.2`, dai PDF v0.2 e dal vecchio
`scripts/generate_diagnostic_maps.py`. Le vecchie mappe PNG **non sono
riutilizzate**. I 9 indicatori storici rimangono quelli del bundle pilota,
con lo stesso anno, valore e perimetro: un nuovo renderer **non corregge**
eventuali problemi dei dati originali.

La versione esplorativa ha **13 slot fissi**: 9 indicatori del pilota,
H47 (quota popolazione 0–11), H50 (basso livello d'istruzione 25–64),
H46 (disoccupazione sulle forze di lavoro 15+) e H03 (HDD annuali
stimati da griglia ARPA). L'ID H03 è **interno** all'inventario e non
sostituisce i gradi-giorno **normativi** nel pilota. Non si sommano
indicatori con unità, periodo o denominatore diversi. SNAI è
*categorico*, mai un numero su una scala lineare.

## Primo run: 9 indicatori disponibili, 4 dichiarati assenti

Aprire **PowerShell** dalla root del repository. Non serve eseguire uno
script `.ps1` (e quindi non serve modificare l'Execution Policy).

```powershell
uv sync --python 3.11 --locked --group dev
uv run --locked pytest -q tests
$run = "outputs/v0.3-atlas-$(Get-Date -Format yyyyMMdd-HHmmss)"
uv run --locked python scripts/build_v0_3_visual_atlas.py --bundle outputs/v0.1.0-pilot --out-dir $run
Start-Process (Resolve-Path "$run/index.html")
```

Il builder richiede il bundle v0.1.0 pilota *completo*, con 27 Comuni,
9 dimensioni e checksum coerenti. Se è assente o alterato **si ferma**:
non legge file `data/indicators/**` a caso, né usa le mappe PNG della
v0.1/v0.2. Il file `.venv` non viene modificato dalle visualizzazioni.

## Secondo run: 10 indicatori quando è disponibile H47

Scaricare il **nuovo** artefatto `posas-2026-h47-technical-review` da
[Actions run #42189307301](https://github.com/REC-Tools/EPAH-diagnosis/actions/runs/42189307301)
(via GitHub con accesso, entro i limiti di retention) e salvarlo fuori
dal Git, per esempio `data/downloads/posas-2026-h47-technical-review.zip`.
È necessario **l'artefatto successivo alla PR #143**, contenente
`h47_independent_reproduction_audit.json` e `sex_totals_verified=true`.
Il primo artefatto del 6 novembre **non basta**, perché saltava una
verifica per sesso. Se l'artefatto è scaduto, rilanciare
`v0.3 ISTAT POSAS 2026 official source QA` da GitHub Actions; non
cambiare silenziosamente lo SHA ufficiale se ISTAT aggiorna la fonte.

```powershell
$run = "outputs/v0.3-atlas-$(Get-Date -Format yyyyMMdd-HHmmss)"
uv run --locked python scripts/build_v0_3_visual_atlas.py `
  --bundle outputs/v0.1.0-pilot `
  --h47-zip data/downloads/posas-2026-h47-technical-review.zip `
  --out-dir $run
Start-Process (Resolve-Path "$run/index.html")
```

Le 27 osservazioni demografiche H47 non sono prese dal bundle storico:
sono importate solo dopo controlli sui codici ISTAT, nomi, percentuali,
anno, stato di QA, hash delle anteprime e corrispondenza fra audit
indipendente e ricevuta dell'originale ISTAT. La QA tecnica non è
un'approvazione scientifica o istituzionale.

## Successivo run: fino a 13 indicatori

Quando saranno state effettivamente prodotte le anteprime dei tre
candidati rimanenti (non quelle sintetiche usate nei test). Per H46 la
procedura reale ISTAT (acquisizione, normalizzazione, audit) è descritta in
[v0_3_h46_official_normalization_and_independent_audit.md](v0_3_h46_official_normalization_and_independent_audit.md):
l'atlante accetta i conteggi H46 decimali (stime ISTAT), senza arrotondarli.

```powershell
$run = "outputs/v0.3-atlas-$(Get-Date -Format yyyyMMdd-HHmmss)"
uv run --locked python scripts/build_v0_3_visual_atlas.py `
  --bundle outputs/v0.1.0-pilot `
  --h47-zip data/downloads/posas-2026-h47-technical-review.zip `
  --h50-dir outputs/quality/h50_preview_<data> `
  --h46-dir outputs/quality/h46_preview_<data> `
  --h03-dir outputs/quality/h03_nwioi_2025_review_01/h03_preview `
  --out-dir $run
```

Ogni cartella opzionale deve contenere il proprio CSV preview,
`qa.json` e `manifest.json` **originali**. Il builder verifica
integrità degli SHA, 27 codici e formule coerenti, senza certificare
che il CSV normalizzato sia stato acquisito correttamente dalla fonte
ufficiale. **Non indicare parametri opzionali di cui non si possiedono
ancora dati reali**: l'interfaccia mostrerà chiaramente `DATI ASSENTI`.

### Prodotti nuovi

| File | Descrizione |
| --- | --- |
| `index.html` | Dashboard offline con 13 indicatori selezionabili, anche quando mancano valori |
| `charts/<indicatore>_map.png` / `.svg` | Mappa *nuova* con colori assoluti, anno, fonte e n/27 |
| `charts/<indicatore>_distribution.png` / `.svg` | Dot plot dei 27 Comuni e mediana non ponderata, oppure frequenze SNAI |
| `atlas_data.json` | Valori realmente presentati e disponibilità di ogni indicatore |
| `atlas_manifest.json` | Checksum SHA-256, originali, identificativi e serie mancanti |
| `README_REVIEW.txt` | Istruzioni e limiti per i revisori |

Le mappe non copiano PNG o SVG storici: rigenerano i poligoni WGS84/CRS84
in **EPSG:32632** per mantenere proporzioni metriche, rispettano
multipart e fori e utilizzano una scala **sequenziale `cividis`**
anche per le variabili socioeconomiche. **Non** usano verde/rosso
come giudizio di benessere. L'indicatore SNAI usa una legenda
categorica distinta e non è ordinato per vulnerabilità. Ogni
indicatore ha la sua scala: non confrontare colori tra mappe
con unità differenti. Nei grafici la mediana è descrittiva, non una
soglia statistica di povertà energetica.

## Controlli e limitazioni

- La dashboard non usa CDN, mappe esterne, chiamate a rete o cookie.
- **Nessun indice composito**, nessun ranking inter-indicatore e nessuna
  misura diretta della povertà energetica. Niente dati CIT in quarantena.
- Il builder **rifiuta** input incompleti (non sostituisce con zero), hash
  incoerenti, nomi/codici/anni discordanti e cartelle di output già esistenti.
- Restano identici i dati e le approvazioni del bundle v0.1/v0.2; le
  anteprime v0.3 restano `technical_draft_do_not_publish`.
- Il manifest segnala anche eventuali **serie numeriche perfettamente
  identiche**, utili per revisione delle fonti, senza cambiarne i dati.
- **Miglioramenti visivi ≠ correzioni dei dati**: se una cartografia
  continua a mostrare valori inattesi, confrontare per Comune
  `atlas_data.json` con originale + data dictionary, prima della
  revisione finale e della diffusione.
- Non crea automaticamente il PDF istituzionale, schede A4 v0.3 o
  nuovi valori reali H50/H46/H03: sono sviluppi separati.

```powershell
uv run --locked pytest -q tests/test_v0_3_visual_atlas.py
python scripts/check_documentation.py
```
