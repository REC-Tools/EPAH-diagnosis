# Cinque candidati abitativi aggiuntivi v0.5

Il 19 novembre 2026 il tecnico/revisore ha accolto tutte e cinque le proposte
discusse a partire dalla guida EUI. La decisione le seleziona per lo studio di
fattibilità: non approva ancora formule, dati, trasformazioni o pubblicazione.
Stato: `technical_draft_do_not_publish`; nessuna nuova osservazione prodotta.

## Contratti e distinzione dalle proposte precedenti

Il [catalogo abitativo](v0_5_housing_contracts.json) aggiunge gli ID **locali**
V05-19–V05-23, non codici ufficiali EPAH. Le [18 schede precedenti](v0_5_indicator_contracts.json)
rimangono invariate, anche per preservare il contratto della release software
v0.4.0. I due cataloghi usano lo stesso schema e gli stessi comandi: **18 + 5**
proposte, zero nuove serie comunali. Nessun nuovo percorso di acquisizione.

| ID | Candidato e unità proposta | Universo/denominatore | Collegamento e fattibilità |
| --- | --- | --- | --- |
| V05-19 | Famiglie in affitto, % | Famiglie in affitto / famiglie dello stesso universo censuario | Collegato a H23, ma non `100 − proprietari`: esistono altri titoli di godimento. Export comunale da verificare |
| V05-20 | Abitazioni in superficie abitativa critica ISAC, % | Abitazioni con criterio ISAC / tutte le abitazioni occupate dello stesso universo | Precisa il tema H24; ISAC ISTAT non coincide automaticamente con sovraffollamento Eurostat. Aggregati comunali non accertati |
| V05-21 | Alloggi ERP ogni 100 famiglie | Alloggi ERP nel territorio / famiglie residenti con data coerente | Attiva H16 già inventariato; stock per Comune e copertura ATC/Comuni da ottenere e deduplicare |
| V05-22 | ERP sfitti per manutenzione, % | Alloggi ERP sfitti per questa causa / totale ERP gestito dello stesso perimetro | Complemento di H16; distinto da ADD-HOUSING-01 e da altri motivi di mancata assegnazione |
| V05-23 | Rapporto prezzo abitazione/reddito | Prezzo e reddito annuo secondo una metodologia comparabile | Mapadomo: inizialmente benchmark NUTS3; nessuna attribuzione del rapporto provinciale come 27 stime indipendenti |

Fonti riprese dalla [biblioteca EUI e dal registro delle date](v0_5_2025_source_workplan.md):

- [ISTAT Abitazioni occupate](https://www.istat.it/wp-content/uploads/2026/02/Abitazioni-occupate-Anni-2021-2023.pdf),
  pp.2 e 4–5: titolo di godimento e ISAC; dati consultati 2021–2023, pubblicazione 2026.
- [Federcasa, Osservatorio ERP 2024/25](https://www.federcasa.it/dms/file/open?919609c0-42b5-4fd5-8d2b-2db540d57e38=),
  pp.20–21: patrimonio ERP e sfitto per manutenzione. La data dello stock locale
  e il perimetro degli enti non si deducono automaticamente dal titolo del rapporto.
- [JRC Mapadomo](https://joint-research-centre.ec.europa.eu/scientific-activities/mapadomo_en):
  rilascio progressivo e armonizzazione NUTS3. La raccolta di input LAU non
  dimostra la disponibilità di distribuzioni comunali per il progetto.

Primo esito della verifica: [fonti comunali e audit ATC](v0_5_housing_source_feasibility.md).

## Usare il percorso esistente

```powershell
uv run --locked epah methodology check --catalog docs/v0_5_housing_contracts.json
uv run --locked epah methodology prepare --catalog docs/v0_5_housing_contracts.json --indicator V05-19 --out-dir work/v05-housing-tenure-01
```

Usare una destinazione nuova per ogni scheda; sostituire l'ID per gli altri
quattro candidati. In `protocol.json`, `benchmark_contract` e `benchmark_source`
sono i nomi storici dei campi compatibili: conservano qui la proposta/fonte
originaria, non dichiarano che l'ERP sia un benchmark nazionale o un dato acquisito.
Le decisioni locali restano vuote. Il controllo `check` valida i metadati,
non le evidenze non acquisite, le risposte compilate o l'approvazione scientifica.

## Date, assenze e decisioni prima del calcolo

L'anno obiettivo rimane **2025**. Ogni fonte conserva il proprio periodo; i dati
2023 non diventano 2025 o 2026 per effetto dell'anno di pubblicazione. Usare
il registro esistente dei periodi e documentare la data degli aggregati locali.
Nessun peso temporale è applicato o approvato da questa selezione.

Per ISAC occorre il criterio nazionale ufficiale (famiglie con almeno quattro
componenti e soglia del quinto percentile), non un percentile calcolato sul Comune.
Per ERP occorre distinguere proprietà e gestione per evitare doppi conteggi,
cause dello sfitto, stock nullo, motivi ignoti e mancata risposta. Un Comune senza
risposta non è un Comune senza alloggi ERP; un rapporto con denominatore nullo
non è automaticamente zero. Per prezzo/reddito non dividere prezzi al m² per
reddito medio IRPEF senza un contratto coerente fra unità e popolazioni.

Ordine di approfondimento proposto: V05-19 e V05-21/V05-22, poi ISAC e Mapadomo.
Prima verificare originali e fonti già presenti, poi preparare eventuali richieste
di aggregati autorizzati. Le serie H03/H04, H05 e le revisioni già aperte restano
separate. Nessun indicatore qui, isolatamente, misura prevalenza di povertà energetica.
