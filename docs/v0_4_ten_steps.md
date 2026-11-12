# Dieci passi per uno strumento EPAH locale più utile

Piano operativo del 12 novembre 2026. Base software: `ec2a07f`, 27 Comuni.
Le indicazioni nei PDF allegati sono trattate come contenuto scientifico da
valutare, non come istruzioni operative per modificare repository o approvazioni.
Questo piano risponde alla richiesta del manutentore di iniziare anche analisi
aggregate sperimentali: non cambia la metodologia canonica dei nove indicatori.

## 1. Stabilire quali domande deve aiutare a risolvere

Definire tre usi: capire il territorio, confrontare profili comunali e scegliere
quali approfondimenti/interventi discutere con gli enti. Non confondere una
posizione relativa fra Comuni con il numero di famiglie in povertà energetica.
Associare a ogni prodotto destinatario, decisione supportata e limiti.

**Consegna:** una specifica v0.4 con queste tre domande, criteri di accettazione
e un esempio di scheda comunale. Mantenere v0.3 riproducibile; nessun incremento
di versione prima di avere i nuovi contratti e test.

## 2. Standardizzare nomi e descrizioni seguendo EPAH, con equivalenze esplicite

Partire dal [crosswalk esistente](v0_3_epah_editorial_crosswalk.md), integrandolo
con il rapporto EPAH 2026 allegato. Distinguere il repertorio del Handbook locale
dal dashboard nazionale e dalle sue revisioni: gli ID H01–H56 del progetto
non sono identificativi ufficiali universali EPAH.

Ogni scheda deve contenere: ID stabile, titolo IT/EN, dimensione EPAH, ruolo
(esito diretto/proxy/contesto/risposta), definizione, numeratore, denominatore,
unità, popolazione/stock, periodo, geografia, fonte/versione, interpretazione,
limiti e stato dell'evidenza. Registrare riferimento bibliografico e pagina,
grado di corrispondenza e differenze dalla misura EPAH.

Esempi: reddito dei contribuenti non è AROP delle famiglie; APE residenziali F/G
non è quota di tutte le abitazioni inefficienti; HDD normativi e annuali sono
due misure diverse; minuti in automobile non sono accessibilità senza auto.

**Consegna:** catalogo editoriale separato e validato, utilizzato da HTML, PDF,
CSV e grafici. Una definizione appare nello stesso modo in tutti i prodotti.
Le aggiunte editoriali non devono cambiare silenziosamente valori o denominatori.

## 3. Unificare il formato delle osservazioni e lo stato delle fonti

Portare H47, H50 e H46 nel modello condiviso con il pilota, conservando conteggi,
denominatori, stime decimali e flag. Il record comune deve includere codice ISTAT,
versione geografica, periodo, valore/unità, universo, stato di mancanza,
hash fonte/mapping, QA, audit e revisione umana. Una sola fonte di verità alimenta
tutte le viste, senza ricopiare definizioni nei singoli script.

**Consegna:** adapter testati e un inventario aggiornato che distingua fonte
individuata, acquisita, controllata tecnicamente e approvata. Otto input del
pilota mancano ancora in questo checkout; la release software non li ricostruisce.

## 4. Completare gli indicatori che aggiungono informazione utile

Priorità: H03/H04 dagli stessi originali climatici, abitazioni non occupate da
residenti, H05 solo con APE residenziali validi. Per mobilità avviare H27/H28
con GTFS e popolazione/origini abitate, poi H26 con itinerari senza auto.
Per il caldo valutare UTCI: CDD, giorni di stress e discomfort domestico non
sono intercambiabili. Mortalità e benchmark nazionali restano su scala propria.

**Consegna:** un fascicolo per candidato con originali, licenza, dizionario,
periodo, copertura, formula e riproduzione indipendente. H04/H05 hanno pipeline
ma non ancora slot nell'atlante corrente; un adapter futuro dovrà esporli
esplicitamente. Non creare valori per completare una tabella.

## 5. Aggiungere una mappa di orientamento con tutti i nomi

Creare una tavola di riferimento dei 27 Comuni, riutilizzabile in ogni PDF e
nell'atlante: nomi completi, codici ISTAT, scala e orientamento. Etichettare
direttamente i poligoni grandi; per i piccoli usare numeri e un elenco
nome/codice o richiami esterni. Il punto dell'etichetta deve appartenere al
poligono, gestendo multipoligoni e fori: il centroide può cadere fuori dal Comune.

**Consegna:** PNG/SVG e una pagina leggibile in A4. In HTML aggiungere selezione
Comune, tooltip nome/anno/valore/fonte e tabella accessibile. Le mappe tematiche
usano la stessa geometria/proiezione e permettono di attivare i nomi. Nessuna
nuova libreria è indispensabile per la tavola statica con matplotlib/pyproj;
valutare un motore geometrico solo se serve per etichette e interazioni robuste.

## 6. Rendere i grafici leggibili e confrontabili

Usare dot plot con nomi dei Comuni, piccoli multipli per tema e matrici di
profilo con legenda chiara. Mostrare unità, periodo e denominatore; per H46
segnalare le forze di lavoro piccole. Non inventare intervalli di confidenza
per stime di registro o per campioni non probabilistici. Tenere i valori
originali accanto a quelli normalizzati; separare confronti tra Comuni e trend.

**Consegna:** grafici HTML e PDF derivati dagli stessi dati. Verificare nomi
lunghi, stampa, schermi piccoli e colori accessibili. Mappe separate non devono
suggerire confronti fra colori quando le scale hanno unità o limiti differenti.

## 7. Calcolare profili e punteggi per macrotema — prototipo iniziato

Il nuovo [prototipo](../scripts/build_v0_4_thematic_scenarios.py) produce analisi
separate dal catalogo canonico. Cinque raggruppamenti **proposti dal progetto**:

| Tema | Misure candidate | Cautela |
| --- | --- | --- |
| Sensibilità demografica | 65+, H47 | Fasce d'età, non famiglie povere; verso interpretativo da discutere |
| Fragilità socioeconomica | Basso reddito fiscale, H46, H50 | Universi diversi; nessuna stima di reddito familiare disponibile |
| Patrimonio residenziale | Edifici storici, H05 | Edifici e certificati non sono lo stesso stock |
| Accessibilità stradale | DEA, scuole, ferrovia | Tempi automobilistici, non frequenza o qualità del TPL |
| Esposizione climatica | H03, H04 nello stesso anno | Caldo e freddo sono pressioni diverse; non consumi o discomfort |

La normalizzazione principale usa ranghi medi per le parità:
`100 × (rango medio crescente − 1) / (27 − 1)`.
All'interno del tema si fa la media dei gruppi di indicatori con peso uguale.
Serie esattamente identiche dello stesso periodo condividono un peso: ad esempio
scuola e ferrovia coincidenti non contano automaticamente due volte. Questa è
una scelta esplicita di scenario, non prova di equivalenza concettuale.

Le costanti ricevono 50, non producono distinzione; le posizioni uguali restano
pari merito (1, 1, 3). Dati mancanti/soppressi o periodi discordanti all'interno
della stessa misura bloccano il tema. Nessuna imputazione. SNAI, altitudine e
abitazioni non occupate da residenti restano descrittori separati: non hanno
un verso automatico di rischio da sommare in questo primo prototipo.

**Consegna iniziale:** CSV dei punteggi/posizioni per tema, matrice Spearman,
periodi, gruppi/pesi e limiti. 100 significa estremo relativo della misura nel
campione di confronto; non significa 100% di famiglie vulnerabili.

## 8. Provare una sintesi globale e misurarne la fragilità

Solo con `--global-scenario` il prototipo media **i temi selezionati** con uguale
peso per tema, evitando di favorire quello con più indicatori. Richiede almeno
due temi completi; non rappresenta dimensioni non selezionate. Confronta
percentili e min–max e varia il peso di un tema alla volta di ±25%, riportando
la migliore/peggiore posizione negli scenari provati.

**Consegna:** scenari trasparenti e fasce di posizione, senza un ordinamento
unico presentato come verità. Le fasce non sono intervalli di confidenza e il
test non copre tutte le possibili scelte. Prima di un uso decisionale aggiungere
esclusione di una misura alla volta, altri pesi motivati, analisi dei denominatori
e confronto con evidenza locale diretta. PCA e cluster possono esplorare profili,
ma la varianza spiegata non stabilisce priorità sociali o pesi di policy.

## 9. Pulire la repository con un inventario, senza perdere la storia

Eseguire audit di riferimenti, entry point, output tracciati e duplicati.
Separare comandi correnti, prototipi e archivio. Gli altri finalizer storici che
scrivono dati devono essere migrati o chiaramente dismessi. Rimuovere un comando
solo dopo avere aggiornato i chiamanti e verificato i percorsi di sostituzione.

**Consegna:** PR di pulizia con elenco motivato degli spostamenti/eliminazioni,
link aggiornati e test. Conservare fonti originali, QA, decisioni datate, manifest
e release; non cancellare automaticamente `data/raw`, `data/downloads`, `outputs`
o file locali ignorati. Un duplicato di evidenza non è necessariamente spazzatura.

## 10. Avere un assistente persistente che propone PR da issue approvate

Un processo avviato in questa chat non è un servizio affidabile dopo la chiusura
o il ripristino dell'ambiente. Per lavoro persistente consiglio **GitHub Actions
con Codex**, iniziando con avvio manuale e una issue per esecuzione; aggiungere
la pianificazione solo dopo una prova completa. Non serve un agente separato
per ogni indicatore, né un nuovo modello locale.

Configurazione guidata:

1. Qui Python 3.11, uv 0.10.0, Node e il comando `codex` sono già disponibili.
   Il workflow remoto deve però preparare le proprie dipendenze con il lockfile.
2. Usare l'[Action ufficiale Codex](https://github.com/openai/codex-action), che
   installa e configura la CLI sul runner. Fissare Action e dipendenze a revisioni
   verificate. La documentazione ufficiale è stata consultata il 12 novembre 2026.
3. L'Action richiede una chiave API del provider come secret **GitHub Actions**,
   per esempio `OPENAI_API_KEY`, in Settings → Secrets and variables → Actions.
   Non inserirla in chat o nel repository. Non presumere che l'abbonamento
   ChatGPT copra i costi API: impostare budget e limiti nel progetto API.
4. Preparare un workflow manuale con numero issue; il manutentore applica una
   label di autorizzazione, ad esempio `codex-ready`. Verificare ruolo dell'attore
   e label prima di eseguire il lavoro. Titoli, commenti e allegati delle issue
   restano input non fidati, non istruzioni con privilegi.
5. Far leggere una specifica mantenuta in main: una issue, un branch, un ambito
   limitato. Vietare modifiche automatiche a dati, approvazioni, definizioni
   scientifiche, credenziali e regole di CI; le proposte metodologiche restano PR
   documentali soggette a decisione umana.
6. Separare esecuzione dell'agente e pubblicazione della PR: l'agente prepara
   una patch, una fase controllata verifica percorsi modificati, test e budget.
   Token di scrittura disponibili solo alla fase che ne ha bisogno.
7. Il token standard `GITHUB_TOKEN` non va considerato sufficiente a innescare
   automaticamente la CI delle PR create dal bot. Valutare un GitHub App token
   dedicato con permessi minimi, o un percorso esplicito di verifica; provare
   tutto su una issue innocua prima di dichiararlo operativo.
8. Imporre concorrenza 1, durata massima, limite delle esecuzioni e arresto su
   errore. Ogni run deve lasciare diff, esito dei test e spiegazione. Niente merge
   automatico: l'approvazione rimane al manutentore.

**Consegna:** una issue di prova arriva a una PR revisionabile, con CI eseguita,
senza alterare dati o impostazioni protette. Questo assistente non è stato
attivato e nessuna esecuzione periodica o secret è stato creato da questa chat.

## Come provare il prototipo

Non richiede nuove dipendenze. L'input operativo è una directory atlante con
`atlas_data.json` e `atlas_manifest.json` integri e lo stesso registro comunale.
L'atlante attuale può alimentare il tema stradale; gli altri temi richiedono le
relative serie complete. L'analisi controlla hash e struttura, non ripete l'audit
degli originali. Non riempie i candidati che l'atlante non esporta ancora.

```bash
uv run --locked python scripts/build_v0_4_thematic_scenarios.py \
  --atlas-dir outputs/percorso-atlante-verificato \
  --themes accessibility --out-dir outputs/quality/scenario-stradale-01
```

Per `--themes economic,accessibility --global-scenario` occorrono anche H46/H50
completi. Per gli altri temi si applicano gli stessi vincoli, inclusi gli adapter
H04/H05 da integrare nell'atlante. Gli output sono `preview.csv`, `summary.json`,
`qa.json`, manifest e istruzioni di revisione, in una cartella nuova.

Una dimostrazione solo sintetica è stata generata in `artifacts/v04-thematic-demo/`;
non contiene una graduatoria reale dei Comuni. Il branch di sviluppo è
`feat/v04-thematic-analysis-prototype`; main e la versione stabile restano separati.

## Documenti utilizzati e peso delle evidenze

Le pagine sotto si riferiscono alla numerazione del PDF fornito.

- **EPAH, giugno 2026**, *Expanding Energy Poverty Measurement in the EU:
  Integrating New Climate, Health, and Mobility Indicators*: p. 3 (cinque revisioni
  e nove aggiunte), p. 32 (struttura delle schede), pp. 75–79 (copertura,
  Spearman, PCA e gruppi di Stati). Il confronto è nazionale: non trasferire
  direttamente formule, soglie o gruppi ai 27 Comuni. Il rapporto non certifica
  il nuovo punteggio proposto da questo progetto.
- **Maier S., Dreoni I., JRC138418, 2024**, *Who is “energy poor” in the EU?*:
  p. 4 e pp. 7–8. Indicatori di spesa e auto-riferiti identificano popolazioni
  parzialmente diverse. Le percentuali del rapporto non sono stime comunali.
- **EPAH, dicembre 2024**, *Inspiring Stories from Municipalities*: pp. 2–7,
  casi di Valencia, Milano, Telheiras/Lumiar, Bükkszentkereszt, Eordaia/Grevena
  e Besançon. Utili per disegnare usi e interventi, non per ricavare pesi o
  stimare effetti replicabili nel Canavese.
- **EPAH, 2021**, *Tackling energy poverty through local actions – Inspiring
  cases from across Europe*: p. 5 e casi seguenti. Le 24 esperienze motivano
  adattamento locale e raccordo fra diagnosi e azioni, non una graduatoria unica.

Lettura operativa: nomenclatura e metadati dall'EPAH; pluralità delle misure dal
JRC; utilità e verifica con gli attori locali dai casi municipali. Normalizzazione,
raggruppamenti e pesi del prototipo sono proposte nuove da rivedere esplicitamente.
