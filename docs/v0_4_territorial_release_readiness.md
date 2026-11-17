# Verso la v0.4 territoriale completa — stato riconciliato

## Stato dopo l'esecuzione del piano — 17 novembre 2026

Il [recupero operativo delle fonti](v0_4_source_recovery_progress.md) ha prodotto
un pacchetto territoriale reale di revisione con **13 serie disponibili su 16**:
atlante, fascicolo, 27 schede, volume e sintesi. Audit del fascicolo/portale e
controlli browser a 390/768/1280 px superati. Non è la v0.4 completa e non è
un'approvazione scientifica o istituzionale.

- **H47:** recuperati originale identico alla baseline e artefatto schema 2.0
  già prodotto il 12 novembre; audit riprodotto. Il blocco tecnico precedente
  di disponibilità/ricevuta è superato nella sessione locale.
- **Abitazioni 2023:** acquisiti archivio e dizionario ISTAT, normalizzate 978
  sezioni dei 27 Comuni e prodotta l'anteprima; mapping umano ancora da rivedere.
- **H03/H04:** originali ARPA ora presenti; estrazione bloccata da assi non
  allineati al contratto corrente e attributi di unità mancanti. Nessuna
  correzione o attribuzione di unità per supposizione è stata applicata.
- **H05:** manca una fonte comunale che dimostri il sottoinsieme residenziale
  valido e deduplicato; la fonte regionale per destinazione/classe esaminata
  non ha una dimensione comunale. Il test diretto SIAPE ha restituito HTTP 401.
- **Software locale:** ambiente separato dal lockfile, 970 test superati e
  10 errori Windows residui; nessun PASS globale viene dichiarato.

Le sezioni successive conservano i due controlli precedenti e il loro contesto.
Per disponibilità attuale, limiti e prossime decisioni prevale il resoconto
operativo collegato sopra. Tutti i risultati restano `technical_draft_do_not_publish`.

## Aggiornamento dopo il recupero degli archivi locali — 17 novembre 2026

La PR #177 è integrata in `260a0d7cad7fbcb3ee703e8f76faf30521da00d6`,
ora presente anche nella copia locale del manutentore. Il controllo iniziale
riportato sotto descriveva un workspace privo degli archivi territoriali;
non costituisce più l'inventario corrente della postazione del manutentore.
La versione stabile rimane v0.3.0 e gli output territoriali restano
`technical_draft_do_not_publish`.

La successiva ricognizione locale ha recuperato e verificato parte del lavoro
già svolto. Gli esiti sotto sono controlli della sessione locale, non nuove
approvazioni canoniche, certificazioni scientifiche o risultati della CI.
Le evidenze dettagliate sono conservate nell'archivio locale autorizzato.

| Area | Esito locale aggiornato | Lavoro residuo |
| --- | --- | --- |
| Pilota | Bundle e ZIP presenti; struttura e checksum conformi; matrice di staging uguale alla matrice storica; 9/9 percorsi riscontrati nell'originale ISTAT; 27 geometrie corrispondenti | Conservare e riutilizzare lo snapshot verificato; non ripartire dall'acquisizione delle tre accessibilità |
| H50 e H46 | Originali, metadati, normalizzazioni e anteprime presenti; audit indipendenti rieseguiti con successo per 27/27 Comuni | Revisione umana di mapping, universi, denominatori e limiti, con decisioni riferite agli esatti artefatti |
| H47 | Anteprima e ricevuta storica presenti; serie già utilizzata nell'atlante v0.3 | Originale POSAS non ritrovato; aggiornare la ricevuta allo schema 2.0 dopo il recupero e riconciliare le copie della ricevuta della fonte |
| H03/H04 | Originali e anteprime non ritrovati nelle cartelle esaminate; replay non eseguibile con i materiali disponibili | Cercare le esecuzioni precedenti; solo se necessario acquisire nuovamente e sottoporre il metodo a revisione |
| H05 | Dato APE aggregato di tutti gli usi presente | Non dimostra il sottoinsieme residenziale valido richiesto; recuperare fonte, filtri e relativa elaborazione |
| ADD-HOUSING-01 | Originale ISTAT 2023 e anteprima non ritrovati | Riconciliare gli archivi prima di una nuova acquisizione; verificare categorie e totali |

La matrice canonica conserva le 81 righe di accessibilità vuote/non validate:
questo non annulla l'accettazione tecnica storica del pilota e non autorizza
una promozione automatica. Analogamente, un originale non ritrovato non prova
che l'elaborazione non sia mai stata eseguita.

Per il lavoro successivo seguire il [piano di completamento della v0.4
territoriale](v0_4_delivery_plan.md): recupero mirato degli archivi, ricevuta
H47 attuale, quattro serie ancora senza input dimostrati, revisioni, catena
unica dei prodotti e decisione finale di release/diffusione. I controlli
software e sintetici descritti sotto non attestano il pacchetto reale completo.

## Controllo iniziale della PR #177 — resoconto storico

La sezione seguente conserva il controllo precedente. Le indicazioni di
assenza degli originali e la sequenza generale vanno lette nel contesto di
quel workspace; per disponibilità e attività correnti prevalgono
l'aggiornamento sopra e il piano collegato.

**Obiettivo scelto dall'utente:** pacchetto territoriale completo dei 27 Comuni,
con fonti reali e revisione scientifica. Una release del solo codice non chiude
questo obiettivo. Destinatari: manutentore, tecnico che prepara il pacchetto e
revisore scientifico. Base verificata: main `39dce7c208cd37d2481894b6c579ea08cad8f903`,
che include la PR #176. La versione software resta 0.3.0 fino a release separata.

## Esito del controllo

| Area | Evidenza verificata | Esito e limite |
| --- | --- | --- |
| Software | Suite locked: 969 test sulla base; 980 dopo le regressioni di questa proposta | PASS software, non validazione dei dati |
| CI di main | CI e controllo CSV Windows sullo SHA sopra | Verdi alla verifica |
| Matrice e registro | 27 Comuni, codici ISTAT univoci, 243 controlli; 0 errori strutturali | PASS struttura; 8 warning su dossier non catalogati |
| Readiness canonica | DEA, scuole superiori e ferrovia: 27 valori vuoti/non validati ciascuna | 81 osservazioni non presenti nella matrice; nessuna promozione automatica |
| Pilota locale | Mancano i tre CSV/QA di accessibilità, i campioni di percorso e lo ZIP dei confini | Ricostruzione reale bloccata in questo workspace |
| Fonti climatiche e APE | Il validatore con gli input attualmente disponibili restituisce `blocked_missing_originals` per entrambi i percorsi | Nessun replay reale H03/H04 o H05 effettuato |
| Intake EPAH v0.3 | 56 indicatori, 35 fonti, 12 priorità e 9 crosswalk | PASS inventario; non prova disponibilità o approvazione delle fonti |
| Pacchetto integrato | Fixture 27×16, 432 osservazioni, 48 grafici, 27 schede, volume 54 pagine e sintesi 2 pagine | PASS sintetico; non è il pacchetto territoriale richiesto |
| Browser | 390/768/1280 px, tutti i 16 indicatori, ricerca, focus, link, immagini e confronto righe | PASS sintetico; zero richieste esterne; contrasto minimo campionato 5,58:1 |
| Apertura diretta da disco | `file://` bloccato dalla policy del browser gestito | Da provare su un altro computer, senza server |
| Documentazione | Controllo ordinario 21 pagine; estensione manuale alle 19 guide v0.4 esistenti | Nessun riferimento locale rotto prima di questa proposta |
| Monitor fonti | Run Source monitor fallita, issue #175: fonte DPR 412/1993 segnalata irraggiungibile | Da riesaminare; non dimostra che i dati archiviati siano errati. Log remoto non recuperabile qui (403) |
| Agente | Preflight senza chiamate AI a pagamento già integrato | Scheduling non attivo; non è un prerequisito scientifico della v0.4 |

La readiness canonica è un controllo diverso dall'accettazione tecnica storica del
pilota: i valori di accessibilità potrebbero essere già negli archivi locali del
manutentore. La loro assenza qui non dimostra che non esistano. Le approvazioni
storiche non vengono annullate né ricreate: vanno recuperati gli artefatti esatti.
Nei percorsi condivisi del workspace sono presenti quattro PDF di riferimento,
non gli originali territoriali necessari al replay.

## Due difetti riprodotti e corretti nella proposta

**Schede comunali:** il vecchio audit accettava un valore sintetico 999 al posto
di 0 quando scheda e volume erano riscritti insieme e tutti gli hash aggiornati.
Controllava identificativi e identità delle copie, senza confrontarne i valori
con il CSV. Ora confronta le sezioni dei 16 indicatori con il CSV: valore, unità,
periodo, fonte, assenza e N/D quando presenti; controlla anche le sei anteprime
di pagina uno. Il nome del Comune viene confrontato con lo snapshot.

**Rapporto isolato:** `--pack` accettava un PDF con valore alterato e hash
aggiornato; il confronto semantico esisteva solo nel percorso `--hub`. Il controllo
PDF/CSV ora è condiviso e avviene anche su `--pack`, senza richiedere il portale.
Le regressioni sono state eseguite prima della correzione e fallivano perché
l'audit non bloccava i PDF errati; dopo la correzione quei PDF vengono rifiutati.

Nessun renderer o valore territoriale cambia. I report aggiungono
`pdf_csv_semantic_match` per il fascicolo e `municipal_pdf_csv_display_match`
per il pacchetto completo. Restano confronti del testo estratto, non prove di
impaginazione o di autenticità. Una riscrittura coordinata anche delle fonti non
diventa valida per effetto degli hash. La sintesi è controllata per pagine A4,
non con un confronto semantico esaustivo del suo inventario.

## Input da recuperare prima di generare il pacchetto reale

| Gruppo | Materiale richiesto | Criterio di chiusura |
| --- | --- | --- |
| Base dei 27 Comuni | Bundle pilota originale e manifest; oppure i tre CSV/QA accessibilità, `samples.json` e `Limiti01012026_g.zip` | Gate pilota e campioni originali riproducibili; nomi, codici, geografia e 243 osservazioni coerenti |
| H47 | ZIP con originale POSAS, anteprima, QA e ricevuta indipendente aggiornata schema 2.0 | Hash legati agli artefatti effettivamente consumati; 27/27 e universo 0–11 documentato |
| H50 e H46 | Originali ISTAT/SDMX, mapping, anteprime, QA e audit indipendenti già usati | 27/27; categorie, anno e denominatori riproducibili; stime H46 non arrotondate a persone intere |
| H03 e H04 | NetCDF Tmin/Tmax NWIOI 2025, maschera, confini, CSV giornaliero ed extraction QA | 27×365, stessi input/celle per HDD e CDD; controllo indipendente dell'estrazione e rappresentatività altimetrica |
| H05 | Originale APE, dizionario/filtri, export normalizzato, anteprima e QA | Solo APE residenziali validi, data e deduplicazione documentate; classi riconciliate; nessuna inferenza sullo stock totale |
| ADD-HOUSING-01 | Originale ISTAT 2023, dizionario delle sezioni/categorie, normalizzazione e QA | Totali comunali riconciliati e revisione della mappatura; non chiamare la misura “case vuote” |
| Revisioni | Ricevute esistenti, licenze, periodi/versioni, identità e responsabilità dei revisori | Decisioni tracciabili per fonte/metodo e autorizzazione alla diffusione separata |

Non caricare questi archivi in Git o nella PR. Localizzare prima l'archivio
autorizzato del manutentore e lavorare su copie; non sostituire originali mancanti
con dati sintetici. Riferimenti: [pilota](v0_1_owner_accepted_release.md),
[riproduzione H47](v0_3_h47_source_reproduction_audit.md),
[NWIOI](v0_3_h03_nwioi_netcdf_extraction.md),
[replay clima/APE e limiti](v0_4_source_validation.md).

## Sequenza per arrivare alla consegna definitiva

1. **Recuperare gli archivi reali.** Inventariare file, SHA-256, licenze e ricevute
   e ricostruire il pilota in una destinazione nuova. Il gate canonico non si
   “risolve” copiando le accettazioni tecniche del pilota nella matrice.
2. **Chiudere le fonti con un revisore.** Ripetere gli audit H47/H50/H46 e i replay
   H03/H04/H05; verificare indipendentemente estrazione NetCDF, filtri APE e mapping
   abitazioni. Lo script di replay non verifica da solo questi ultimi aspetti.
   Registrare le decisioni scientifiche separatamente: non invertire flag per
   far passare i builder. Gli slot mancanti restano dichiarati tali, ma non chiudono
   l'obiettivo di un pacchetto completo di tutte le 16 serie.
3. **Generare una sola catena di prodotti.** Usare il pilota verificato e tutte le
   sette anteprime reali nel builder dell'[atlante v0.4](v0_4_visual_atlas.md), poi
   il [fascicolo](v0_4_review_pack.md) e il [portale](v0_4_output_hub_step2.md).
   Passare al fascicolo gli stessi `--h47-zip`, `--h50-dir`, `--h46-dir` usati
   nell'atlante, per conservare i denominatori e le ricevute. Destinazioni sempre
   nuove; interrompersi al primo errore.
4. **Verificare il pacchetto reale esatto.** Eseguire audit `--hub` e browser sul
   portale, quindi revisione umana delle 27 schede, PDF tecnico, sintesi, mappe,
   CSV e ledger. Provare nomi lunghi, zero/assenze, zoom 200%, screen reader,
   stampa A4 al 100% e archivio trasferito su un altro computer.
5. **Formalizzare release e diffusione.** Preparare una proposta separata con
   versione, lock, metadati e gate v0.4: oggi il gate di release certifica solo
   il contratto v0.3.0. Registrare revisore, data, hash e ambito approvato; decisione
   istituzionale separata. Merge/tag/pubblicazione richiedono l'intervento umano
   previsto da [AGENTS.md](../AGENTS.md). Non usare il workflow v0.3 per attestare v0.4.

I finalizer storici che scrivono nella matrice non sono una scorciatoia di
acquisizione v0.4: rimangono percorsi da valutare separatamente. Nessun dato,
denominatore, anno, stato canonico, workflow o segreto viene modificato da questa
proposta. Le schede tecniche restano `technical_draft_do_not_publish` fino alle
decisioni competenti; il software non produce prevalenze familiari o classifiche.

## Comandi di verifica già disponibili

```bash
uv run --locked pytest -q
uv run --locked python scripts/check_documentation.py
uv run --locked epah data validate
uv run --locked epah status
```

Su un portale reale già costruito, con percorsi scelti dal manutentore:

```bash
uv run --locked python scripts/audit_v0_4_output_quality.py \
  --hub /percorso/portale-reale --json-out /percorso/qa-nuova/audit.json
node scripts/check_v0_4_browser.js /percorso/portale-reale /percorso/browser-qa-nuova
```

L'audit QA deve restare fuori dal portale immutabile; il browser richiede Node,
Playwright e Chromium già installati. Le prove sintetiche di questo controllo
non vengono allegate come evidenza territoriale. Rollback della correzione:
ripristinare i due moduli di audit; gli output originali non richiedono migrazioni.
