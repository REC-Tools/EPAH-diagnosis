# V05-02: proposta di richiesta minima UTCI 2025

Stato del 19 novembre 2026: `technical_draft_do_not_publish`. Richiesta preparata,
non inviata; nessun originale UTCI acquisito o dato comunale calcolato.
È il passo successivo alle [scelte 2025](v0_5_2025_source_workplan.md).

## Cosa è ora accertato

Il [catalogo pubblico CDS](https://cds.climate.copernicus.eu/api/catalogue/v1/collections/derived-utci-historical)
collega form, vincoli e descrizione del prodotto. Sono stati conservati snapshot
locali con SHA-256; gli URL delle risorse e gli hash sono nella
[proposta JSON](v0_5_utci_2025_request.json). La collection è un endpoint mutevole:
un aggiornamento successivo può cambiarne hash e collegamenti; usare quelli
dello snapshot o registrare una nuova verifica, senza sovrascrivere la precedente.

**Una singola regola dei vincoli pubblici** ammette contemporaneamente:

| Parametro | Valore candidato verificato |
| --- | --- |
| Dataset | `derived-utci-historical` |
| Variabile del pacchetto | `universal_thermal_climate_index_yearly_statistics` |
| Versione | `1_1` |
| Tipo | `consolidated_dataset` |
| Anno | `2025` |

Questo risolve l'identificazione del pacchetto annuale candidato. Non equivale
a una richiesta accettata dal server o alla verifica del contenuto di un export.
Il nome del singolo campo NetCDF dei conteggi sotto soglia resta sconosciuto:
la proposta lo conserva `null`, senza confonderlo con il nome del pacchetto.

La [descrizione CDS](https://cds.climate.copernicus.eu/datasets/derived-utci-historical?tab=overview)
espone statistiche annuali, con variabili in K e conteggi in giorni. Il form
pubblico ammette un'area rettangolare e avverte che il ritaglio può essere
aggiustato alla griglia. Unità e coordinate effettive vanno lette nell'originale.

## Area richiesta e identità dei Comuni

L'inviluppo candidato è **Nord 46,00; Ovest 6,75; Sud 45,00; Est 8,25** gradi,
nell'ordine CDS nord/ovest/sud/est. È calcolato dalle geometrie locali CRS84,
arrotondando verso l'esterno a 0,25° e aggiungendo un margine di 0,25° per lato.
La regola riguarda il dominio di acquisizione, non ricampionamento o precisione.
Nessun dato globale o serie oraria è richiesto nella proposta.

Verificata l'identità esatta dei 27 nomi/codici fra geometrie e registro canonico.
Hash di entrambi e inviluppo originale sono nel JSON; i file rimangono invariati.
Le geometrie dichiarano **boundary_year 2026**. Possono delimitare l'area
candidata, ma la loro compatibilità con l'analisi **2025 non è verificata**.
Prima dell'aggregazione ottenere geometrie 2025 o evidenza documentata della
stabilità dei confini pertinenti. Il solo codice ISTAT coincidente non basta.

## Impostazione confermata con condizioni dal revisore

1. **Misura:** totale annuo dei giorni con minimo UTCI giornaliero sotto **9 °C**,
   coerente con il totale presentato nel rapporto EPAH §4.2 pp.38–40. Non sommare
   le classi cumulative. La soglia è confermata condizionatamente dal revisore, non applicata.
2. **Aggregazione:** media dei conteggi delle celle, ponderata per la superficie
   di intersezione con il Comune. Calcolare le aree in una proiezione equivalente
   da confermare (proposta EPSG:3035). Il risultato può essere frazionario:
   giorni medi sulla superficie comunale, non giorni sperimentati da ogni famiglia.
3. **Copertura:** conservare area totale/valida, celle incluse/escluse e ragioni
   di assenza. Non trasformare mancanti in zero e non rinormalizzare in silenzio
   su una parte del territorio. Criteri di accettazione e tolleranze da deliberare.
4. **Limiti:** riportare risoluzione nativa, celle condivise da più Comuni e
   rappresentatività montana. Non introdurre differenze comunali artificiali,
   pesi demografici non documentati o correzioni altimetriche automatiche.

Questa impostazione, confermata dal revisore il 19 novembre 2026, non cambia
le definizioni del catalogo esistente. Il contratto locale rimarrà distinto dal
benchmark EPAH; condizioni e verifiche richieste restano da soddisfare. Non risolvono H03/H04 o H05. Nessun peso temporale è introdotto.

## Verifica richiesta sull'eventuale originale

- Identificare campo dei conteggi, unità, soglia, minimo giornaliero e natura
  cumulativa dalla documentazione e dagli attributi reali; non selezionare un
  campo semplicemente perché il suo nome sembra pertinente.
- Verificare 2025 completo e consolidato, dimensioni, maschera, valori mancanti,
  coordinate effettive e copertura spaziale dei 27 Comuni. Controllare i conteggi
  rispetto ai 365 giorni dell'anno, senza confondere lo zero con assenza.
- Preservare originale, richiesta esatta accettata, versione, termini applicabili,
  ricevuta e hash; preparare poi normalizzazione e replay indipendente.

Nessun client è stato modificato per inviare il JSON. Esso è una proposta
documentale, non un nuovo percorso operativo. Prima dell'acquisizione occorrono
revisione delle scelte e accesso CDS autorizzato con termini applicabili; non
sono state lette credenziali o accettate licenze per conto dell'utente.

**Decisione registrata il 19 novembre 2026:** il revisore ha confermato soglia
totale sotto 9 °C e media per superficie, subordinatamente alla verifica di
export, copertura e compatibilità dei confini 2025/2026. La conferma esplicita
è registrata nel JSON, distinta dagli esiti dei test. Non approva risultati o
pubblicazione, non accetta termini CDS e non chiude le condizioni pendenti.
