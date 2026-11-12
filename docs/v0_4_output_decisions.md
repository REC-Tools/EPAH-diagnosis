# Decisioni per migliorare gli output EPAH v0.4 (10 gate)

Stato iniziale: 27 Comuni; v0.3.0 stabile come software; atlante v0.4
sperimentale a 16 slot; fascicolo HTML/CSV/PDF e tavola cartografica A4
già presenti. Alcuni indicatori non hanno ancora fonti originali.
Questo documento guida decisioni editoriali, **non** cambia la metodologia.

Ogni gate si chiude registrando scelta, responsabile, evidenza e criteri
di accettazione. **Scelte iniziali raccomandate** sotto: da confermare
prima di introdurre interpretazioni o grafici di confronto sostanziali.

| Passo | Decisione | Scelta di partenza | Criterio di uscita |
| --- | --- | --- | --- |
| 1 | Utente prioritario: tecnici, amministratori o pubblico | **Tecnici e amministratori**; pubblico solo dopo approvazione | Un lettore e un compito per ogni artefatto |
| 2 | Output principale: atlante, report o schede | **Atlante navigabile + PDF breve**, CSV per audit | Aprire ogni formato dallo stesso snapshot |
| 3 | Scopo della scheda comunale | **1–2 pagine:** profilo, limiti, fonte; nessuna graduatoria | Scheda utile anche con dati mancanti |
| 4 | Inventario e nomenclatura | **Nove canonici separati da sette candidati** | Un titolo, anno, unità, universo e fonte coerenti ovunque |
| 5 | Mappe e orientamento | **Mappa dei 27 Comuni con nomi/codici**, mappe per tema a scala chiara | Geometria verificata, legenda, A4 e mobile |
| 6 | Grafici di confronto | **Dot plot nominati** e tabelle; niente punteggio unico | Dati, piccoli denominatori e anni leggibili |
| 7 | Interazione e accessibilità | **Ricerca Comune, tastiera, colori accessibili** | Test desktop/mobile/print e fallback tabellare |
| 8 | Provenienza e missingness | **Hash, fonti, periodi e assenze esplicite** | Stessi valori in HTML, CSV, PDF; zero distinto da mancante |
| 9 | Gate di qualità | **CI + test semantici + revisione visiva umana** | Nessuna regressione; report QA riproducibile |
| 10 | Agente in background | **Una PR draft piccola per ciclo, mai merge automatico** | Diff circoscritto, CI verde, decisione umana finale |

## Ordinamento dei miglioramenti

**P0 — sicurezza e affidabilità:** verificare corrispondenza HTML/CSV/PDF,
SHA, denominatori e motivi dei dati mancanti. Il nuovo audit
`scripts/audit_v0_4_output_quality.py` costituisce il primo gate.

**P1 — usabilità immediata:** scheda comunale breve e indice, navigation
tra atlante e fascicolo, etichette su grafici, stampa A4, test a 390 px.

**P2 — arricchimenti:** grafici tra temi e confronti su periodi differenti
solo dopo decisioni esplicite sul metodo. Mai trasformare proxy territoriali
in incidenza di povertà energetica o indici EPAH certificati.

## Registro delle scelte

| Data | Gate | Opzione scelta | Motivazione | Approvato da |
| --- | --- | --- | --- | --- |
| 2026-11-12 | 1 | Tecnici e amministratori locali | Destinatari prioritari degli output | Utente |
| 2026-11-12 | 2 | Atlante HTML come punto di ingresso, PDF e CSV collegati | Architettura offline di consultazione e audit | Utente |
| 2026-11-12 | 3 | Schede comunali A4 da due pagine | Profilo leggibile e tracciabilità separati | Utente |
| 2026-11-12 | 4 | Catalogo semantico unico su 16 indicatori | Nomi, universi e limiti senza cambiare valori | Proposta tecnica implementata |
| 2026-11-12 | 5 | Solo fino a cinque nomi sulle mappe, per area del poligono e senza sovrapposizioni | Evitare affollamento e false priorità; tutti i 27 nomi restano nelle tabelle | Utente: richiesta di semplificazione cartografica |
| 2026-11-12 | 6 | Dot plot numerici con 27 etichette in ordine ISTAT; barre SNAI per categoria | Facilita il confronto senza presentare un ordinamento dei valori come priorità | Proposta tecnica implementata |

La possibilità di automatizzare la **proposta di PR** non equivale
all'autorizzazione a modificare metodologie, dati canonici o a pubblicare.
