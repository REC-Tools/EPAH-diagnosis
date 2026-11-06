# H03 v0.3 — estrazione automatica da NetCDF ARPA NWIOI (anteprima tecnica)

**Stato:** `technical_draft_do_not_publish`. Il programma non modifica il catalogo,
`data/verification_matrix.csv`, i GG normativi DPR 412/1993 o i risultati v0.2.
L'estrazione è offline, senza download automatico, con **un unico anno di riferimento
2025** e 27 Comuni. Non sono ancora state acquisite/interpretate le intestazioni
interne dei NetCDF ufficiali: i test di questa PR usano **solo originali sintetici**.

## Perché occorre la maschera regionale

[ARPA Piemonte — dataset NWIOI](https://www.arpa.piemonte.it/scheda-informativa/dataset-griglia-nwioi)
fornisce temperature **minime (TN)** e **massime (TX)** giornaliere su griglia
regolare **0,125°**, con aggiornamento quotidiano e licenza **CC BY 2.5 Italia**.
ARPA chiarisce che le celle **fuori dal Piemonte** possono contenere
interpolazioni non attendibili: la **maschera ufficiale 0/1 è quindi un input
obbligatorio**. Non si permette di aggirare questo controllo.

Originali necessari, da conservare localmente senza caricarli in Git:

- [NetCDF Tmin](https://www.arpa.piemonte.it/static/data/NWIOItminDAY.nc) — `NWIOItminDAY.nc`;
- [NetCDF Tmax](https://www.arpa.piemonte.it/static/data/NWIOItmaxDAY.nc) — `NWIOItmaxDAY.nc`;
- **maschera regionale NWIOI**, presente nella [pagina dataset ARPA](https://www.arpa.piemonte.it/scheda-informativa/dataset-griglia-nwioi), conservata con il suo nome originale; nessun URL diretto alla maschera è stato verificato in questa PR;
- `data/geography/municipalities_2026.geojson` — poligoni comunali ISTAT 2026
  in CRS84, rigenerabili dalla [procedura geografica](geography.md);
- `data/municipalities.csv` — registro canonico **27 codici ISTAT**.

Le due serie ARPA possono essere aggiornate nel tempo. L'estrattore registra
gli SHA-256 originali e rifiuta modifiche dei file durante la lavorazione.
Il confronto con hash verificati indipendentemente è opzionale, ma raccomandato.

## Convenzione e scelta geografica

Lo script legge dai NetCDF soltanto le date del **2025** e accetta solo un
calendario giornaliero completo (365 date senza duplicati), latitudine e
longitudine **monodimensionali e allineate** tra Tmin, Tmax e maschera,
temperature con unità esplicite Celsius o Kelvin e celle mascherate come `1`.
La griglia può presentare la latitudine in ordine crescente o decrescente.
Variabili multiple o unità ignote causano un errore, senza inferenza silenziosa.

Per ogni Comune, il programma cerca i **centri di celle mascherate validi
all'interno del poligono** ISTAT. Se più celle risultano interne, sceglie
quella vicina alla media dei vertici del contorno principale, come regola
riproducibile di selezione, **non come punto sede comunale certificato**.
Se non ci sono centri di celle interni, seleziona la cella mascherata più
vicina al **bordo** del poligono, fino a una distanza massima di **25 km**
(modificabile con `--max-fallback-km`); altrimenti il programma si interrompe.
La distanza è approssimata localmente e serve solo come gate tecnico.

Ogni assegnazione, inclusi i fallback, viene riportata nell'audit: **una
cella per Comune** e quindi nessuna media areale o correzione di quota.
La risoluzione grigliata e le variazioni altimetriche sono limitazioni
importanti nelle valli alpine. Il metodo annuale è quello del
[candidato H03](v0_3_h03_annual_hdd_candidate.md), basato sulla
[convenzione Eurostat HDD](https://ec.europa.eu/eurostat/cache/metadata/EN/nrg_chdd_esms.htm):
`Tmean_est=(Tmin+Tmax)/2`; per `Tmean_est <= 15 °C`, `HDD_day=18-Tmean_est`, altrimenti zero.
**Non** coincide con il dato statico normativo o con l'HDD operativo ARPA
calcolato nel punto della sede comunale.

## Esecuzione in PowerShell

Dopo aver acquisito gli originali con browser o il proprio client di download,
salvarli in `data/downloads/` (esclusa dal Git). Acquisire i confini ISTAT:

```powershell
uv run --locked python scripts/acquire_municipality_boundaries.py
```

Eseguire la pipeline **senza preparare manualmente alcun CSV di temperature**:

```powershell
uv run --locked python scripts/extract_nwioi_hdd_2025_v0_3.py `
  --tmin-netcdf data/downloads/NWIOItminDAY.nc `
  --tmax-netcdf data/downloads/NWIOItmaxDAY.nc `
  --mask-netcdf data/downloads/NWIOI_region_mask.nc `
  --boundaries-geojson data/geography/municipalities_2026.geojson `
  --reference-year 2025 `
  --out-dir outputs/quality/h03_nwioi_2025_review_01
```

**Attenzione:** `NWIOI_region_mask.nc` è un **nome locale illustrativo**, non
il nome ufficiale confermato del file di maschera. Inserire il percorso vero
conservato dall'originale ARPA; non fabbricare una maschera.

Se necessario, specificare `--tmin-variable`, `--tmax-variable` e
`--mask-variable` con i **nomi letti nei metadata** dei file. L'estrattore
riconosce assi geografici `lat`/`latitude`, `lon`/`longitude` e
`time`/`valid_time`. Se il formato ufficiale è diverso (assi 2D, unità
sconosciute, proiezione differente, maschera non binaria), **si ferma**:
non convertire i file senza documentare e testare la nuova convenzione.

Si possono fornire gli hash originali attesi tramite `--expected-tmin-sha256`,
`--expected-tmax-sha256`, `--expected-mask-sha256`,
`--expected-boundaries-sha256`. Ogni tentativo necessita di una cartella
`--out-dir` **nuova**, per conservare intatte le evidenze precedenti.

## Output e controlli

| File | Contenuto |
| --- | --- |
| `nwioi_2025_municipal_daily.csv` | Esattamente **27 × 365 = 9.855** righe; nome/codice, data, cella, coordinate, Tmin/Tmax in °C |
| `extraction_qa.json` | Schema, unità, variabili, hash, maschera applicata, celle interne/fallback, distanze, limiti e stato |
| `h03_preview/hdd_eurostat_annual_preview.csv` | 27 HDD annui calcolati riutilizzando la **pipeline H03 già testata**, non dati canonici |
| `h03_preview/qa.json` e `h03_preview/manifest.json` | QA e provenance della pipeline H03 originale |

Il controllo rigetta: mancanza di Comuni o date, geometrie non coerenti con
il registro, coordinate/geometrie fuori Piemonte, maschera non binaria,
assegnazioni a celle non mascherate, griglie Tmin/Tmax differenti, doppioni
temporali, valori mancanti o non finiti, Tmin > Tmax e temperature fuori
range di sicurezza. Gli output vengono creati solo **dopo** tutti i controlli.

**Distinguere due livelli:** `extraction_qa.json` documenta la buona riuscita
dell'estrazione tecnica in una specifica esecuzione; nel pacchetto annuale
originale gli indicatori di revisione geospaziale/scientifica possono restare
`false`, perché l'attribuzione di una cella rappresentativa al Comune richiede
ancora una **valutazione metodologica umana**. Nessuno di questi flag equivale
all'approvazione scientifica/istituzionale o alla misura diretta di povertà
energetica.

## Stato e prossime verifiche

- **Realizzato e testato:** parser NetCDF generico con assi CF standard, verifica
  maschera 0/1, associazione geometrica e passaggio diretto al calcolo H03.
- **Non ancora dimostrato:** compatibilità degli **originali ARPA effettivamente
  scaricati** con il contratto di dimensioni, coordinate, variabili e unità.
- **Da valutare prima della v0.3 finale:** fallback geografici, quota della
  cella, attribuzione geografica, licenza e uso istituzionale, effetti della
  scelta Tmin/Tmax anziché media giornaliera osservata.

Test offline (senza rete):

```powershell
uv run --locked pytest -q tests/test_nwioi_hdd_extraction_v0_3.py
uv run --locked pytest -q
python scripts/check_documentation.py
```

Questa pipeline **non** scrive `data/verification_matrix.csv`,
`config/indicators.json`, `data/indicators/**` o altri file canonici.
