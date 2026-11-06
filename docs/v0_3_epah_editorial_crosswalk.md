# Crosswalk editoriale EPAH — nove indicatori canonici e candidati v0.3

Documento di **armonizzazione dei nomi e delle descrizioni**, non migrazione del database: gli `id`, i denominatori, il periodo e i valori di `config/indicators.json` rimangono invariati. Le categorie tematiche seguono **EPAH Handbook 1, tabella 5**, ma le corrispondenze sono spesso **parziali**; una nuova etichetta non rende il dato una misura di povertà energetica.

| ID repository | Etichetta italiana descrittiva da utilizzare nei rapporti v0.3 | Dimensione EPAH | Ruolo | Riferimento / differenza da EPAH |
| --- | --- | --- | --- | --- |
| `population_65_plus` | Quota di popolazione residente di 65 anni e più | Socio-economic | Proxy demografico | H48 interno: la tabella di ricognizione cita «più di 65», mentre la repo misura «65 e più». |
| `income_vulnerability` | Quota di contribuenti con reddito dichiarato fino a 15.000 euro | Socio-economic | Proxy economico | H32 solo parziale; non è povertà familiare o rischio di povertà AROP. |
| `old_building_stock` | Quota di edifici residenziali realizzati prima della soglia documentata | Facilities/Housing | Proxy edilizio storico | H22 correlato ma non identico: quota storica, non età media né classe energetica. |
| `heating_degree_days` | Gradi-giorno normativi per il riscaldamento (DPR 412/1993) | Climate | Descrittore climatico normativo | H03 non equivalente agli HDD annui osservati o stimati; mantenere separato. |
| `mean_altitude` | Altitudine media comunale | Climate / territorial context | Descrittore geografico | Nessuna equivalenza diretta nella tabella EPAH. |
| `snai_classification` | Classificazione comunale delle aree interne (SNAI) | Mobility / territorial context | Descrittore di perifericità | Nessuna equivalenza diretta; la classe A–F non misura l'accesso al TPL. |
| `dea_accessibility` | Tempo stradale verso il Comune sede di DEA I/II più vicino | Mobility | Accessibilità stradale | Non equivale a H26, che richiede accessibilità **senza automobile**. |
| `upper_secondary_accessibility` | Tempo stradale verso un polo di scuola secondaria superiore | Mobility | Accessibilità stradale | Non equivale a H26; elenco delle sedi e metodologie devono essere dichiarati. |
| `rail_accessibility` | Tempo stradale verso un accesso ferroviario attivo selezionato | Mobility | Accessibilità stradale | Non equivale a H27/H28: non misura distanza pedonale alle fermate né frequenza del servizio. |

## Nuovi indicatori candidati v0.3 selezionati

| ID progetto | Etichetta editoriale | Categoria | Stato |
| --- | --- | --- | --- |
| `h05_ape_fg` / H05 inventario | Quota di APE residenziali validi nelle classi energetiche F o G | Facilities/Housing, proxy prestazionale | Tecnico, filtri e fonte da verificare |
| `dwellings_not_occupied_by_residents` / ADD-HOUSING-01 | Quota di abitazioni non occupate da persone residenti | Facilities/Housing, descrittore non equivalente | Tecnico, fonte censuaria 2023 da verificare |
| H04 | Gradi-giorno annui di raffrescamento stimati da temperature giornaliere (CDD) | Climate, esposizione climatica | Tecnico, associazione celle/temperature da verificare |

## Struttura editoriale per tutte le schede

Adottare questa sequenza, senza alterare l'identificativo tecnico storico:

- **Nome descrittivo (unità)** — specifica esattamente l'universo.
- **Ruolo nel processo EPAH** — esito diretto, proxy di vulnerabilità, descrittore territoriale, politica/intervento, benchmark.
- **Definizione operativa** — numeratore, denominatore, metodo di calcolo e scala.
- **Fonte e riferimento temporale** — archivio ufficiale, accesso, versione, anno.
- **Interpretazione e limiti** — nessuna inferenza causale automatica, bias, impossibilità di identificare singole famiglie.
- **Stato dell'evidenza** — acquisizione, QA, revisione umana ed eventuale approvazione.

Non utilizzare le intestazioni «famiglie in povertà energetica», «tasso comunale di povertà energetica» o «rischio EPAH» per il solo insieme di proxy e descrittori.

Riferimento metodologico: https://energy-poverty.ec.europa.eu/system/files/2024-05/EPAHhandbook_diagnosis_finalpdf.pdf
