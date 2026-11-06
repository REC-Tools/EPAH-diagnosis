# v0.3 — H46: tasso di disoccupazione comunale (15 anni e più)

**Perimetro:** 27 Comuni Sinergie in Canavese. **Stato:** `technical_draft_do_not_publish`.
Candidato socioeconomico separato dai nove indicatori canonici e dalla release v0.2.
La revisione scientifica complessiva dei nuovi indicatori verrà effettuata alla fine
dello sviluppo v0.3, senza considerare i test tecnici una convalida delle fonti.

## Definizione proposta

`H46_candidate_pct = 100 × unemployed_15_plus / (employed_15_plus + unemployed_15_plus)`

- Numeratore: **disoccupati di 15 anni e più**, nel medesimo universo censuario e periodo.
- Denominatore: **forze di lavoro = occupati + disoccupati**, della stessa fascia d'età.
- Gli **inattivi non sono disoccupati** e non entrano nel denominatore.
- Il valore **non** si ottiene da `100 − tasso di occupazione`.
- La popolazione 15+ è usata **solo come controllo di riconciliazione** e non come
  denominatore del tasso. La quota di disoccupati sulla popolazione è un altro indicatore.

L'universo **15 anni e più** è coerente con definizioni censuarie ISTAT storicamente
utilizzate per il tasso comunale; non equivale automaticamente alla popolazione 15–64,
15–74, o a specifici tassi della Rilevazione sulle forze di lavoro. La comparabilità
tra fonti e anni andrà approvata dopo aver controllato il dizionario del file originale.
L'indicatore è una **proxy di vulnerabilità economica territoriale**: non identifica
famiglie in povertà energetica.

## Fonte individuata e limiti

- **ISTAT — Censimento permanente, risultati**: https://www.istat.it/statistiche-per-temi/censimenti/popolazione-e-abitazioni/risultati/
- **F06** nel registro delle fonti v0.3 e **H46** nel mapping interno EPAH, non ID ufficiali.
- **Anno di lavoro previsto:** 2024; `reference_date = 2024-12-31` è la data
  di riferimento demografico scelta per l'intake, non prova da sola che la tavola
  lavoro comunale abbia proprio quella data.
- **Definizione ISTAT disoccupazione**:
  https://www.istat.it/statistiche-per-temi/focus/dati-alla-mano/cosa-significa/
- La matrice di priorità H46 richiama espressamente **disoccupati / forze di lavoro**.
  La presenza di entrambe le variabili per **27 Comuni e lo stesso universo d'età**
  deve essere dimostrata dall'export e non presunta.

### Acquisizione SDMX 6 novembre 2026 e limiti

Una prima acquisizione reale dell'export ISTAT 2024, dei metadati SDMX e di un
codebook ha coperto **27/27 Comuni**. Lo specifico dataflow è
`IT1,DF_DCSS_ISTR_LAV_PEN_2_TV_3,1.0`; i filtri usati per il calcolo sono
`FREQ=A`, `INDICATOR=RESPOP_AV`, `GENDER=T`,
`AGE_NOCLASS=Y_GE15`, `CITIZENSHIP=TOTAL`, `EDU_ATTAIN=ALL`,
`LOC_DEST=ALL`, `REAS_COMMUTING=ALL`, `TIME_PERIOD=2024`.
I codici della dimensione `CUR_ACT_STAT` sono:

| Codice SDMX | Etichetta ISTAT | Uso nella normalizzazione |
| --- | --- | --- |
| `1` | Occupato | `employed` |
| `12` | In cerca di occupazione | `unemployed` |
| `22` | Forze di lavoro | `labour_force` (totale di controllo) |
| `23` | Non forze di lavoro | `inactive` |
| `99` | Totale | `population_total` (totale di controllo) |

Le voci `24`, `4`, `5`, `7` sono sottocategorie delle non forze
di lavoro: non vanno sommate una seconda volta al codice `23`.
La fonte non restituisce una categoria indipendente «condizione sconosciuta»
nelle osservazioni selezionate: un `unknown=0` normalizzato può essere
ammesso **solo dopo** avere documentato la riconciliazione
`22 + 23 = 99` per ogni Comune entro la precisione stimata, mai come
valore osservato o imputazione silenziosa.

**Il codice delle dimensioni è stato identificato, ma il mapping finale
originale → normalizzato e l'approvazione metodologica restano aperti.**
Questa PR non aggiunge dati reali al catalogo. I confronti con dati da
Rilevazione sulle forze di lavoro o altre fonti richiedono definizioni
coerenti; statistiche mensili nazionali non sostituiscono i dati censuari
comunali.

## Contratto CSV di input

Le colonne sono obbligatorie; i codici ISTAT devono mantenere **sei cifre**:

| Campo | Valore richiesto |
|---|---|
| `municipality_code` | Codice ISTAT del Comune, uno dei 27 della registry |
| `municipality` | Nome ufficiale corrispondente |
| `reference_year` | Esattamente `2024` |
| `age_universe` | Esattamente `15_plus` |
| `sex` | Esattamente `total` |
| `labour_status` | Uno dei sei codici sotto |
| `persons` | Stima numerica non negativa in notazione decimale semplice, es. `7.970101160766249` o `93`, con punto decimale; non usare separatori delle migliaia, esponenti, NaN o segnaposto |

Per ogni Comune devono esserci **sei righe**, una per ciascuna delle seguenti categorie:

| Categoria normalizzata | Significato |
|---|---|
| `employed` | Occupati 15+ |
| `unemployed` | Disoccupati 15+ / in cerca di lavoro **secondo la definizione della fonte** |
| `inactive` | Inattivi / non forze di lavoro |
| `unknown` | Condizione lavorativa non classificata, **solo se attestata dal dizionario** |
| `labour_force` | Forze di lavoro = occupati + disoccupati |
| `population_total` | Popolazione complessiva 15+ nello stesso universo |

Le categorie `labour_force` e `population_total` sono **totali di controllo** e
non vanno aggiunte alle categorie elementari. Se la fonte non riporta il totale
forze di lavoro, non inventare un totale indipendente e poi dichiararlo verificato:
documentare l'eventuale ricostruzione nel dossier di mapping finale. Un valore
`unknown=0` è lecito solo se il dizionario originale garantisce l'esaustività
delle altre categorie; non sostituire gli omessi o i dati soppressi con zero.

Controlli per Comune: `employed + unemployed = labour_force` e
`labour_force + inactive + unknown = population_total`. L'export ISTAT 2024
presenta anche **conteggi stimati frazionari**, non soltanto interi.
La pipeline utilizza `Decimal` dall'input fino alle somme: non arrotonda
i conteggi prima del calcolo della percentuale. Per entrambe le
riconciliazioni ammette uno scarto assoluto massimo di **0,000001 persone**
esclusivamente per il rumore di rappresentazione numerica del file fonte;
lo scarto massimo realmente osservato viene registrato in `qa.json`.
Arrotondare 1,499 persone a 1 o 2 supererebbe la tolleranza.

Il denominatore `labour_force` deve essere **maggiore di zero**. Uno zero
**reale** di disoccupati è ammesso e va distinto da un dato indisponibile.
Le quote finali sono presentate a due decimali, arrotondando **solo alla fine**;
le somme presenti in `qa.json` sono stringhe numeriche per non perdere
precisione durante la serializzazione JSON. Gli input interi rimangono ammessi.

Numero totale atteso: **27 × 6 = 162 righe**. Non includere una seconda
dimensione di sesso o fasce d'età dettagliate insieme al totale.

## Esecuzione offline, senza modificare i dati canonici

Salvare l'export originale ufficiale fuori dal repository versionato e costruire
la tabella normalizzata **soltanto dopo** aver documentato la mappatura dei codici:

```powershell
uv run --locked python scripts/prepare_unemployment_15_plus_v0_3.py `
  --original-export outputs/quality/h46_api_20261106-161656/ISTAT_censimento_2024_lavoro_original.csv `
  --normalized-csv outputs/quality/h46_input/labour_2024_normalized.csv `
  --out-dir outputs/quality/h46_review_01
```

Opzionale: `--expected-original-sha256 <hash_sha256_verificato>` per impedire
l'acquisizione involontaria di una versione diversa dell'export.
La cartella `--out-dir` deve essere nuova. Il programma produce:

- `unemployment_15_plus_preview.csv`: 27 numeratori, denominatori, popolazione,
  percentuali e stato tecnico.
- `qa.json`: controlli sui sei conteggi, copertura, quota ponderata sulle
  **forze lavoro complessive**, non media semplice delle 27 percentuali,
  sconosciuti e comuni con zero disoccupati.
- `manifest.json`: SHA-256 dell'export originale, input normalizzato, registro,
  CSV di output e QA. Gli stati scientifici rimangono `false`.

La presenza e l'hash dell'originale non dimostrano che il CSV normalizzato sia
stato effettivamente ricavato da esso. **Questa verifica è ancora obbligatoria
prima della promozione**, insieme al dizionario e all'audit delle scelte
normalizzative. Il percorso originale nel comando sopra riflette l'acquisizione
locale del 6 novembre; il CSV `outputs/quality/h46_input/labour_2024_normalized.csv`
va prima prodotto con una procedura di mapping documentata. Non generare zeri o
conteggi interi arrotondati per soddisfare il contratto.

## Verifiche alla chiusura dello sviluppo v0.3

1. Conservare originali e checksum dell'intake SDMX 2024 e verificare
   l'autenticità della provenienza.
2. Applicare e documentare il mapping `1`, `12`, `22`, `23`, `99`
   alle sei categorie normalizzate, motivando l'eventuale `unknown=0` con
   riconciliazioni della fonte; non convertire le stime frazionarie a interi.
3. Confrontare tutti i 27 Comuni con le celle originali 15+, i totali
   per sesso e la somma delle fasce d'età; verificare piccole numerosità,
   eventuali soppressioni e residui numerici documentati.
4. Confrontare H46 e H50 solo con anni, universi e denominatori esplicitati;
   valutare significato e limiti scientifici di entrambi.
5. Registrare approvazione metodologica prima di qualsiasi integrazione nel
   catalogo canonico. Non derivare classifiche/indici di povertà energetica.

```powershell
uv run --locked pytest -q tests/test_unemployment_15_plus_v0_3.py
python scripts/check_documentation.py
python scripts/check_v0_3_evidence.py
```
