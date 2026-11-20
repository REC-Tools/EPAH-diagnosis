# Preparare la richiesta di aggregati ERP per i 27 Comuni

Il pacchetto rende concreta la richiesta descritta nel
[dossier delle fonti comunali](v0_5_housing_source_feasibility.md). Serve al
tecnico incaricato per chiedere i dati necessari a V05-21 e V05-22; non contiene
un dato ERP acquisito o approvato. Stato: `technical_draft_do_not_publish`.

## Generare una nuova bozza

```powershell
uv run --locked epah methodology erp-request --registry data/municipalities.csv --reference-date 2025-12-31 --out-dir work/v05-erp-request-01
```

Il comando usa il lettore esistente del registro, richiede 27 identità uniche
con codici ISTAT di sei cifre e conserva l'hash dei byte originali. La data
richiesta è esplicita; l'anno obiettivo dell'analisi resta 2025. Non viene
assegnata come data dello stock a una risposta ancora assente.

Il risultato comprende:

- `request.md`: bozza con richiesta degli aggregati ed elenco completo dei Comuni;
- `response_template.json`: traccia facoltativa, con 27 record e tutti i conteggi
  inizialmente null, data effettiva e provenienza da compilare nella risposta;
- `README_REVIEW.md`: istruzioni per il tecnico e definizioni dei campi proposti;
- `manifest.json`: esito non inviato, hash del registro e dei file del pacchetto.

La destinazione deve essere nuova, anche se quella esistente è vuota. Il
pacchetto viene esposto solo quando tutti i file sono pronti; nessun prodotto
precedente è sovrascritto. Nessuna rete o funzione di invio è implementata.

## Conteggi separati e compatibilità

La traccia distingue totale ERP, occupati, locati, totale sfitti, assegnabili,
non assegnabili e sfitti per manutenzione/altre cause/causa sconosciuta.
Ogni campo parte da null. Occupati e locati non sono sinonimi; i conteggi di
assegnabilità richiedono la definizione e l'insieme di riferimento dell'ente,
che può essere limitato ai soli sfitti. Questi assi non sono addendi: non
sommarli fra loro né ricavare resti senza una partizione attestata dalla fonte.

Il modello ha versione `0.5-erp-response-template-draft-2` e il manifest
`0.5-erp-request-packet-2`. Le copie della prima bozza restano conservate;
non vengono aggiornate o migrate. Rigenerare in una destinazione nuova per
ottenere i campi aggiunti. Comando, flag e campi precedenti restano disponibili;
non esiste una migrazione automatica fra le due versioni. L'import locale
descritto sotto accetta esplicitamente una copia mappata secondo la versione 2;
non interpreta tabelle arbitrarie dell'ente e non attiva calcoli diagnostici.

## Importare una risposta locale, senza invii

Il nuovo comando prepara una tabella dei 27 Comuni a partire da una copia
compilata del modello v2. Conservare separatamente anche l'originale ricevuto
dall'ente e il mapping delle sue colonne, se il formato iniziale è diverso.
Non si deducono corrispondenze, categorie o perimetri da una tabella sconosciuta.

```powershell
uv run --locked epah methodology erp-import --response work/risposte-erp-mappate.json --registry data/municipalities.csv --out-dir work/erp-import-01
```

Il risultato, in una destinazione nuova, comprende:

- `inputs/response.json` e `inputs/registry.csv`: copie degli esatti byte letti;
- `responses.csv`: tabella nel medesimo ordine del registro, con nove conteggi,
  stato dichiarato dalla fonte, data effettiva, contesto e lacune;
- `review.json`: valori ricevuti e riepilogo della disponibilità, con questioni
  da revisionare e differenza fra anno obiettivo 2025 e anno effettivo;
- `README_REVIEW.txt` e `manifest.json`: limiti, istruzioni e hash dei file.

Il CSV conserva i codici ISTAT di sei cifre: nel foglio di calcolo importare
questa colonna come testo. Le celle testuali a rischio formula sono rese
letterali con un apostrofo usando la protezione già impiegata dagli export;
il JSON e la copia dell'input conservano il testo originale.

Tutti i 27 record devono essere presenti: mantenere `not_provided` e null per
i Comuni senza risposta. Nomi e codici devono coincidere con il registro, senza
duplicazioni. Nel formato di scambio i conteggi sono interi JSON non negativi
oppure null; stringhe numeriche, separatori, booleani e frazioni non vengono
convertiti. Le date sono `YYYY-MM-DD` oppure null per la data effettiva ignota.
Gli errori di formato bloccano l'import prima della creazione del prodotto.

Le risposte parziali sono invece conservate e segnalate: contesto assente,
conteggi mancanti o in conflitto con lo stato, zero dichiarato senza totale zero
esplicito o accompagnato da conteggi positivi. `verified_zero` resta una
dichiarazione della fonte, non una validazione del programma. Una data diversa
dal 2025 rimane tale; la differenza di anno non applica un peso di qualità.
Non vengono verificati o imposti rapporti fra occupazione, locazione,
assegnabilità e cause di sfitto: i rispettivi insiemi richiedono evidenza.

Il comando restituisce 0 quando la cartella di revisione è pronta, anche con
lacune dichiarate, e 2 se l'import è bloccato. Nessuna formula, deduplicazione,
somma fra enti o nuova osservazione viene prodotta. `request_sent_as_declared`
copia quanto dichiarato nell'input; `messages_sent_by_tool` e
`network_requests_made` restano zero. Non viene contattato alcun ente.

### Esempio immediato senza dati privati

```powershell
uv run --locked epah methodology erp-import --example --out-dir work/erp-import-demo-01
```

Usa il medesimo importatore e il generatore del modello esistente, con 27 nomi
e codici fittizi. Il pacchetto è marcato **DATI SINTETICI - NON SONO DATI
TERRITORIALI**. Contiene una risposta parziale del 2024, uno zero dichiarato,
un territorio non gestito, un dato non disponibile e 23 mancate risposte.
Aprire `responses.csv` o `review.json`; tutti gli stati scientifici restano falsi.
Il flag `--example` non accetta percorsi di risposte o registri reali.
Per prove fittizie fornite dall'utente usare `--synthetic` con input espliciti;
senza questo flag la fonte è classificata come risposta locale non certificata.

L'importazione non completa V05-21/V05-22: mancano ancora verifica di fonte,
copertura e sovrapposizioni fra enti, cause dello sfitto e denominatore famiglie.
I blocchi UTCI, H03/H04 e H05 restano distinti. Le revisioni manuali possono
essere effettuate successivamente, senza trasformare la disponibilità del
software in autorizzazione alla diffusione dei risultati.

## Revisione locale, senza contatti

La richiesta resta una bozza interna finché il tecnico non decide diversamente.
Generare o revisionare il pacchetto non comporta invio, raccolta o solleciti.

## Revisionare prima dell'invio

Leggere la bozza, confermare data proposta e perimetro, completare firma e
recapiti del tecnico e individuare l'ufficio competente. La
[pagina ufficiale ATC dei contatti](https://www.atc.torino.it/contattaci), consultata
il 19 novembre 2026, riporta `protocollo@atc.torino.it` e la PEC `atc@pec.atc.torino.it`.
Sono recapiti generali, non un referente nominativo verificato del dataset;
non sono inseriti automaticamente in un invio e nessun contatto è stato effettuato.

Va bene ricevere una tabella già usata dall'ente, con dizionario delle colonne:
il modello JSON non impone un formato di consegna e non è un loader operativo.
La data effettiva della fonte può differire dal 31 dicembre 2025 e deve essere
dichiarata. Il patrimonio gestito da ATC non si somma a quello comunale senza
verificare se si tratti degli stessi alloggi.

Gli esiti proposti distinguono `not_provided`, `data_provided`, `verified_zero`,
`not_managed`, `unavailable`. Il pacchetto iniziale è tutto `not_provided`:
nessuno zero è inventato e nessuna assenza dal menu ATC diventa assenza di ERP.
Gli stati sono una proposta di scambio; attribuirli a una risposta richiede
evidenza del rispondente. Non effettuano validazione automatica.

Prima di qualsiasi calcolo conservare originale ricevuto, data, perimetro,
condizioni d'uso, ricevuta e hash; verificare poi mapping, copertura e doppi
conteggi. Il denominatore delle famiglie per V05-21 rimane da acquisire con
periodo e territorio coerenti. Nessuna formula o stato scientifico è promosso.

## Nuovo controllo ISTAT del 19 novembre 2026

Una sola ulteriore richiesta ai metadati del candidato flusso
`DF_DCSS_HUDW_1_COM` ha restituito ancora HTTP 500, senza retry automatici.
Corpo: 365 byte; SHA-256
`aa90e0823148aaa3d4e102922e281cbf0313db2f4fa5de37208d114f8baea638`,
uguale al precedente errore osservato. Non è una prova di indisponibilità dei
dati in ogni canale, né conferma l'identità o il periodo del nuovo flusso.
Non si utilizzano dati nazionali per riempire i 27 Comuni. Il lavoro sul
pacchetto ERP prosegue indipendentemente dal ripristino di quel servizio.
