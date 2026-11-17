# Piano di completamento della v0.4 territoriale

Aggiornamento: 17 novembre 2026, dopo la riconciliazione degli archivi locali
del manutentore con la PR #177. Destinatari: manutentore, tecnico incaricato
della preparazione e revisore scientifico.

**Obiettivo:** consegnare i prodotti territoriali dei 27 Comuni, con tutte le
16 serie previste, fonti reali e decisioni scientifiche tracciabili. Il codice
e i prodotti restano `technical_draft_do_not_publish`; il software stabile
rimane v0.3.0 fino a una release separatamente revisionata.

Questo piano distingue attività già svolte, riproducibilità da completare e
nuove acquisizioni eventualmente necessarie. Un file non ritrovato negli
archivi esaminati non dimostra che il lavoro non sia mai stato eseguito.
Il [controllo di readiness](v0_4_territorial_release_readiness.md) conserva
il contesto, i limiti e il resoconto storico della PR #177.

## Avanzamento dell'esecuzione — 17 novembre 2026

Il [resoconto operativo del recupero](v0_4_source_recovery_progress.md)
aggiorna lo stato iniziale di questo piano: H47 è ora disponibile con originale
e ricevuta schema 2.0, compresa la run storica del 12 novembre; abitazioni 2023
ha una nuova anteprima 27/27. È stato generato e collaudato un pacchetto reale
di revisione con **13 serie disponibili su 16**, mantenendo H03/H04/H05 assenti.

Per il clima sono stati acquisiti gli originali: il blocco ora riguarda
allineamento delle coordinate e unità non dichiarate nei NetCDF, non la mera
assenza dei file. Per H05 le fonti esaminate non dimostrano l'incrocio comunale
residenziale valido. I controlli automatici dei prodotti passano; la suite
software locale resta a 970 successi e 10 errori Windows. Revisioni e diffusione
rimangono separate. I checkbox sotto sono criteri del piano, non approvazioni;
la tabella iniziale è conservata come punto di partenza, non come stato corrente.

## Punto di partenza da conservare

Gli esiti seguenti sono quelli della ricognizione locale del manutentore,
non attestazioni scientifiche canoniche né risultati certificati dalla CI.
Le evidenze della sessione rimangono nell'archivio locale autorizzato;
non allegare a Git originali, percorsi personali o dataset privati.

| Gruppo | Lavoro già presente | Cosa rimane |
| --- | --- | --- |
| Pilota 27×9 | Bundle, ZIP, tre CSV/QA di accessibilità e campioni recuperati; controllo di struttura e checksum positivo; staging della matrice uguale alla matrice storica; 9/9 percorsi ricontrollati nell'originale ISTAT; 27 geometrie corrispondenti | Riutilizzare lo snapshot verificato. Ricostruirlo soltanto se cambiano input, codice pertinente o criteri di accettazione |
| H47 | Anteprima 27/27 e ricevuta storica di riproduzione; serie già inclusa nell'atlante v0.3 locale | Originale POSAS non ritrovato; ricevuta precedente allo schema 2.0; riconciliare le due copie della ricevuta della fonte |
| H50 | Originale ISTAT, metadati, normalizzazione e anteprima presenti; audit indipendente rieseguito con successo, 27/27 | Revisione umana del mapping, universo e denominatore; conservare gli esatti input verificati |
| H46 | Originale ISTAT, metadati, normalizzazione e anteprima presenti; audit indipendente rieseguito con successo, 27/27 | Revisione umana del mapping e denominatore; mantenere i conteggi stimati frazionari |
| H03/H04 | Codice di estrazione, preparazione e replay disponibile | Originali e anteprime non ritrovati nelle aree esaminate; cercare esecuzioni precedenti prima di acquisire nuovamente |
| H05 | Fonte aggregata APE di tutti gli usi e relativa QA presenti | Non dimostrano il sottoinsieme residenziale valido richiesto da H05 |
| ADD-HOUSING-01 | Contratto di normalizzazione e builder disponibili | Fonte ISTAT 2023, dizionario, normalizzazione e anteprima non ritrovati |
| Prodotti v0.4 | Catalogo editoriale, grafici, mappe, accessibilità, ledger e audit implementati; #177 integrata | Esecuzione e revisione sul pacchetto territoriale reale completo |

Le 81 righe di accessibilità ancora vuote/non validate nella matrice canonica
sono distinte dai valori accettati per il pilota. Non trasferire automaticamente
approvazioni o stati dal pilota al canonico.

## Attività e criteri di chiusura

I ruoli indicano responsabilità da assegnare, non persone già incaricate.
Ogni chiusura richiede riferimento agli artefatti esatti, SHA-256, data,
responsabile e ambito del controllo; i checkbox restano aperti fino a ricevuta.

### R1 — Riconciliare l'archivio, prima di ripetere acquisizioni

Responsabile: manutentore con supporto tecnico.

- [ ] Cercare negli archivi autorizzati, nelle consegne delle chat e nelle
  esecuzioni precedenti gli originali mancanti e le relative ricevute.
- [ ] Registrare separatamente: lavoro storico documentato; file disponibile;
  replay eseguibile oggi; revisione scientifica; autorizzazione alla diffusione.
- [ ] Per ciascuna lacuna stabilire se basta recuperare una copia, serve
  aggiornare una ricevuta oppure occorre davvero una nuova acquisizione.

Uscita: inventario privato con file, origine, licenza, periodo, hash e legami
alle elaborazioni. Non sovrascrivere copie discordanti per uniformarne gli hash.
Per H47 le copie locali di `source_observation.json` differiscono per timestamp
e codifica di alcuni caratteri: conservarle e ricostruirne la provenienza.

### R2 — Rendere H47 compatibile con il gate attuale

Responsabile: tecnico; revisore per vintage, fonte e limiti del proxy.
Dipendenza: R1 per H47.

- [ ] Recuperare `POSAS_2026_it_Comuni.zip` della lavorazione storica.
  La baseline ZIP documentata è
  `910639e5f7b1bb8256637eee824655ba76fb8459670c9559fea1ac0922667eac`.
- [ ] Se la copia recuperata coincide, eseguire l'audit indipendente aggiornato
  sugli artefatti della stessa lavorazione, in una destinazione nuova.
- [ ] Se la fonte corrente differisce, documentare il nuovo vintage prima di
  rigenerare anteprima e QA; non sostituire automaticamente l'hash atteso.
- [ ] Preparare un nuovo archivio di revisione compatibile con `--h47-zip`,
  contenente ricevuta schema 2.0 e hash degli esatti file consumati.

Uscita: 27/27, universo 0–11 e denominatori riprodotti dall'originale;
ricevuta schema 2.0 verificabile. La ricevuta storica resta conservata.
Procedura: [audit H47](v0_3_h47_source_reproduction_audit.md).

### R3 — Chiudere insieme H03 e H04

Responsabile: tecnico per la riproduzione; revisore per metodo e territorio.
Dipendenza: R1 per le fonti climatiche.

- [ ] Recuperare, o acquisire se il recupero non riesce, Tmin/Tmax NWIOI,
  maschera regionale e documentazione delle coordinate/unità; conservare
  anche l'orografia utile alla valutazione altimetrica.
- [ ] Estrarre il 2025 con i confini verificati e documentare celle condivise,
  fallback geografici e rappresentatività altimetrica.
- [ ] Produrre HDD e CDD dallo stesso CSV giornaliero e dagli stessi input;
  eseguire il replay indipendente delle formule.

Uscita tecnica: 27×365 giornate complete, QA dell'estrazione e hash coerenti.
Uscita scientifica separata: decisione sulla selezione delle celle e sui limiti
territoriali. I GG normativi del pilota restano distinti dagli HDD annuali.
Procedure: [estrazione NWIOI](v0_3_h03_nwioi_netcdf_extraction.md) e
[replay delle fonti](v0_4_source_validation.md).

### R4 — Dimostrare il sottoinsieme residenziale H05

Responsabile: detentore della fonte e tecnico; revisore per filtri e universo.
Dipendenza: R1 per APE.

- [ ] Recuperare una fonte che consenta di dimostrare residenzialità, validità,
  periodo e deduplicazione degli attestati.
- [ ] Documentare i filtri e produrre il normalizzato con le 11 categorie
  previste per ciascuno dei 27 Comuni, comprese le classi e il totale.
- [ ] Generare l'anteprima e ripetere il controllo indipendente dei conteggi.

Uscita: classi e totali riconciliati, catena originale→normalizzato→anteprima
tracciabile e revisione indipendente dei filtri. Il dataset APE di tutti gli usi
non sostituisce H05; i certificati non rappresentano l'intero stock abitativo.
Il replay numerico da solo non certifica i filtri: [limiti del controllo](v0_4_source_validation.md).

### R5 — Ricostruire il descrittore delle abitazioni

Responsabile: tecnico e revisore del mapping ISTAT. Dipendenza: R1 per abitazioni.

- [ ] Recuperare originale ISTAT 2023 e dizionario delle categorie/sezioni.
- [ ] Documentare aggregazione ai 27 Comuni e mapping verso occupate da
  residenti, non occupate da residenti e totale al 31 dicembre 2023.
- [ ] Riconciliare i totali e verificare indipendentemente la normalizzazione.

Uscita: 27 anteprime riproducibili con denominatori documentati. Non chiamare
la misura “case vuote” o “seconde case”; non sostituire silenziosamente il 2023
con gli archivi edilizi 2011. Builder: `scripts/prepare_v0_3_housing_candidates.py`.

### R6 — Consolidare le decisioni scientifiche

Responsabile: revisore scientifico; manutentore per il registro delle decisioni.
La revisione di H50/H46 può iniziare subito; le altre dipendono dai rispettivi
originali e replay. Non è necessario ripetere acquisizioni già verificate.

- [ ] Registrare per ciascuna delle 16 serie definizione, fonte, unità, periodo,
  universo, denominatore, geografia, limiti e decisione del revisore.
- [ ] Distinguere integrità dei file, riproduzione tecnica, validazione umana
  e autorizzazione istituzionale; una decisione non implica le altre.
- [ ] Conservare approvazioni storiche con il loro ambito; trattare eventuali
  variazioni di definizione o di stato canonico in una proposta separata.

Uscita: decisioni riferite agli artefatti esatti, con responsabili, date e ambiti.
Il piano non assegna approvazioni e non propone graduatorie o prevalenze.

### R7 — Produrre e collaudare una sola catena territoriale

Responsabile: tecnico e revisore dei prodotti. Dipendenze: input verificabili
di R2–R5 e decisioni pertinenti di R6. Preparare anche un ambiente separato dal
lockfile revisionato: gli ambienti storici possono dipendere da interpreti
non più disponibili. Non confondere librerie di recupero con una suite locked.

- [ ] Eseguire suite locked e controllo documentazione sul codice che include
  #177; registrare commit, ambiente, comandi ed esiti.
- [ ] Generare [atlante](v0_4_visual_atlas.md), [fascicolo](v0_4_review_pack.md)
  e [portale](v0_4_output_hub_step2.md) in cartelle nuove. Usare lo stesso pilota,
  registro e le sette anteprime; conservare gli stessi input H47/H50/H46 anche
  nel fascicolo per mantenere denominatori e ricevute.
- [ ] Verificare 27 Comuni × 16 slot = 432 osservazioni attese, disponibilità
  effettiva delle serie e motivi di eventuali assenze. Il solo conteggio di 432
  righe non prova completezza: gli slot `not_acquired` non chiudono l'obiettivo.
  Se una fonte non permette un valore comunale, serve una decisione esplicita
  sul perimetro; non inventare valori o denominatori.
- [ ] Applicare gli audit `--pack --atlas` e `--hub`, con QA fuori dai prodotti;
  interrompere la catena al primo errore.
- [ ] Ispezionare HTML, CSV, PDF tecnico, sintesi, 27 schede, mappe e ledger;
  verificare mobile, tastiera, zoom 200%, lettore di schermo, stampa A4 al 100%
  e apertura da disco su un secondo computer.

Uscita: pacchetto reale coerente, controlli ripetibili e ricevute della revisione
visiva e scientifica. Il PASS sintetico della PR #177 non sostituisce questo
collaudo. Riferimento: [gate end-to-end](v0_4_end_to_end_qa_step9.md).

### R8 — Deliberare release e diffusione

Responsabile: manutentore e soggetti competenti. Dipendenza: R6 e R7 chiusi.

- [ ] Preparare una proposta separata per versione, lock, metadati e contratto
  di release v0.4; il contratto v0.3 non certifica la v0.4.
- [ ] Registrare hash del pacchetto finale, revisore, data e ambito approvato.
- [ ] Ottenere separatamente l'autorizzazione alla diffusione istituzionale.

Nessun merge, tag o pubblicazione è autorizzato automaticamente dal piano.
La rimozione di `technical_draft_do_not_publish` richiede una decisione esplicita.

## Prima azione e parallelismo utile

Avviare R1 con priorità H47 e archivi climatici, mentre il revisore esamina
H50/H46 già riprodotti. R3, R4 e R5 possono avanzare indipendentemente dopo
la riconciliazione dei rispettivi archivi. L'aggiornamento dell'interfaccia non
è il blocco principale; evitare nuove modifiche grafiche prima del collaudo reale.

Una v0.4 parziale può servire alla revisione tecnica se mostra le assenze,
ma non va presentata come completamento delle 16 serie. Se una fonte è
inaccessibile, documentare l'esito e sottoporre una variazione di perimetro
al manutentore e al revisore, senza cambiare il contratto implicitamente.
