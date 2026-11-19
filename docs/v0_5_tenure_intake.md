# Affitto: acquisizioni limitate e verifica degli originali

Per il tecnico che prepara la diagnosi v0.5 dei 27 Comuni. Questo percorso
estende il [pilota ISTAT e l'inventario 2023](v0_5_istat_section_review.md):
acquisisce originali e prepara controlli della fonte, senza produrre percentuali
di affitto o osservazioni diagnostiche approvate. Stato invariato:
`technical_draft_do_not_publish`.

## Un piano e una nuova esecuzione

Servono il metadato SDMX del flusso `DF_DCSS_HUDW_1_COM`, l'originale XML del
pilota già acquisito e il registro comunale esistente. I percorsi sotto sono
esempi: usare le copie locali senza riscaricarle o rinominarle per adattarle
all'esempio. Nessuna credenziale è richiesta.

```powershell
uv run --locked epah methodology tenure-acquire --metadata work/input/tenure-metadata.xml --seed work/input/alpette-original.xml --seed-code 001007 --registry data/municipalities.csv --out-dir work/tenure-run-01 --plan-only
uv run --locked epah methodology tenure-acquire --metadata work/input/tenure-metadata.xml --seed work/input/alpette-original.xml --seed-code 001007 --registry data/municipalities.csv --out-dir work/tenure-run-01
```

`--plan-only` legge e verifica gli input, senza file o rete: 26 richieste
pianificate e un pilota riusato. Il piano non acquisisce i dati. L'esecuzione
richiede una destinazione nuova e riusa il lettore del registro già esistente.
Il metadato deve confermare flusso, DSD, ordine delle dimensioni, codelist e
nota dell'universo del totale. Il pilota deve corrispondere al codice indicato.

La selezione è annuale, per un codice alla volta, indicatore `NPHH_AV`, tutte
le categorie di godimento e gli altri filtri verificati insieme nel pilota.
`lastNObservations=1` limita all'ultima osservazione per serie. Non è una serie
storica completa e non garantisce che tutte le categorie abbiano lo stesso
anno: il controllo segnala eventuali divergenze. L'anno obiettivo resta 2025;
il periodo ricevuto non viene riscritto.

## Rispetto del servizio e stati di errore

Le richieste sono sequenziali, con almeno 16 secondi di attesa fra la fine di
una richiesta e l'inizio della successiva. Il timeout è 30 secondi e non ci
sono retry automatici. Non eseguire più acquisizioni contemporaneamente:
il [limite ISTAT di cinque query al minuto](https://www.istat.it/classificazioni-e-strumenti/web-services-sdmx/)
si applica per IP, non per cartella o processo.

L'esecuzione si ferma su HTTP 403/429, su struttura/identità inattese di una
risposta 200 o dopo tre richieste consecutive fallite. Gli altri codici restano
`not_requested`; un errore conserva ricevuta e corpo, se ricevuto. Un timeout
senza risposta non genera un XML fittizio. Un'interruzione gestita, come Ctrl+C, conserva
`phase: interrupted` e le evidenze già acquisite. Nessuna directory precedente
viene rimossa per riprovare. Per una ripresa selettiva usare --reuse-run in una destinazione nuova, come descritto sotto; non riscaricare gli originali riusciti.

L'uscita è 2 quando non tutti i 27 snapshot sono stati acquisiti/riusati e
ispezionati. Un'uscita 0 attesta solo questo completamento tecnico: eventuali
questioni sui dati restano in `review_issues`, senza approvazione automatica.

## Riprendere soltanto i codici mancanti

Aggiungere `--reuse-run work/tenure-run-01` e scegliere, per esempio,
`--out-dir work/tenure-run-02`, mantenendo gli altri argomenti. Usare prima
`--plan-only`: se il primo run ha 25 snapshot disponibili, il nuovo piano deve
indicare due richieste e 25 riusi. La ripresa è un comando esplicito, non un
retry automatico. Non avviarla mentre il primo run è ancora in esecuzione.

Il riuso richiede una fase terminale, gli stessi hash di metadati/registro e
le esatte 27 identità. Ogni originale riuscito viene controllato contro il
checksum della ricevuta e nuovamente ispezionato; questioni aperte non sono
cancellate dal riuso. Una ricevuta attiva, un originale alterato o un diverso
registro bloccano il piano prima della rete. Il nuovo run conserva una copia
della ricevuta precedente in inputs/reused-run.json, con hash; non modifica
il run precedente. Se è già completo, il riuso richiede zero nuove query.
## Cosa conservare

```text
tenure-run-01/
  inputs/       copie esatte di metadati e registro
  raw/          risposte originali per codice, incluso il pilota riusato
  receipts/     una ricevuta per richiesta effettivamente eseguita
  reviews/      controlli della fonte, separati dagli originali
  run.json      stato, hash, richieste, errori e codici non richiesti
  coverage.json copertura tecnica conclusiva, distinta dagli indicatori
```

Solo `run.json` evolve durante l'esecuzione, con sostituzione atomica della
ricevuta del nuovo run. Gli altri file sono creati esclusivamente e non
sovrascritti. Un run interrotto o fallito conserva gli originali già scritti
anche se non arriva al riepilogo finale. Un arresto forzato del processo può lasciare la fase running: non equivale a un completamento e richiede ispezione delle ricevute e degli hash. Le copie degli input non costituiscono
nuove acquisizioni di rete. Non caricare la cartella in Git come risultato
territoriale approvato.

`coverage.json` distingue snapshot ispezionati, codici con osservazioni,
codici con quattro categorie e un solo periodo, questioni da revisionare,
richieste fallite e codici non richiesti. I conteggi riguardano gli artefatti
ricevuti: non sono valori comunali dell'indicatore.

## Ripetere il controllo senza rete

```powershell
uv run --locked epah methodology tenure-review --xml work/tenure-run-01/raw/001029.xml --metadata work/tenure-run-01/inputs/metadata.xml --istat-code 001029 --json-out work/tenure-replay-001029.json
```

Il report deve essere nuovo e il genitore esistente. L'audit rilegge originale
e metadati senza usare come prova il report precedente. Rifiuta flussi, codici,
filtri, serie duplicate e campi di osservazione ambigui. Conserva i valori
numerici come stringhe originali e note/flag nei tre ambiti SDMX (dataset,
serie, osservazione). Non converte i conteggi decimali in interi.

Categorie mancanti, periodi discordanti, valori mancanti/non finiti/negativi,
totale non positivo, nota del denominatore assente e flag della fonte rimangono
questioni esplicite. La differenza esatta fra totale e somma delle tre categorie
è un controllo aritmetico con Decimal, senza tolleranza o aggiustamento:
anche un piccolo residuo richiede interpretazione, non una correzione dei dati.
Nessun rapporto o peso temporale è calcolato.

## Decisioni prima di un indicatore locale

La nota primaria `TIT_POSSESSO__ALL_N1` esclude le famiglie senza tetto dal
totale della tavola: quel denominatore non si sostituisce con `PF1` 2023 o con
un totale generale di famiglie. Occorre revisionare universo, periodo,
significato dei conteggi decimali, flag, eventuali categorie mancanti e residui
prima della normalizzazione. Mancante non è zero; il totale non positivo non
autorizza un rapporto nullo. La verifica del software non approva queste scelte.

I contratti V05-19/V05-20, gli originali v0.4 e gli stati canonici sono invariati.
ISAC, ERP, H03/H04, H05 e UTCI restano separati. Nessun ente o stakeholder viene
contattato: sono consultazioni del servizio pubblico di diffusione dati.

## Esito locale del 19 novembre 2026

Acquisiti gli originali dei 27 Comuni: quattro categorie per codice (`ALL`,
`OWN`, `RENT`, `OTH_OR`), 108 valori della fonte, tutti riferiti al **2021**.
Il primo run ha conservato 24 nuove risposte riuscite più il pilota e due
timeout (Noasca 001165, Prascorsano 001206). Una ripresa esplicita ha richiesto
solo quei due codici, riusando 25 snapshot verificati; entrambe le richieste
sono riuscite. Nessuna richiesta ripetuta per gli altri 25 Comuni.

La verifica offline sui 27 XML ha riprodotto esattamente i report salvati e
controllato gli hash di metadati, pilota, registro e originali del primo run.
Il minimo intervallo osservato nella ripresa è 16,009561 secondi. Le ricevute
del primo run, compresi i timeout, sono rimaste inalterate. Non sono state
osservate categorie mancanti, anni discordanti, valori mancanti/non finiti/
negativi, totali non positivi o flag OBS_STATUS. Questa constatazione riguarda
solo gli snapshot acquisiti, non una garanzia sulla serie storica.

In sei risposte la differenza fra ALL e somma di OWN/RENT/OTH_OR non è zero:

| Codice ISTAT | Comune | Differenza esatta nei valori ricevuti |
| --- | --- | --- |
| 001091 | Colleretto Castelnuovo | 0,000001 |
| 001107 | Forno Canavese | 0,000001 |
| 001121 | Ingria | -0,000001 |
| 001212 | Ribordone | -0,000001 |
| 001238 | San Colombano Belmonte | -0,000001 |
| 001288 | Valprato Soana | 0,000001 |

Sono evidenze aritmetiche della fonte, non tassi o risultati territoriali
approvati. Nessun residuo è stato azzerato o redistribuito.

Il dossier da revisionare prima del calcolo è ora concreto:

| Decisione richiesta al revisore | Evidenza da usare |
| --- | --- |
| Pertinenza dell'universo della tavola, che esclude famiglie senza tetto | Nota TIT_POSSESSO__ALL_N1 e attributi ALL dei 27 originali; non sostituire il denominatore |
| Uso del contesto 2021 rispetto all'obiettivo 2025 | TIME_PERIOD delle 108 osservazioni, quattro anni di scarto espliciti; nessuna rietichettatura o ponderazione |
| Interpretazione di conteggi decimali e residui | Originali, definizione NPHH_AV, dizionario/metodologia ISTAT e i sei report QA; nessuna tolleranza approvata |
| Contratto locale e trattamento delle future lacune | Catalogo di proposta e report con casi sintetici di categorie/valori/periodi mancanti; nessuna promozione automatica |

I cataloghi conservano gli snapshot originari delle proposte, non costituiscono
il registro operativo aggiornato delle acquisizioni. La disponibilità attuale
è documentata da run.json, coverage.json e dagli originali con hash. Questa
acquisizione non modifica quelle schede né aggiunge serie alla diagnosi.
