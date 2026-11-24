# Dashboard dei 23 candidati v0.5

Destinatario: tecnico che deve vedere in un unico luogo i 18 candidati EPAH e
le cinque proposte abitative, senza confondere contratto, fonte e valore.

## Comando unico

Dal checkout installato con il lockfile del progetto:

```powershell
uv run --locked epah methodology dashboard --out-dir work/v05-dashboard-01
```

Aprire `work/v05-dashboard-01/index.html`. La destinazione deve essere nuova.
Senza input numerici si vedono tutte le 23 schede, definizioni, denominatori,
fonti, limiti e prossimi passi. Un contratto documentato non è un indicatore
calcolato: in questa modalità le serie numeriche presenti sono zero.

## Collaudare i 23 grafici senza dati reali

```powershell
uv run --locked epah methodology dashboard --example --out-dir work/v05-example-01
```

Genera 23 grafici con territori e valori inventati. Gli avvisi `DATI SINTETICI`
compaiono anche nei grafici. Non è il risultato dei 27 Comuni. Le due modalità
non si mescolano: `--example` rifiuta input numerici o portali reali.

## Collegare le evidenze locali già disponibili

```powershell
uv run --locked epah methodology dashboard --source-pack work/v05-source-review-20261123-02 --out-dir work/v05-local-01
```

Il comando verifica il portale fonti con il suo audit esistente, lo copia
nel nuovo pacchetto e ripete l'audit sulla copia. Non scarica dati.
Mostra lo stato delle fonti affitto, UTCI ed ERP; i conteggi originali di
famiglie in affitto sono un grafico separato di fonte, non la quota V05-19.
Nessuna nuova formula o aggregazione comunale è eseguita. Dati e stati dei
cataloghi originali, matrice canonica e approvazioni restano invariati.

## Visualizzare valori precalcolati

```powershell
uv run --locked epah methodology dashboard --observations work/observations.json --out-dir work/v05-values-01
```

Il file `observations_template.json` prodotto dalla dashboard offre il
contenitore vuoto. Ogni osservazione deve avere esattamente questi campi:

```json
{
  "schema_version": "0.5-dashboard-observations-1",
  "input_kind": "precomputed_technical_review",
  "scientific_approval": false,
  "publication_allowed": false,
  "observations": [
    {
      "indicator_id": "V05-19",
      "geo_code": "001007",
      "geo_name": "Alpette",
      "scope": "municipality_target_not_verified",
      "period": "2021",
      "series": "Quota da revisionare",
      "unit": "percent",
      "value": null,
      "missing_reason": "not_acquired",
      "source_url": "https://www.istat.it/comunicato-stampa/abitazioni-occupate/",
      "source_note": "Nessuna quota calcolata: conservare universo, fonte e decisioni pendenti."
    }
  ]
}
```

Un valore presente è una stringa decimale, ad esempio `"0"`, con
`missing_reason: null`. Un valore assente è `null` con motivo `not_acquired`,
`suppressed`, `not_applicable` o `not_responded`. Zero resta zero; le assenze
non sono imputate. Unità e scope devono coincidere con il contratto della
proposta: i benchmark nazionali non possono essere trasformati in dati
comunali cambiando il codice geografico. La scala rimane sempre visibile.

Il renderer separa periodi, scale e serie in grafici distinti, conserva
etichette e decimali nella tabella e rifiuta duplicati e valori non finiti.
Il file fornito è conservato byte per byte con il suo hash. La conformità del
tracciato non certifica autenticità delle fonti, formule, campionamento o
confrontabilità: occorre una revisione umana del dato e del metodo.

## Output e limiti

- `index.html`: dashboard, ricerca, filtro disponibilità, grafici SVG e tabelle.
- `snapshot.json`: contratti e valori visualizzati, senza promozioni scientifiche.
- `observations.csv`: stessi valori e missingness, etichette protette per il CSV.
- `readiness.csv`: visualizzazione supportata e calcolo implementato separati.
- `manifest.json`: hash dei file del pacchetto.
- `source_review/`: eventuale copia verificata del portale fonti.

Le schede restano leggibili senza JavaScript; tutti i grafici sono offline.
I soli collegamenti alle fonti richiedono rete. Lo stato rimane
`technical_draft_do_not_publish`; nessuna autorizzazione alla pubblicazione.

I 23 calcoli e le acquisizioni non sono completati da questo comando.
Per completarli occorrono, per ogni candidato, fonte accessibile, universo,
periodo, geografia, regole di calcolo e QA: vedere le decisioni aperte nelle
schede e la [metodologia](v0_5_methodology.md). I cinque candidati abitativi
restano distinti nel [catalogo abitativo](v0_5_housing_candidates.md).


## Anteprima tecnica autorizzata della quota affitto 2021

```powershell
uv run --locked epah methodology dashboard --source-pack work/v05-source-review-20261123-02 --rent-preview --out-dir work/v05-dashboard-affitto-01
```

L’opzione esplicita calcola solo V05-19 per i 27 Comuni: `100 × RENT / ALL`,
sui quattro conteggi originali del 2021, riletti dagli XML e verificati con i
metadati e gli hash del portale sottoposto ad audit. Il denominatore è ALL,
non la somma delle tre categorie. L’universo esclude le famiglie senza tetto.
Il 2021 è un riferimento storico distinto dall’obiettivo 2025. Il significato
dei conteggi decimali resta da chiarire: l’anteprima non risolve questo limite.

La richiesta esplicita del 24 novembre 2026 autorizza l’anteprima con i sei
residui osservati, senza correzioni né tolleranze: Colleretto Castelnuovo,
Forno Canavese e Valprato Soana `0.000001`; Ingria, Ribordone e San Colombano
Belmonte `-0.000001`. Il residuo è `ALL − (OWN + RENT + OTH_OR)`.
Un cambiamento del loro insieme o valore blocca questa anteprima e richiede
una nuova revisione. Anni diversi, dati mancanti, nuovi flag e denominatori
non positivi sono rifiutati. Non si possono mescolare valori V05-19 forniti
esternamente con quelli calcolati nello stesso pacchetto.

La scheda affitto mostra un grafico di 27 quote, la tabella dei sei residui,
i limiti e i valori di calcolo. `rent_preview.csv` conserva tutti gli input,
residui e percentuali. Il calcolo usa 50 cifre significative e ROUND_HALF_EVEN;
il grafico arrotonda a due decimali. CSV e snapshot conservano la precisione
di calcolo, non una frazione periodica infinita. Nessun arrotondamento degli
input, correzione o aggiornamento dei dati canonici. Le altre 22 formule
non sono calcolate automaticamente. `readiness.csv` distingue implementazione
del calcolo e presenza dei valori. Tutti gli output restano bozze tecniche,
con approvazione scientifica e autorizzazione alla pubblicazione false.


## Decisione esplicita e pubblicazione della sola quota affitto

Il 24 novembre 2026 Tommaso Ferrucci, responsabile della valutazione dichiarato
in chat, ha approvato definizione e calcolo con le riserve del dossier e ha
espressamente autorizzato la pubblicazione. La dichiarazione è registrata in
`v0_4_rent_decision_20261124.json`: è una registrazione della decisione umana,
non una firma digitale, una revisione esterna o una certificazione EPAH.

```powershell
uv run --locked epah methodology dashboard --source-pack work/v05-source-review-20261123-02 --rent-preview --decision docs/v0_4_rent_decision_20261124.json --out-dir work/v05-affitto-decisione-01
```

L’opzione `--decision` verifica un’impronta dell’intero contratto V05-19,
formula, anno, universo, precisione, originali e 27 righe calcolate. Cambiare
uno di questi elementi richiede una nuova decisione. La presenza di un file
JSON non autentica da sola l’identità di chi decide: il referente deve aver
approvato esplicitamente, come documentato dalla dichiarazione conservata.

La dashboard mostra nome, ruolo, data, approvazione limitata e permesso di
diffusione. I sei residui e tutti i limiti rimangono visibili. La validazione
statistica completa della fonte resta da completare; gli altri 22 indicatori
non ricevono approvazioni. I cataloghi originali e i precedenti pacchetti di
revisione non vengono riscritti retroattivamente.

Per la diffusione si usa **soltanto la cartella `rent_publication/`** prodotta
nel pacchetto: contiene pagina della quota con grafico e tabelle, CSV,
decisione, snapshot e manifest. Non contiene gli originali di revisione,
UTCI, ERP, percorsi privati o le altre schede. La dashboard completa rimane
`technical_draft_do_not_publish`, con `publication_allowed=false` a livello
globale e `publication_subset_allowed=true` per questa sola quota. Il
pacchetto della quota dichiara `approved_with_reservations`, pubblicazione
ammessa e ambito scientifico `definition_and_calculation_only`; non afferma
una validazione statistica completa. Il comando prepara i file autorizzati,
non li carica su un sito. Conservare tutta la cartella per non perdere i limiti.
