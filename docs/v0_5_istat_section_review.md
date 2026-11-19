# Affitto e ISAC: cosa consentono gli originali ISTAT locali

Verifica del 19 novembre 2026. Anno obiettivo 2025, fonte esaminata riferita
al 31 dicembre 2023. Stato `technical_draft_do_not_publish`.

## Esito per il tecnico

Gli originali già recuperati sono sufficienti per verificare la presenza delle
sezioni dei 27 Comuni e leggere il dizionario dei campi. Non forniscono i dati
necessari per calcolare V05-19 (famiglie in affitto) o V05-20 (ISAC).

| Verifica sugli originali locali | Esito |
| --- | --- |
| Tracciato e intestazione del file Piemonte | 138 campi, corrispondenza completa |
| Righe con identità di sezione nel file Piemonte | 49.435, senza duplicati Comune/sezione |
| Righe corrispondenti al registro del progetto | 978, con presenza per tutti i 27 codici |
| Originali e registro | Hash invariati rispetto al recupero precedente |
| Disponibilità dei due indicatori | Non dimostrata dalla presenza delle sezioni |

Il risultato conferma il controllo geografico delle righe già selezionate nel
[recupero v0.4](v0_4_source_recovery_progress.md); non acquisisce nuovamente
l'archivio e non approva il mapping abitazioni. La compatibilità territoriale
rimane una verifica distinta. Non sono stati letti o validati i valori delle
variabili abitative per produrre nuovi indicatori.

## Campi effettivi e dati ancora necessari

Il dizionario contiene `PF1` (famiglie residenti totali), `PF3`–`PF8` (numero
di componenti), `PF9` (famiglie coabitanti), `A2` (abitazioni occupate da
residenti), `A3` (vuote oppure occupate solo da non residenti), `A5` (altri
alloggi occupati) e `A8` (abitazioni totali). Non contiene categorie del titolo
di godimento, superfici o un aggregato ISAC.

- **V05-19:** serve una tavola comunale del titolo di godimento, con affitto,
  altre categorie, totale, periodo, universo e mancanti. `PF1` non fornisce il
  numeratore. Non usare `100 − proprietari` né dividere un numeratore 2021 per
  famiglie 2023 senza una decisione scientifica esplicita.
- **V05-20:** serve un aggregato ISAC comunale ufficiale oppure microdati
  autorizzati con il criterio nazionale documentato. Componenti della famiglia
  e abitazioni occupate, separatamente, non ricostruiscono la distribuzione
  congiunta con le superfici. Non calcolare un percentile locale o sostituire
  case non occupate, coabitazione o componenti medi.

I [contratti delle proposte](v0_5_housing_candidates.md) restano invariati.

## Ripetere l'inventario indipendente

Il comando usa due copie locali dei membri originali, senza estrarre o
riscaricare l'archivio. I percorsi sotto sono esempi da sostituire con le
posizioni effettive; non duplicare gli originali solo per adattarli all'esempio.

```powershell
uv run --locked python -m epah_diagnosis.istat_section_source_review_v0_5 --data work/input/R01_Piemonte_2023_sezioni.xlsx --layout work/input/TRACCIATO_FILE_REGIONALI.xlsx --registry data/municipalities.csv --reference-year 2023 --json-out work/istat-section-review-01.json
```

La directory genitore deve esistere e il report deve essere nuovo. Un file
esistente, anche vuoto, o un link simbolico non viene sostituito. Il controllo
rifiuta layout ambigui, colonne incoerenti, identità assenti/non numeriche,
duplicati e input modificati durante la lettura. Non elimina righe per far
riuscire l'audit. Il dizionario e la copertura per codice sono conservati nel
JSON con gli hash dei tre input; i percorsi locali non sono inclusi.

`source_section_rows` è un numero di righe, non un numero di famiglie o
abitazioni. `not_observed` significa che un codice non compare nel file
esaminato, non assenza di fenomeno. Il rapporto non verifica valori, formule,
anni, completezza degli indicatori o compatibilità territoriale. L'anno CLI è
una dichiarazione del chiamante, non una data dedotta dal nome del file:
`reference_year_verified` resta false; la verifica del periodo usa la fonte
primaria sotto. Nessuna serie comunale o approvazione viene aggiunta.

## Verifiche pubbliche e prossimo passo

La [pagina ISTAT delle sezioni](https://www.istat.it/notizia/dati-per-sezioni-di-censimento/)
specifica dati al 31 dicembre 2023 su basi territoriali 2021, con aggiornamenti
del rilascio nel 2026. Non sono dati 2025. Il tracciato locale riporta proprio
le variabili sopra: l'anno di pubblicazione non aggiunge variabili mancanti.

Il [comunicato Abitazioni occupate](https://www.istat.it/comunicato-stampa/abitazioni-occupate/)
definisce ISAC e collega il rapporto, ma nella pagina consultata non è stato
individuato un export ISAC dei 27 Comuni. Non si conclude che non esista in
altri canali. I valori per regione o tipologia di Comune restano contesto.

### Ripristino dei metadati e pilota affitto

Il nuovo controllo ha restituito HTTP 200 per i
[metadati ufficiali del flusso](https://esploradati.istat.it/SDMXWS/rest/dataflow/IT1/DF_DCSS_HUDW_1_COM/1.0/?detail=Full&references=Descendants)
`IT1 / DF_DCSS_HUDW_1_COM / 1.0`, nome confermato «Famiglie per titolo di
godimento - comuni», DSD `DCSS_HUDW_TV`. Snapshot: 12.469.910 byte, SHA-256
`13ca7a84d04ac63b80d7bae8e6ab6fae557d320afb04678aac279c5ed5334e28`.
L'ordine verificato delle dimensioni è `FREQ`, `REF_AREA`, `INDICATOR`,
`TENURE_STATUS_HOU`, `PERIOD_CONSTRUCT`, `OCC_STATUS_CDW`, `USE_FLOOR_SPACEGROUP`,
`NUMBER_OCCUPANTS`, `DENSITY_STANDARD`, `HEATING_SYSTEM_TYPE`; il tempo è
`TIME_PERIOD`. I 27 codici sono nella codelist, fatto distinto dalla presenza
di osservazioni per tutti i 27 Comuni.

Un pilota pubblico per Alpette (`001007`) ha restituito quattro osservazioni
**2021**, indicatore `NPHH_AV`, categorie `ALL`, `RENT`, `OWN`, `OTH_OR`.
Sono stati conservati valori originali, anche decimali, e attributi: nessun
arrotondamento o rapporto calcolato. Con `lastNObservations=1` si ottiene
l'ultima osservazione per serie, non una garanzia di completezza storica o
dell'anno obiettivo. SHA-256 del pilota:
`57482717d9a708d4299f510ca0edaec2a28fb746dd7acc78db778ae0c7fdaf14`.

La query riuscita del pilota, da conservare con gli header di formato SDMX
GenericData XML 2.1 e la ricevuta, è:

```text
https://esploradati.istat.it/SDMXWS/rest/data/IT1,DF_DCSS_HUDW_1_COM,1.0/A.001007........?dimensionAtObservation=TIME_PERIOD&lastNObservations=1
```
La nota primaria `TIT_POSSESSO__ALL_N1` precisa che il totale della tavola
esclude le famiglie senza tetto. Per V05-19 occorre quindi revisionare
l'universo del denominatore: non sostituirlo automaticamente con `PF1` delle
sezioni 2023 o con un totale generale di famiglie.

Le richieste su tutti i 27 codici, prima con dimensioni libere e poi con le
combinazioni effettivamente restituite insieme nel pilota, sono scadute dopo
30 secondi prima degli header HTTP. Il primo tentativo aveva inoltre ottenuto
422 per `dimension_at_observation`: il nome accettato dal servizio è
`dimensionAtObservation`, corretto prima del pilota riuscito. Errori e timeout
sono conservati separatamente e non sono dataset acquisiti. Nessun ciclo di
retry automatico. ISTAT documenta un
[limite di cinque query al minuto](https://www.istat.it/classificazioni-e-strumenti/web-services-sdmx/).

Copertura dei dati di affitto osservata in questa verifica: **1/27**, non
27/27; per gli altri 26 Comuni la disponibilità resta non verificata, non zero.
Il prossimo incremento potrà acquisire gli altri codici con richieste limitate,
ritmate e ricevute di errore, verificare periodi/categorie/flag e preservare
eventuali valori decimali. Prima della normalizzazione serve un contratto
locale separato con denominatore e criteri di missingness espliciti.
Non usare i metadati disponibili per dichiarare riuscito un export fallito.

Nessun ente o stakeholder è stato contattato. ERP resta una bozza locale.
H03/H04, H05 e l'export UTCI restano dossier separati. Il risultato di questo
incremento è un inventario verificabile con un limite concreto, non due nuove
serie disponibili: la prossima acquisizione dovrà colmare i campi identificati.
