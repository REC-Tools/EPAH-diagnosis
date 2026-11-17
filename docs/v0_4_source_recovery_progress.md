# v0.4 — recupero delle fonti ed esecuzione territoriale

Aggiornamento operativo del 17 novembre 2026, sul codice che include la PR #177.
Destinatari: manutentore, tecnico e revisore scientifico. Questo resoconto
aggiorna il [piano di completamento](v0_4_delivery_plan.md) e la
[readiness](v0_4_territorial_release_readiness.md).

**Esito: pacchetto reale di revisione con 13 serie disponibili su 16.**
La v0.4 completa non è ancora conseguita. Stato invariato:
`technical_draft_do_not_publish`; nessuna promozione canonica, approvazione
scientifica, release software o autorizzazione alla diffusione.

Originali, ricevute, log e prodotti nuovi sono conservati separatamente
nell'archivio locale della sessione. Non aggiungerli a Git. I numeri sotto
descrivono questa esecuzione locale e non sono attestazioni della CI.

## H47: recuperato il lavoro già eseguito

- Scaricato lo ZIP POSAS dall'endpoint ufficiale ISTAT. SHA-256 uguale alla
  baseline storica:
  `910639e5f7b1bb8256637eee824655ba76fb8459670c9559fea1ac0922667eac`.
- Recuperato l'artefatto della [run GitHub del 12 novembre
  2026](https://github.com/REC-Tools/EPAH-diagnosis/actions/runs/43211200796).
  Conteneva già una ricevuta schema 2.0: non era un'attività mai svolta.
- Rigiocato l'audit aggiornato sull'originale recuperato e sugli esatti file
  della run: il risultato coincide con la ricevuta storica schema 2.0.
- Preparato separatamente anche un archivio schema 2.0 legato all'anteprima
  locale storica, mantenendone i byte. Il gate d'ingresso dell'atlante passa
  per 27/27 Comuni. Nessuna vecchia ricevuta è stata sovrascritta.

Il blocco tecnico H47 di disponibilità/ricevuta è superato in questa sessione.
Restano la revisione umana e le limitazioni documentate del proxy 0–11 anni.

## Abitazioni 2023: originale e anteprima recuperati

Fonte: [ISTAT, dati per sezioni di censimento](https://www.istat.it/notizia/dati-per-sezioni-di-censimento/),
archivio ufficiale `Dati_regionali_2023.zip`. Conservato l'archivio completo
(261.295.722 byte), verificati i CRC e la corrispondenza dei membri estratti
con l'archivio integrale.

Il file Piemonte e il tracciato ufficiale consentono la seguente mappatura:

| Campo originale | Significato nel tracciato | Gruppo previsto dal builder |
| --- | --- | --- |
| A2 | Abitazioni occupate da almeno una persona residente | `occupied_by_residents` |
| A3 | Abitazioni vuote e abitazioni occupate solo da persone non residenti | `not_occupied_by_residents` |
| A8 | Abitazioni totali | `total` |

Selezionate per codice ISTAT 978 sezioni dei 27 Comuni; verificata l'identità
`A2 + A3 = A8` in ogni sezione, senza imputare conteggi mancanti. Prodotte 81
righe normalizzate e 27 anteprime con il builder esistente. I nomi normalizzati
derivano dal registro canonico, tramite codice; le grafie della fonte sono
conservate nella QA, comprese le anomalie di codifica.

`source_mapping_verified` e `scientific_approval` restano falsi. Occorre la
revisione del mapping e della compatibilità territoriale fra le basi censuarie
e i 27 Comuni. La misura resta “abitazioni non occupate da residenti”, senza
inferenze su case inutilizzate, seconde case o povertà energetica.

## H03/H04: gli originali esistono; il blocco è nel contratto della fonte

Dalla [documentazione ufficiale ARPA NWIOI](https://www.arpa.piemonte.it/scheda-informativa/dataset-griglia-nwioi)
sono stati recuperati Tmin, Tmax, maschera e orografia. I nomi dei due ultimi
file sono visibili anche nella figura della documentazione:
`mask_netcdf.nc` e `orografia_netcdf.nc`. Gli endpoint verificati sono nella
stessa directory ufficiale `https://www.arpa.piemonte.it/static/data/`.

I file Tmin/Tmax coprono il 2025 completo. L'esecuzione dell'estrattore esistente
si interrompe con `Temperature and mask latitude grids are not aligned`:

| Controllo sui file acquisiti | Osservazione |
| --- | --- |
| Dimensioni spaziali | 20 latitudini × 24 longitudini per temperature e maschera |
| Prima latitudine temperatura / maschera | 44,063 / 44,0625 |
| Prima longitudine temperatura / maschera | 6,563 / 6,5625 |
| Differenza massima per ciascun asse | Circa 0,0005° |
| Tolleranza corrente del controllo | 0,00000001°, senza tolleranza relativa |
| Attributo `units` di Tmin/Tmax | Assente; presenti soltanto codici GRIB e numero di tabella |

Non sono state modificate coordinate, soglie, unità, maschera o formule.
Non è stata prodotta un'anteprima H03/H04 valida. La sola disponibilità degli
originali non chiude il replay e il loro aggiornamento giornaliero non dimostra
la comparabilità con eventuali vecchie elaborazioni.

**Decisioni tecniche da documentare prima di continuare:**

1. Conferma dalla fonte che i due assi descrivano le stesse celle e spiegazione
   della precisione/arrotondamento dichiarata. Eventuale normalizzazione va
   proposta esplicitamente, mantenendo intatti gli originali e registrando
   trasformazione, tolleranza e hash; nessun riallineamento automatico.
2. Attestazione autorevole dell'unità delle temperature degli esatti file;
   non dedurla soltanto dai valori o attribuirla per supposizione.
3. Dopo l'eventuale adeguamento revisionato del contratto: estrazione 27×365,
   HDD/CDD dagli stessi input, replay indipendente e revisione di celle,
   fallback e rappresentatività altimetrica.

## H05: verificata un'ulteriore fonte, ancora insufficiente

Esaminati i metadati ufficiali del dataset regionale
[`Sicee_od_sicee_ape_destuso_classe_9919`](https://api.smartdatanet.it/metadataapi/api/v02/detail/Sicee_od_sicee_ape_destuso_classe_9919),
segnalato dal catalogo pubblico come ripartizione per destinazione d'uso e
classe. Lo schema pubblicato non contiene un campo comunale: non fornisce
il necessario incrocio Comune × residenzialità × classe.

I conteggi comunali di tutti gli usi già presenti e i conteggi regionali per
destinazione non determinano le celle mancanti dell'incrocio. Non sono stati
combinati per stimarle. Non risultano dimostrati validità, deduplicazione e
periodo del sottoinsieme richiesto da H05.

Il [portale pubblico SIAPE](https://siape.enea.it/filtro-dati) espone filtri per
Comune e destinazione, ma la singola interrogazione diretta di verifica ha
restituito HTTP 401. Non sono state effettuate autenticazioni, tentativi di
aggiramento o richieste di contatto. L'accessibilità dell'export tramite un
flusso autorizzato resta da verificare.

Materiale da ottenere: export autorizzato per i 27 Comuni con classi A4–G e
totale, filtro residenziale valido, periodo e regole di deduplicazione, insieme
al dizionario e alla ricevuta del filtro. L'assenza di fonte resta esplicita.

## Pacchetto territoriale di revisione generato

Usati il pilota verificato, H47 aggiornato, H50/H46 già riprodotti e la nuova
anteprima abitazioni. Atlante, fascicolo e portale derivano dalla stessa catena;
gli stessi input H47/H50/H46 sono passati anche al fascicolo.

| Prova locale | Esito e limite |
| --- | --- |
| Disponibilità | 13 serie disponibili, H03/H04/H05 assenti; 432 righe di slot, comprese 81 righe `not_acquired` |
| Audit `--pack --atlas` | Superato sul fascicolo reale di revisione |
| Audit `--hub` | Superato; hash, PDF/CSV e schede coerenti; nessuna approvazione scientifica |
| Prodotti | 27 schede da due pagine, volume 54 pagine, fascicolo 17 pagine, sintesi due pagine, HTML/CSV e grafici |
| Browser | 390/768/1280 px: 16 slot controllati, ricerca/tastiera, corrispondenza tabelle/snapshot e link; nessuna richiesta esterna |
| Apertura da disco | Caricato il passaggio portale→atlante; non è una prova completa su un secondo computer |
| PDF | Renderizzati volume, fascicolo e sintesi; ispezione d'insieme e campioni leggibili; revisione umana completa/stampa ancora necessarie |

La presenza di 432 righe non certifica la completezza dei dati; 81 righe
rimangono prive di osservazione. Il pacchetto è un risultato concreto per
revisione, non la consegna della v0.4 completa.

## Ambiente e controlli software dell'esecuzione iniziale (storico)

La manutenzione successiva introduce una [pubblicazione locale condivisa e
compatibile con Windows](v0_4_architecture.md), correggendo il difetto delle
directory descritto sotto. I controlli delle modalità Git sono ora indipendenti
dal filesystem; i due test che richiedono symlink reali rilevano la capacità
dell'host. Eseguire la suite corrente seguendo la
[guida sviluppatore](v0_4_developer_guide.md). I numeri sotto sono conservati
come esito della precedente esecuzione, non come stato del codice aggiornato.

Creato un ambiente separato con le dipendenze del `uv.lock` revisionato,
senza sostituire gli ambienti storici. La prima esecuzione della suite aveva
anche problemi di configurazione del runner, corretti nella ripetizione.
Il secondo run completo locked termina con **970 passed e 10 failed**:

- tre errori di creazione di symlink senza privilegio Windows;
- un controllo dei bit eseguibili che non si comporta come su POSIX;
- sei errori nella pubblicazione di anteprime sperimentali, perché
  `os.replace` non sostituisce la directory riservata su Windows.

Non è un PASS globale. I dieci casi restano aperti e non sono stati esclusi,
marcati come approvati o corretti modificando dati/metodi. Il percorso reale
atlante→fascicolo→portale e i due audit sopra sono invece riusciti.

## Prossime attività circoscritte

1. Sottoporre al revisore i quesiti clima sopra e il mapping abitazioni; iniziare
   o completare la revisione H47/H50/H46 dagli originali ora disponibili.
2. Ottenere l'export H05 attraverso una fonte e un accesso autorizzati.
3. Proporre separatamente la compatibilità Windows della pubblicazione degli
   output e dei controlli di piattaforma, senza indebolire le protezioni.
4. Solo con input e decisioni pertinenti disponibili, generare una nuova
   catena completa con 16 serie e ripetere audit, browser e revisione umana.

Nessun originale, output preesistente, ricevuta storica, matrice canonica,
definizione, workflow o versione di release è stato modificato da questa
esecuzione. La diffusione richiede una decisione separata.
