# Stress da caldo UTCI: replay locale delle fonti

Per il tecnico che deve confrontare i conteggi annuali con i massimi UTCI
giornalieri già acquisiti, prima di un protocollo comunale. Il controllo è
offline e non modifica originali, matrice canonica o dashboard.
Stato invariato: `technical_draft_do_not_publish`.

## Eseguire il controllo

Dal checkout con le dipendenze del lockfile revisionato:

```powershell
uv run --locked python scripts/audit_utci_heat_source.py --annual work/input/annual.nc --daily-zip work/input/daily.zip --year 2025 --json-out work/heat-source-audit-01.json
```

I percorsi sono esempi. Usare gli originali locali esistenti, senza
riscaricarli per adattarli ai nomi. La cartella del rapporto deve esistere;
il file di destinazione deve essere nuovo. Il programma non scarica dati,
non estrae lo ZIP sul disco e non contatta enti.

L'uscita è 0 solo quando tutte le celle sono complete e tutti i conteggi
annuali sono riprodotti. È 2 per fonte incompleta, discrepanze, struttura
non supportata o errore di scrittura. Le lacune numeriche producono un
rapporto `blocked`; gli errori strutturali interrompono prima della scrittura.

## Cosa viene verificato

- Campo `utci_daily_max`, con `cell_methods=time: maximum`, e quattro campi
  annuali `utci_days_above_{26,32,38,46}_daily_max` mantenuti separati.
- Griglia regolare 0,25°, coordinate esplicite e corrispondenza esatta;
  ordinamenti differenti sono allineati per coordinate, senza interpolazione.
- Calendario gregoriano esplicito, date uniche dell'anno scelto e supporti
  giornalieri ricevuti 00:00–23:00, senza riscriverli come intervalli semiaperti.
- Massimi giornalieri in Kelvin secondo la [specifica CDS](https://cds.climate.copernicus.eu/datasets/derived-utci-historical?tab=overview).
  Unità incompatibili sono rifiutate; se `units` manca, occorre la cronologia
  della conversione `-addc,273.15`. L'attributo originale resta assente.
- Contributi validi per cella: una data o cella mancante non diventa zero e
  impedisce la piena riproduzione. Sono supportati anche gli anni bisestili.
- Conteggi con confronto stretto `>` alle soglie convertite in Kelvin;
  i conteggi inclusivi `>=` sono conservati separatamente per la revisione.
- Hash di annuale, ZIP, membri NetCDF e cronologie; gli hash dei due input
  vengono ricontrollati al termine. Il rapporto non include percorsi assoluti.

Il rapporto conserva conteggi originali, conteggi ricalcolati, copertura e
problemi distinti. Non contiene medie comunali, pesi o classifiche.
Le prove automatiche usano esclusivamente NetCDF sintetici.

## Limiti e decisioni successive

Un replay coincidente documenta coerenza fra i prodotti ricevuti, non
autenticità, rappresentatività o correttezza delle contribuzioni orarie che
hanno generato ciascun massimo. Una cronologia coerente non è un audit del
processo del produttore. Se `>` e `>=` coincidono in assenza di valori sul
confine, questo non determina la semantica originale degli estremi.

L'operatore riprodotto non è un'approvazione scientifica del protocollo.
Le soglie cumulative non vanno sommate. Aggregazione comunale, pesi,
copertura e limiti montani richiedono revisione specifica secondo il
[piano dei prossimi passi](v0_4_dataset_next_steps.md). L'approvazione
dell'affitto non si estende ai dati climatici. Originali e rapporti reali
restano nell'archivio locale, fuori da Git.
