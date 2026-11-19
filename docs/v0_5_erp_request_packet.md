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
