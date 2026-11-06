# v0.3 — H03: gradi giorno annuali climatici, stima da temperatura grigliata

**Perimetro:** 27 Comuni della Green Community Sinergie in Canavese. **Anno candidato:** 2025 (1 gennaio–31 dicembre). **Stato:** `technical_draft_do_not_publish`. Questo è un **nuovo descrittore di esposizione climatica**, non un indicatore diretto di povertà energetica.

L'identificativo **H03** è interno al nostro inventario EPAH v0.3. La fonte **F08** è ARPA Piemonte, dataset su griglia **NWIOI/NWOI**. La pipeline è completamente separata dai gradi giorno **normativi** `heating_degree_days` (DPR 412/1993) già presenti nel catalogo v0.2. Non modificarli né confrontare i due numeri come se avessero uguale periodo e formula.

## Definizione e convenzione

Si adotta la **convenzione climatica Eurostat** per i gradi giorno di riscaldamento (HDD):

- Stima della temperatura media del giorno: `Tmean_est = (Tmin + Tmax) / 2`, in °C, ricavata dalle **temperature minima e massima giornaliere interpolate sulla griglia ARPA**.
- Se `Tmean_est <= 15 °C`, `HDD_day = 18 °C − Tmean_est`; altrimenti `HDD_day = 0`.
- `HDD_2025 = somma(HDD_day)` su **tutti i 365 giorni** del calendario 2025; unità **°C·giorno**.
- Si arrotonda **solo il risultato annuo** a due decimali. Non sono ammesse interpolazioni automatiche di giorni mancanti né sostituzioni del dato del Comune vicino.

| Esempio illustrativo | Tmin | Tmax | Tmean stimata | HDD giorno |
| --- | ---: | ---: | ---: | ---: |
| Giornata fredda | 10 °C | 14 °C | 12 °C | 6 °C·giorno |
| Soglia inclusa | 14 °C | 16 °C | 15 °C | 3 °C·giorno |
| Giornata mite | 15 °C | 16 °C | 15,5 °C | 0 |

**Differenza da evitare:** il metodo non è `max(0, 18−Tmean)` per tutti i giorni. Con `Tmean = 16 °C`, la convenzione Eurostat conta **0**, non 2.

La **media stimata da Tmin/Tmax non coincide necessariamente con la media giornaliera osservata**, né rende i valori confrontabili senza ulteriori controlli con gli HDD Eurostat elaborati su serie proprie. Le soglie sono una **scelta esplicita di metodologia candidata**: non attribuire ad ARPA l'adozione del metodo Eurostat in questo nuovo calcolo.

Fonti di metodologia e dati:

- [Eurostat, metadata Heating and Cooling Degree Days](https://ec.europa.eu/eurostat/cache/metadata/EN/nrg_chdd_esms.htm) — formula, soglie 15/18 °C, somma annua.
- [ARPA Piemonte, dataset su griglia NWIOI](https://www.arpa.piemonte.it/scheda-informativa/dataset-griglia-nwioi) — temperature giornaliere **Tmin/Tmax** interpolate, griglia regolare **0,125°**, NetCDF, licenza **CC BY 2.5 IT**.
- [ARPA Piemonte, stima GG sul municipio](https://www.arpa.piemonte.it/dato/stima-dei-gradi-giorno-riscaldamento-comune) — **prodotto diverso**, stime quindicinali su edificio municipale, con una finestra storica limitata. Non concatenare o confondere con gli HDD 2025 da griglia.
- [Indicatore v0.2: gradi giorno normativi DPR 412](indicator_04_heating_degree_days.md) — **serie statica, non osservazione climatica del 2025**.

## Stato degli input: nessuna acquisizione reale in questa PR

ARPA distribuisce gli originali NetCDF di temperatura [minima](https://www.arpa.piemonte.it/static/data/NWIOItminDAY.nc) e [massima](https://www.arpa.piemonte.it/static/data/NWIOItmaxDAY.nc). Possono essere file aggiornati quotidianamente: **conservare copie originali e relativi SHA-256**. Non committarli in Git.

Lo script **non legge ancora la struttura interna dei NetCDF** e **non verifica** che la cella associata a ciascun Comune sia effettivamente la cella più vicina al municipio, al centroide, o rappresentativa dell'area. Per l'input richiede quindi un **CSV normalizzato** di temperature Tmin/Tmax per una cella dichiarata per Comune, accompagnato dai due originali conservati. L'estrazione/mappatura geospaziale deve essere verificata sul dataset prima di promuovere risultati, nella revisione finale v0.3. Le coordinate sono controllate per plausibilità, **non contro il NetCDF**.

I piccoli Comuni montani possono condividere una cella. Una griglia di circa 0,125° può non rappresentare le quote e i microclimi della Valle Soana. Il metodo produce una **stima per punto/cella**, non una media climatica dell'intero territorio comunale. Nessun risultato derivato da questo metodo va usato per stimare consumi delle famiglie, classificare povertà energetica o selezionare beneficiari.

## Contratto del CSV normalizzato

Dalla matrice climatica originale estrarre **soltanto il 2025**, in Celsius, con intestazioni UTF-8 e i campi obbligatori:

| Campo | Vincolo |
| --- | --- |
| `municipality_code` | Sei cifre ISTAT, deve appartenere al registro dei 27 Comuni |
| `municipality` | Nome del Comune corrispondente (accenti confrontati in modo normalizzato) |
| `date` | Un giorno calendario ISO `YYYY-MM-DD`, **2025** |
| `grid_cell_id` | Identificativo non vuoto, stabile della cella grigliata scelta per Comune |
| `grid_latitude`, `grid_longitude` | Coordinate **della cella**, non del Comune, in gradi decimali |
| `tmin_c`, `tmax_c` | Temperature giornaliere in **°C**, decimali con punto e non NaN/blank |

Devono esserci **esattamente 27 × 365 = 9.855 osservazioni** nel 2025, una per Comune e giorno. Per ogni Comune è consentita una sola cella dichiarata per l'intero anno. Una cella condivisa da più Comuni deve avere **le stesse temperature** sullo stesso giorno. La copertura richiesta riguarda **365 giorni** per ciascun Comune.

Il parser rifiuta giorni mancanti o duplicati, date fuori anno, province/codici estranei, nomi non corrispondenti, cambiamenti di cella, coordinate impossibili o non plausibili per il Piemonte, `Tmin > Tmax`, temperature fuori dal limite di sicurezza −65/+65 °C e segnaposto non numerici. Non riempie valori mancanti. Supporta anche un **anno bisestile esplicitamente richiesto** (366 giorni) per future elaborazioni, da documentare separatamente: il 2025 rimane l'annata di riferimento di questa PR.

## Esecuzione offline — solo anteprima tecnica

Scaricare e conservare **entrambi** gli originali ARPA con data e SHA-256, preparare il CSV normalizzato e usarli solo in cartelle locali non tracciate:

```powershell
uv run --locked python scripts/prepare_hdd_eurostat_2025_v0_3.py `
  --original-tmin-netcdf data/downloads/NWIOItminDAY.nc `
  --original-tmax-netcdf data/downloads/NWIOItmaxDAY.nc `
  --normalized-daily-csv outputs/quality/h03_input/nwioi_2025_municipal_daily.csv `
  --reference-year 2025 `
  --out-dir outputs/quality/h03_eurostat_2025_review_01
```

Facoltativo: `--expected-tmin-sha256` e `--expected-tmax-sha256`, riferiti ai digest indipendentemente verificati degli originali, per rilevare revisioni silenziose. Il programma **si ferma** se la cartella output esiste già.

La cartella di revisione contiene:

- `hdd_eurostat_annual_preview.csv` — 27 righe, HDD annui stimati, ID della cella, coordinate, numero giorni e marcatura non pubblicabile;
- `qa.json` — copertura, controlli, numero celle distinte, intervallo e **media non ponderata dei 27 valori comunali**, che **non** equivale a una media territoriale areale o demografica;
- `manifest.json` — hash SHA-256 di originali Tmin/Tmax, CSV normalizzato, registro comunale e file risultanti. I flag di revisione della mappatura restano `false`.

**Non** vengono modificati `data/verification_matrix.csv`, `config/indicators.json`, i prodotti v0.2 o i gradi giorno normativi. **Nessun valore reale è acquisito né verificato da questa PR**; i test impiegano soltanto temperature sintetiche. La verifica scientifica e dei dati reali di tutti i candidati v0.3 resta programmata **alla conclusione della fase di sviluppo**.

## Test

```powershell
uv run --locked pytest -q tests/test_hdd_eurostat_2025_v0_3.py
uv run --locked pytest -q
python scripts/check_documentation.py
python scripts/check_v0_3_evidence.py
```
