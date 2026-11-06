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

L'export censuario comunale 2024, i suoi codici di condizione lavorativa, le modalità
"non rilevato" e l'eventuale totale di forza lavoro **non sono ancora stati acquisiti
e confrontati**. Per questo il software accetta soltanto una tabella normalizzata,
accompagnata dall'export originale conservato immutato. Nessun dato reale o misura
comunale è inclusa nella PR. Le statistiche mensili nazionali sul lavoro non sono
 sostituti delle misure censuarie comunali.

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
| `persons` | Numero intero non negativo, senza soppressioni o segnaposto |

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
`labour_force + inactive + unknown = population_total`. Il denominatore deve
essere **maggiore di zero**. Uno zero **reale** di disoccupati è ammesso e va
 distinto da un dato indisponibile. Numero totale atteso: **27 × 6 = 162 righe**.
Non includere una seconda dimensione di sesso o age-band dettagliate insieme al totale.

## Esecuzione offline, senza modificare i dati canonici

Salvare l'export originale ufficiale fuori dal repository versionato e costruire
la tabella normalizzata **soltanto dopo** aver documentato la mappatura dei codici:

```powershell
uv run --locked python scripts/prepare_unemployment_15_plus_v0_3.py `
  --original-export data/downloads/ISTAT_censimento_2024_lavoro_original.csv `
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
stato effettivamente ricavato da esso. **Questa verifica è rinviata alla fase
finale**, non aggirata.

## Verifiche alla chiusura dello sviluppo v0.3

1. Identificare tavola comunale ISTAT del 2024, variabili lavoro e metadati.
2. Riconciliare i codici originali di occupati, disoccupati, inattivi,
   forze lavoro e totali con il contratto normalizzato, senza imputazioni.
3. Confrontare i 27 Comuni e un campione di celle con l'export originale,
   annata, universo d'età, eventuali soppressioni e piccole numerosità.
4. Confrontare H46 e H50 solo con anni, universi e denominatori esplicitati;
   valutare significato e limiti scientifici di entrambi.
5. Registrare approvazione metodologica prima di qualsiasi integrazione nel
   catalogo canonico. Non derivare classifiche/indici di povertà energetica.

```powershell
uv run --locked pytest -q tests/test_unemployment_15_plus_v0_3.py
python scripts/check_documentation.py
python scripts/check_v0_3_evidence.py
```
