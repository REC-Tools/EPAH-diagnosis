# Decisioni di fonte e metodo da chiudere per la v0.4

Destinatari: manutentore e revisore scientifico; eventuale referente del
detentore della fonte. Questo dossier rende concrete le attività circoscritte
del [piano](v0_4_delivery_plan.md). Nessuna decisione è approvata dal documento.
Non sono state inviate comunicazioni a terzi o modificati metodi e dati.

Le evidenze osservate sono nel [resoconto del recupero](v0_4_source_recovery_progress.md).
L'architettura degli output può essere consolidata indipendentemente dalle
decisioni sotto; la disponibilità delle 16 serie complete dipende da esse.

## D1 — Griglia dei NetCDF NWIOI

**Osservazione:** temperature e maschera hanno 20×24 celle, ma le prime
coordinate differiscono: latitudine 44,063 contro 44,0625 e longitudine
6,563 contro 6,5625; differenza massima circa 0,0005° per asse. Il controllo
esistente rifiuta l'allineamento. Gli originali sono conservati con SHA-256.

**Quesito alla fonte:** gli assi rappresentano gli stessi centri di cella con
una diversa precisione dichiarata? Esiste una maschera ufficiale della stessa
versione dei file di temperatura, oppure una corrispondenza documentata?

**Evidenza per decidere:** documentazione o conferma del detentore riferita
agli esatti file/versioni. Se occorre una normalizzazione, descriverla in una
proposta separata con tolleranza motivata, casi di rifiuto e hash dei derivati.
Nessuna correzione di coordinate o rilassamento della soglia è autorizzato qui.

**Uscita:** corrispondenza geografica riproducibile e decisione del revisore;
solo dopo, estrazione e replay HDD/CDD dagli stessi input e celle.

## D2 — Unità di Tmin/Tmax

**Osservazione:** manca l'attributo `units`; compaiono codici GRIB e numero
di tabella. La distribuzione dei valori, da sola, non attesta l'unità.

**Quesito alla fonte:** quale unità e quali eventuali fattori di scala/offset
si applicano ai due file acquisiti? Quale documento lo certifica per quella
versione della distribuzione NetCDF?

**Evidenza per decidere:** metadati ufficiali o conferma documentata. Un eventuale
adattatore deve conservare il file originale e registrare la trasformazione;
il contratto non deve indovinare Celsius o Kelvin.

**Uscita:** unità attestata, lettura riproducibile e controllo indipendente dei
totali annuali, distinto dalla rappresentatività altimetrica dei Comuni.

## D3 — Export H05 residenziale comunale

**Osservazione:** il dataset comunale presente copre tutti gli usi; il dataset
regionale per destinazione/classe esaminato non ha una dimensione comunale.
La verifica diretta del servizio SIAPE ha restituito HTTP 401. Nessuno di
questi elementi dimostra il sottoinsieme residenziale valido e deduplicato.

**Richiesta da sottoporre al detentore tramite un accesso autorizzato:**

- 27 codici ISTAT, classi A4/A3/A2/A1/B/C/D/E/F/G e totale;
- definizione della residenzialità e delle esclusioni;
- validità degli attestati e trattamento di annullati, sostituiti e duplicati;
- data di riferimento, intervallo delle emissioni e snapshot della banca dati;
- dizionario dei campi, filtri applicati, licenza e ricevuta dell'estrazione.

Sono sufficienti aggregati anonimi verificabili; non occorre includere dati
personali nel pacchetto. Non stimare l'incrocio da due distribuzioni marginali.

**Uscita:** originale autorizzato, normalizzato 27×11, riconciliazione delle
classi, replay e revisione dei filtri. Non equivale a quota dello stock abitativo.

## D4 — Mapping delle abitazioni 2023

**Proposta già eseguita come anteprima tecnica:** A2→occupate da residenti,
A3→non occupate da residenti, A8→totale, secondo il tracciato ISTAT recuperato.
978 sezioni selezionate per codice, identità A2+A3=A8 verificata per sezione;
nessuna imputazione di conteggi mancanti.

**Quesito al revisore:** confermare universo, data 31 dicembre 2023, trattamento
delle sezioni e compatibilità dei codici/geografia con il registro dei 27 Comuni.
Verificare indipendentemente l'aggregazione e le anomalie di codifica dei nomi.

**Uscita:** decisione riferita a originale, dizionario, normalizzato e anteprima
esatti. Non interpretare la categoria come case vuote o immobili disponibili.

## Registrazione delle decisioni

Per D1–D4 registrare responsabile, data, artefatti e SHA-256, evidenza, decisione,
limiti e ambito approvato in una ricevuta nuova dell'archivio autorizzato.
Le precedenti ricevute restano immutate. H47/H50/H46 richiedono analogamente
revisione delle fonti/metodi già riprodotti; i PASS tecnici non la sostituiscono.
