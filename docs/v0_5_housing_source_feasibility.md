# Famiglie in affitto ed ERP: verifica delle fonti comunali

Verifica del 19 novembre 2026 per V05-19, V05-21 e V05-22. Stato:
`technical_draft_do_not_publish`; nessuna nuova osservazione comunale approvata
o indicatore calcolato. Anno obiettivo 2025, anni delle fonti distinti.

## Aggiornamento successivo della verifica

I metadati ufficiali del flusso affitto sono ora raggiungibili e confermati;
un pilota per Alpette ha restituito dati 2021 e una nota sull'esclusione delle
famiglie senza tetto dal totale. Gli export sui 27 codici hanno invece avuto
timeout: la copertura osservata per l'affitto è 1/27. Vedere il
[nuovo dossier ISTAT](v0_5_istat_section_review.md) per hash, campi e limiti.
L'[acquisizione sequenziale successiva](v0_5_tenure_intake.md) ha ora completato
27/27 snapshot del titolo di godimento, tutti 2021. Denominatore, uso dell'anno
e sei piccoli residui rimangono questioni da revisionare prima del calcolo.
La tabella seguente conserva l'esito precedente al ripristino del servizio.

## Esito concreto precedente al nuovo controllo

| Candidato | Evidenza acquisita | Ostacolo da risolvere |
| --- | --- | --- |
| V05-19, famiglie in affitto | Identificato un candidato flusso censuario comunale; richiesta ai metadati ISTAT conservata | Servizio metadati risponde HTTP 500; nome del flusso, dimensioni, anni e copertura non confermati dalla fonte primaria |
| V05-21, dotazione ERP | Portale ufficiale ATC raggiungibile e sei risposte comunali acquisite | La tabella espone gestioni e alloggi locati/riscattati, non uno stock ERP completo datato; una coppia di righe identiche richiede chiarimento |
| V05-22, sfitto ERP per manutenzione | Verificato il tracciato delle stesse risposte ATC | Non contiene il numero degli alloggi sfitti con causa manutenzione; serve un aggregato specifico dal gestore |

Non si distribuiscono valori nazionali sul territorio. Un esito di ricerca o
un servizio indisponibile non dimostrano assenza di famiglie in affitto o di ERP.

## Acquisizioni locali precedenti e verifica ISTAT

La ricerca circoscritta per nomi di file in `outputs/`, `data/downloads/` e
`artifacts/` non ha individuato export già denominati per affitto/titolo di
godimento o ATC/ERP; ambienti e cache sono stati esclusi. Non è una ricerca
esaustiva in ogni archivio compresso. Gli originali delle sezioni 2023 e il
tracciato già recuperati sono preservati: la loro esistenza non equivale a
un export comunale del titolo di godimento verificato. Nessuna riacquisizione.

Un indice secondario ha segnalato `IT1 / DF_DCSS_HUDW_1_COM / 1.0` come candidato
“Famiglie per titolo di godimento - comuni”, nell'approfondimento censuario 2021.
È una pista di scoperta, non metadato ufficiale confermato e non un dato 2025.
La richiesta primaria effettuata è:

```text
https://esploradati.istat.it/SDMXWS/rest/dataflow/IT1/DF_DCSS_HUDW_1_COM/1.0/?detail=Full&references=Descendants
```

Ha restituito HTTP 500 con errore di connessione del backend. Un solo controllo
sul flusso H46 già usato dal progetto ha dato lo stesso stato e corpo identico
(SHA-256 uguale). Questo indica un ostacolo del servizio osservato nella sessione;
non verifica l'identità del nuovo flusso e non prova che i dati non esistano.
Due richieste metadati, distanziate, senza tentativi automatici o query dati.
Le [istruzioni ufficiali ISTAT](https://www.istat.it/classificazioni-e-strumenti/web-services-sdmx/)
indicano il servizio e il limite di cinque query al minuto per IP.

Al ripristino: confermare il flusso sulla fonte primaria, leggere DSD/codelist e
anni disponibili, poi selezionare i 27 codici e tutte le categorie di godimento
necessarie al totale coerente. Non indovinare ordine delle dimensioni o codici;
non usare il denominatore 2023 con un numeratore 2021 senza decisione esplicita.

## Cosa restituisce realmente ATC

La [notizia ufficiale ATC](https://www.atc.torino.it/notizia/13108) del 5 maggio
2025 collega il [portale del patrimonio](https://giano.casaatcservizi.it/servizio/patrimonio/).
Il portale, consultato nel 2026, mostra un aggiornamento della pagina del
28 aprile 2025: **non attesta la data di riferimento dello stock**.
Il filtro pubblico consulta `search-php/selectPATRIMONIO.php` tramite POST del
solo parametro `comune`; non è un invio di messaggi o una modifica di dati.
Nessun modulo email, login o contatto a terzi è stato utilizzato.

Le otto colonne osservate sono Comune, Indirizzo, Proprietà, Gestione, Alloggi
locati, Alloggi riscattati, Altro (locali commerciali/posti auto), Riscaldamento.
Non sono presenti codice ISTAT, data dello stock o motivo dello sfitto.

| Comune del registro | Codice ISTAT | Righe della risposta, non alloggi ERP | Righe identiche dopo normalizzazione degli spazi |
| --- | --- | --- | --- |
| Castellamonte | 001066 | 3 | Righe 2 e 3 |
| Castelnuovo Nigra | 001067 | 1 | Nessuna |
| Cuorgnè | 001098 | 4 | Nessuna |
| Forno Canavese | 001107 | 1 | Nessuna |
| Pont Canavese | 001199 | 1 | Nessuna |
| Rivara | 001216 | 1 | Nessuna |

Il matching dei sei nomi è stato riesaminato con il registro; il selettore
originale di Cuorgnè è `CUORGNE%`. Non è un'identità ISTAT fornita dal portale.
Gli altri **21 Comuni non compaiono nel menu osservato**: questo non significa
stock nullo o assenza di gestione. Non è stata effettuata alcuna richiesta
inventando selettori per i Comuni assenti.

Le due righe di Castellamonte sono uguali negli otto campi dopo aver uniformato
gli spazi. Senza identificativo di gestione non è dimostrato se rappresentino
lo stesso oggetto: non si eliminano né si sommano automaticamente. Anche gli
alloggi riscattati e i locali/posti auto non si aggiungono implicitamente allo
stock ERP. Gli originali HTML rimangono locali, senza pubblicare indirizzi.

## Ripetere l'audit indipendente

Il controllo riutilizzabile lavora su una risposta HTML già acquisita; non
esegue richieste di rete e non produce un indicatore ERP:

```powershell
uv run --locked python -m epah_diagnosis.atc_source_review_v0_5 --html work/atc-response.html --json-out work/atc-review-01.json
```

I percorsi sono esempi da sostituire con una risposta reale del filtro, non
con l'intera pagina del portale. Il report deve essere nuovo e la directory
genitore già esistente. Il comando rifiuta header/tracciati cambiati, HTML
incompleto e sovrascritture. Segnala celle numeriche mancanti o ambigue e gruppi
di righe identiche, senza sommare né rimuovere righe. Il report non include
indirizzi o nomi personali. Un'uscita zero indica solo ispezione completata:
`result` resta `source_review_required`, anche per una tabella vuota o senza
duplicati. Stock, data, perimetro ERP e identità ISTAT rimangono non verificati.

L'audit delle sei risposte reali ha completato il controllo del tracciato,
identificando la coppia sopra; gli hash degli originali sono invariati.
È un audit della fonte, separato da normalizzazione, calcolo e approvazione.

## Aggregati da richiedere, senza contatti inviati

Per ciascuno dei 27 codici ISTAT occorre preparare una richiesta ad ATC/Comuni
con queste informazioni, preferibilmente riferite al 31 dicembre 2025 oppure
con l'esatta data alternativa dichiarata:

- codice ISTAT e Comune, proprietario/gestore e perimetro ERP/non ERP;
- totale alloggi ERP, occupati/locati, sfitti, assegnabili e non assegnabili;
- sfitti per manutenzione, per altre cause e con causa sconosciuta;
- identificativi aggregabili di gestione per evitare doppi conteggi fra proprietà
  comunale e gestione ATC, senza dati personali degli assegnatari;
- definizioni, inclusioni/esclusioni, data dello stock, copertura, licenza e
  riferimento dell'estrazione; chiarimento delle righe identiche osservate;
- risposta esplicita per stock zero verificato, territorio non gestito oppure
  dato non disponibile. I tre esiti non sono equivalenti.

Servirà poi un denominatore di famiglie residenti territorialmente e temporalmente
coerente per V05-21. La richiesta qui è soltanto preparata: nessun messaggio è
stato inviato. Restano invariati [contratti e stati dei cinque candidati](v0_5_housing_candidates.md).

La richiesta è ora riproducibile con il [pacchetto ERP dei 27 Comuni](v0_5_erp_request_packet.md):
bozza, traccia facoltativa della risposta e manifest. Generarla non invia messaggi
e non trasforma i campi vuoti in dati acquisiti.

## Verifica interna successiva: sezioni 2023 e ISAC

L'[inventario indipendente degli originali locali](v0_5_istat_section_review.md)
conferma 978 righe di sezione per i 27 codici e 138 campi coerenti con il tracciato.
Nessuna variabile del titolo di godimento, superficie o ISAC è presente in quel
rilascio: la presenza geografica delle righe non colma i due indicatori.
Gli originali e le osservazioni precedenti restano invariati; nessuna acquisizione
duplicata o contatto esterno. Il nuovo comando è un audit, non un normalizzatore.
