# V05-02: fonte climatica e fattibilità territoriale

Verifica documentale del 18 novembre 2026 per il tecnico incaricato e revisore.
Stato: `technical_draft_do_not_publish`. Fonte candidata identificata; nessun
originale UTCI acquisito in questa verifica, nessuna osservazione municipale
prodotta, nessuna approvazione scientifica o autorizzazione di raccolta.

## Conclusione operativa

Esiste una fonte Copernicus pertinente a V05-02. Il passo successivo è definire
una richiesta di dati circoscritta e revisionabile, **prima** di scaricare dati
o scrivere un estrattore. Le specifiche pubbliche non dimostrano ancora la
copertura effettiva dei 27 Comuni, la completezza di un anno o la rappresentatività
delle celle per il territorio montano.

## Evidenze verificate e loro ambito

| Evidenza | Risultato | Cosa non dimostra |
| --- | --- | --- |
| Rapporto EPAH fornito, §4.2 pp.38–42; tabella 9 p.40 ispezionata anche visivamente | Edizione 1940–2024, 40 GEO (39 Paesi e UE27); p.39 dichiara risultati nazionali e distingue classi cumulative/non cumulative | Non offre una serie comunale pronta all'uso |
| [CDS: Thermal comfort indices derived from ERA5 reanalysis](https://cds.climate.copernicus.eu/datasets/derived-utci-historical?tab=overview), DOI 10.24381/cds.553b7518 | Prodotto ERA5-HEAT `derived-utci-historical`, v1.1; griglia regolare 0,25°; dal 1940 a quasi tempo reale; NetCDF; UTCI in K e statistiche anche in giorni | Nessuna verifica dei byte o metadati di un export locale ancora assente |
| [Metodi Copernicus, sezione ERA5 Heat](https://climate.copernicus.eu/GCH2025-about-data-and-methods) | Descrive i conteggi del freddo sul minimo giornaliero UTCI e presenta soglie in °C | Non approva automaticamente una conversione o aggregazione nel nostro progetto |
| Originali NWIOI già recuperati per H03/H04 | Tmin/Tmax, maschera e orografia presenti; metadati riletti senza trasformazioni | Non sono un originale UTCI; non risolvono i blocchi H03/H04 |
| Registro comunale canonico | 27 righe, identità tramite codici ISTAT; hash conservato nel dossier locale | Il registro da solo non prova l'intersezione e copertura di una griglia climatica |

Il PDF consultato coincide con il catalogo esistente: SHA-256
`5f4605f253e747d23576bf7dea8bd06179fd70f157775c0817ef7ae95e2fb08b`.
Il [catalogo delle proposte](v0_5_indicator_contracts.json) resta invariato.
Le pagine del rapporto usano anche il termine generico temperatura; la fonte
Copernicus precisa la variabile UTCI. È un'evidenza per il revisore, non una
chiusura automatica della decisione già registrata.

Il catalogo CDS indica aggiornamenti intermedi e consolidati distinti. La
[pagina download](https://cds.climate.copernicus.eu/datasets/derived-utci-historical?tab=download)
richiama la licenza Copernicus. In questa sessione sono stati consultati soltanto
metadati pubblici: nessuna autenticazione, accettazione di termini per conto
dell'utente, richiesta dati o acquisizione di un export UTCI.

## Originali locali: verifica senza sostituzioni

La verifica riprende l'[inventario e il recupero v0.4](v0_4_source_recovery_progress.md).
Gli esatti file NWIOI conservati nella sessione hanno 20×24 celle; Tmin e Tmax
contengono 25.188 passi giornalieri dal 1 dicembre 1957 al 16 novembre 2026.
Questo intervallo dei file non è un nuovo anno scelto per l'indicatore.
Le unità delle due variabili di temperatura restano assenti; assi di temperature
e maschera conservano la differenza già documentata di circa 0,0005°.
Hash e metadati sono registrati nel dossier locale, senza cambiare gli originali.

La ricerca per nomi/estensioni nelle cartelle locali `outputs/`, `data/downloads/`,
`artifacts/` e la verifica dell'archivio di recupero non hanno identificato un
originale UTCI utilizzabile. È un esito limitato a questi controlli: non prova
l'assenza in ogni archivio compresso o in altre cartelle del manutentore.
Non si riacquisiscono gli originali NWIOI.

## Scelte successive del revisore

Il 19 novembre 2026 il revisore ha scelto esposizione al freddo, anno obiettivo
2025, giorni di stress e pacchetto preliminare sui 27 Comuni con dettaglio
comunale sostenibile. Vedere [decisioni e registro fonti](v0_5_2025_source_workplan.md).
Il confronto di anni sotto è il quesito storico: l'anno obiettivo ora è 2025,
con completezza della fonte, campo UTCI, classe e metodo spaziale da verificare.

## Decisione da preparare prima dell'estrazione

| Scelta aperta | Proposta da sottoporre al revisore | Evidenza necessaria per procedere |
| --- | --- | --- |
| Prodotto e variabile | Valutare prima le statistiche annuali dei giorni sotto soglia basate sul minimo UTCI giornaliero; evitare un download orario esteso se non necessario | Identificatore esatto del campo nel form/API, definizione della statistica e richiesta riproducibile |
| Periodo | Confrontare la comparabilità di un anno coerente con EPAH 2024 e di un anno della diagnosi territoriale | Decisione sull'anno; completezza del periodo e stato consolidato del prodotto selezionato |
| Unità e classi | Separare UTCI in K, soglie espresse in °C e conteggi in giorni; mantenere distinta ogni classe cumulativa e non cumulativa | Metadati dell'export e decisione esplicita su classe, estremi e trasformazioni; nessun calcolo qui |
| Geografia | Verificare celle, maschera e geometrie riferite all'esatto registro dei 27 Comuni | Versione/confini, intersezioni e copertura; confronto motivato fra metodi spaziali e loro limiti montani |
| Missingness e QA | Non convertire lacune, celle escluse o periodi incompleti in zero | Convenzioni del prodotto, criteri di rifiuto e replay indipendente da definire nel contratto |
| Accesso e provenienza | Preparare una richiesta minima dopo la revisione | Accesso autorizzato, termini applicabili, filtri/versione, ricevuta e hash dell'originale acquisito |

La scelta fra statistiche già pubblicate e ricostruzione da dati orari è ancora
aperta. La proposta sopra riduce l'acquisizione potenziale, ma non certifica
equivalenza statistica o rappresentatività comunale. Nessun campo API è stato
indovinato o inserito in un comando eseguibile.

## Confini e prossimo incremento

La copia locale della scheda V05-02 contiene le risposte preliminari su fonte,
copertura e limiti con riferimenti alle evidenze. La baseline generata rimane
intatta; le voci non determinate restano aperte. Compilare il dossier non lo
trasforma in un protocollo approvato e `methodology check` non ne valida le risposte.

Restano separati i [dossier H03/H04 e H05](v0_4_scientific_decisions.md),
la revisione abitazioni e la proposta V05-04 sulle persone in abitazioni
riqualificate. La fonte UTCI non risolve le questioni APE o le unità NWIOI.

Il prossimo incremento potrà preparare una richiesta minima di estrazione per
il revisore, dopo la decisione su prodotto, periodo, classe e metodo spaziale.
Seguiranno eventualmente acquisizione autorizzata, contratto locale distinto,
fixture sintetica e replay. Non modificare i 16 slot storici v0.4 e non usare
il benchmark nazionale come stima dei Comuni. Per la sequenza operativa vedere
il [workflow v0.5](v0_5_local_collection_workflow.md).
