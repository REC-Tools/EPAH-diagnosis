# V05-02: richiesta minima UTCI 2025 e controllo dell'export

Stato del 20 novembre 2026: `technical_draft_do_not_publish`. L'utente ha
autorizzato la richiesta esatta con accesso CDS configurato, dichiarando i termini
già accettati. Un solo job è stato inviato ed è terminato con successo;
archivio originale, richiesta e ricevute sono conservati localmente. Nessun
termine è stato accettato dall'agente, nessun dato comunale è stato calcolato.
È il passo successivo alle [scelte 2025](v0_5_2025_source_workplan.md).

La [proposta JSON del 19 novembre](v0_5_utci_2025_request.json) rimane invariata:
descrive le evidenze e le autorizzazioni disponibili **prima** dell'acquisizione.
Non è una ricevuta del job. I suoi `acquisition_authorized: false` e campo NetCDF
`null` non rappresentano lo stato successivo; le nuove ricevute locali registrano
l'autorizzazione del 20 novembre e l'esito effettivo.

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

La verifica del 19 novembre risolveva l'identificazione del pacchetto annuale candidato. Non equivaleva
a una richiesta accettata dal server o alla verifica del contenuto di un export.
Il nome del singolo campo NetCDF era ancora sconosciuto:
la proposta lo conserva `null`, senza confonderlo con il nome del pacchetto.
La nuova ispezione è descritta sotto, senza riscrivere tale evidenza storica.

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

Il JSON resta una proposta documentale, non un nuovo comando di acquisizione.
Il 20 novembre l'accesso configurato è stato usato per la sola richiesta
autorizzata; credenziali e URL firmati non sono inclusi nei resoconti. Non sono
stati modificati i precedenti downloader orari né registrate nuove credenziali.

**Decisione registrata il 19 novembre 2026:** il revisore ha confermato soglia
totale sotto 9 °C e media per superficie, subordinatamente alla verifica di
export, copertura e compatibilità dei confini 2025/2026. La conferma esplicita
è registrata nel JSON, distinta dagli esiti dei test. Non approva risultati o
pubblicazione, non accetta termini CDS e non chiude le condizioni pendenti.

## Originale ricevuto e limiti accertati il 20 novembre

La richiesta inviata coincide con `dataset` e `request_candidate` della proposta:
v1.1 consolidata, statistiche annuali 2025, area N46/W6,75/S45/E8,25.
Lo stato `successful` attesta la consegna CDS, non la completezza scientifica.

| Artefatto locale preservato | Evidenza |
| --- | --- |
| Archivio ZIP originale | 162554 byte; SHA-256 `adf33bdc12782e5956ad32e46fb477df63993cd36b6b5e44501906290b645b66` |
| Unico membro NetCDF, estratto senza modificarne i byte | 162287 byte; SHA-256 `2351896b5cc2ed8022185727d9311f9954fff907c8a5cfc958831c21f5b17190` |
| Richiesta e ricevute di invio/stato | Conservate fuori Git insieme all'originale; nessuna nuova acquisizione necessaria per ripetere l'audit |

Il NetCDF dichiara CF-1.6 e una griglia di **5 latitudini × 7 longitudini**:
latitudine 46→45, longitudine 6,75→8,25, passo 0,25°. È l'inviluppo delle
coordinate dei centri, non la copertura verificata dei 27 poligoni comunali.

Il campo candidato effettivamente presente è `utci_days_below_9_daily_min`.
L'ispezione esplicita trova 35 valori finiti, nessun mascherato/non finito e
valori compresi fra 221 e 365. Sono diagnostiche sulle celle del ritaglio,
**non osservazioni comunali**. Il campo non dichiara `units`, `long_name` o
`standard_name`; `cell_methods` è `time: minimum`. Il software segnala
`day_units_not_explicit`: non ricava l'unità dal nome né aggiunge attributi.
La [descrizione ufficiale CDS](https://cds.climate.copernicus.eu/datasets/derived-utci-historical?tab=overview)
descrive le statistiche in giorni, ma l'assenza nell'originale resta visibile;
la corrispondenza esatta di soglia, minimo giornaliero e cumulatività richiede
una decisione documentata sulle evidenze prima dell'uso scientifico.

Il calendario è `proleptic_gregorian`; una sola coordinata annuale usa
`hours since 2025-1-1 00:00:00`, con limiti `[0, 8759]`, decodificati in
**2025-01-01 00:00:00 → 2025-12-31 23:00:00**. Il controllo conserva questi
limiti e segnala `time_bounds_require_interpretation`: non li trasforma in un
intervallo semiaperto fino al 2026. L'attributo globale `frequency: day` non
dimostra la presenza dei 365 contributi giornalieri. Il controllo di serie
giornaliere/orarie esistente non va applicato a una sola statistica annuale.

## Ripetere il controllo offline

Il modulo indipendente `epah_diagnosis.utci_export_review_v0_5` appartiene al
livello degli audit delle fonti nell'[architettura](v0_4_architecture.md).
Riusa hash e pubblicazione locale delle directory esistenti; non introduce
un'alternativa a `epah outputs plan/run`, non acquisisce dati e non normalizza
o calcola indicatori. Non richiede accesso CDS per l'audit o per l'esempio.
Installazione e configurazione Windows sono nella [guida sviluppatore](v0_4_developer_guide.md).

Usare sempre una destinazione nuova; i file esistenti non vengono sostituiti.
In PowerShell, adattare soltanto il percorso dell'originale locale:

```powershell
$original = 'C:\percorso\originale.nc'
uv run --locked python -m epah_diagnosis.utci_export_review_v0_5 inspect --file "$original" --reference-year 2025 --json-out work/utci-inventory-01.json
uv run --locked python -m epah_diagnosis.utci_export_review_v0_5 inspect --file "$original" --reference-year 2025 --field utci_days_below_9_daily_min --json-out work/utci-review-01.json
```

Il primo comando inventaria senza scegliere un campo. Il secondo richiede una
scelta esplicita per l'ispezione, che non approva l'interpretazione scientifica.
Entrambi conservano hash, dimensioni, attributi pertinenti, maschera e packing
CF, tempo e coordinate. Il rapporto non include il percorso locale; la storia
di elaborazione resta nell'originale ed è rappresentata nel rapporto da un hash.

Codici di uscita: **0** controlli strutturali senza anomalie (revisione comunque
necessaria); **2** rapporto scritto con lacune o scelta del campo pendente;
**1** errore di lettura/scrittura, sorgente mutata durante la lettura o destinazione
già presente. Il JSON contiene gli esiti espliciti; un 2 non va registrato come
test software fallito o come acquisizione fallita. Per questo originale il
secondo comando restituisce 2 per unità mancanti e limiti temporali da interpretare.

Esempio sintetico, con lo stesso servizio di controllo:

```powershell
uv run --locked python -m epah_diagnosis.utci_export_review_v0_5 example --out-dir work/utci-synthetic-01
uv run --locked python -m epah_diagnosis.utci_export_review_v0_5 inspect --file work/utci-synthetic-01/synthetic.nc --reference-year 2025 --field example_days --json-out work/utci-synthetic-replay-01.json
uv run --locked pytest -q tests/test_utci_export_review_v0_5.py
```

Il generatore restituisce 0 quando l'esempio è completo. Il replay restituisce
intenzionalmente 2: una cella mascherata deve restare una lacuna, distinta dallo
zero valido. `review.json` e il replay devono coincidere. I dati sono marcati
`SOFTWARE TEST FIXTURE, NOT ERA5-HEAT`; non sono evidenze territoriali.

## Consultare il pacchetto UTCI offline

Il JSON dell'audit può ora essere consultato in un pacchetto locale con HTML,
originale e hash. Con `$original` impostato come sopra:

```powershell
uv run --locked epah methodology utci-portal --file "$original" --reference-year 2025 --field utci_days_below_9_daily_min --out-dir work/utci-review-portal-01
```

Aprire `index.html` e conservare la cartella intera. I quattro file sono:

| File | Contenuto |
| --- | --- |
| `source/original.nc` | Copia identica dei byte del NetCDF selezionato |
| `review.json` | Nuovo controllo prodotto da `inspect_export`, non un rapporto salvato accettato come prova |
| `index.html` | Campo, unità ricevuta o sua assenza, anno richiesto, tempo effettivo, valori, coordinate e questioni aperte |
| `manifest.json` | SHA-256 di originale, controllo e HTML; stato di bozza e approvazioni false |

Il builder verifica che copia, originale ispezionato e sorgente al termine della
preparazione abbiano lo stesso hash. La destinazione deve essere nuova; la
cartella completa viene esposta tramite `directory_publication`, come gli altri
prodotti. Un errore prima di questo passaggio non lascia un pacchetto parziale.
Il manifest non include il proprio hash, evitando un riferimento circolare.

Il renderer legge soltanto lo snapshot dell'audit: non converte unità, non
calcola indicatori e non legge un secondo originale per riempire lacune. I
valori numerici del file non sono medie comunali; anche un controllo strutturale
senza anomalie lascia aperte semantica, completezza e copertura. Il comando
restituisce **0 quando il pacchetto è costruito**, anche con lacune esplicite;
**2 quando la costruzione è bloccata**. Uno 0 non è approvazione scientifica.

Il pacchetto non acquisisce dati né certifica versione o provenienza CDS. ZIP,
richiesta e ricevute dell'acquisizione restano nell'archivio locale separato;
il NetCDF si riconcilia tramite l'hash documentato sopra. Non viene aggiunto
automaticamente alla catena `epah outputs` dei risultati territoriali.

### Esempio sintetico del portale e replay indipendente

```powershell
uv run --locked python -m epah_diagnosis.utci_export_review_v0_5 example --out-dir work/utci-portal-input-01
uv run --locked epah methodology utci-portal --file work/utci-portal-input-01/synthetic.nc --reference-year 2025 --field example_days --synthetic --out-dir work/utci-portal-demo-01
uv run --locked python -m epah_diagnosis.utci_export_review_v0_5 inspect --file work/utci-portal-demo-01/source/original.nc --reference-year 2025 --field example_days --json-out work/utci-portal-replay-01.json
```

Il flag `--synthetic` espone l'avviso **DATI SINTETICI · NON SONO DATI TERRITORIALI**
nel portale e la dichiarazione nel manifest. È un'etichetta dichiarativa;
senza flag l'input resta `unclassified_local_source`, non diventa una fonte
certificata. Il replay restituisce intenzionalmente 2 per la cella mascherata;
il suo JSON deve coincidere con `review.json` del portale:

```powershell
uv run --locked python -c "import json; from pathlib import Path; assert json.loads(Path('work/utci-portal-demo-01/review.json').read_text(encoding='utf-8')) == json.loads(Path('work/utci-portal-replay-01.json').read_text(encoding='utf-8'))"
uv run --locked pytest -q tests/test_utci_review_portal_v0_5.py tests/test_utci_export_review_v0_5.py
```

Gli esempi richiedono sempre nuove destinazioni e nessun originale privato o
accesso CDS. Il portale usa collegamenti relativi, CSS incorporato e nessuno
script o asset remoto; i metadati ricevuti sono testo escapato. Le prove
automatiche di link, contenuti e hash non sostituiscono l'ispezione visiva nel
browser, soprattutto su mobile e in stampa.

## Fare i controlli giusti sul pacchetto

### 1. Controllo automatico, senza modificare il pacchetto

```powershell
uv run --locked epah methodology utci-audit --pack work/utci-review-portal-01 --json-out work/utci-pack-audit-01.json
```

Il rapporto deve essere nuovo e **fuori** dal pacchetto. Il comando funziona
anche dopo il trasferimento dell'intera cartella e non richiede CDS, credenziali
o pytest. Verifica i quattro membri del contratto v1, gli hash, gli stati di
bozza, il replay del NetCDF e la corrispondenza di tabelle, periodi, coordinate,
avvisi, codici delle questioni e collegamenti HTML. Non richiama il renderer e
non usa il rapporto salvato come prova di sé stesso. Un HTML alterato resta
incoerente anche se ne è stato aggiornato l'hash nel manifest.

**0 / COERENTE** significa che il pacchetto è internamente coerente, non che
la fonte sia scientificamente approvata. `source_review_issues` conserva tutte
le questioni aperte: nel pacchetto reale corrente sono due. **2 / BLOCKED**
indica un problema di struttura, hash, replay o presentazione; fermarsi e
conservare l'evidenza, senza correggere manualmente JSON o manifest. Il comando
non ripara, cancella o sovrascrive i file. Non accetta file aggiuntivi nel
pacchetto: tenere note e nuove ricevute esterne alla baseline.

JSON con chiavi duplicate o valori non finiti, percorsi estranei nel manifest,
file mancanti, link simbolici e dichiarazioni di approvazione sono rifiutati.
La verifica non certifica autenticità/versione CDS, rappresentatività, layout,
visibilità CSS, accessibilità o autorizzazione istituzionale.

Per provare il comando sull'esempio sintetico generato sopra:

```powershell
uv run --locked epah methodology utci-audit --pack work/utci-portal-demo-01 --json-out work/utci-demo-audit-01.json
uv run --locked pytest -q tests/test_utci_review_audit_v0_5.py
```

Il risultato atteso è 0 con una questione della fonte ancora aperta: la cella
mascherata intenzionale. Non confondere questo esito con il 2 del precedente
comando `inspect`, che segnala lacune nella fonte, non incoerenze del pacchetto.

### 2. Controllo visivo del revisore

- Aprire `index.html`: testi interi, tabelle leggibili, collegamenti a originale,
  JSON e manifest funzionanti; provare una finestra stretta e l'anteprima stampa.
- Verificare che campo e anno richiesto siano quelli attesi e che il tempo
  effettivo del file rimanga distinto. Nel pacchetto reale: campo
  `utci_days_below_9_daily_min`, anno richiesto 2025, limiti fino al
  31 dicembre 2025 alle 23:00.
- Le due lacune note devono restare visibili. Minimo e massimo sono valori
  numerici delle celle: non medie comunali né una prevalenza di povertà energetica.
- Confermare che la bozza non presenti risultati come approvati. Negli esempi
  deve essere evidente anche l'avviso sui dati sintetici.

### 3. Decisioni sulla fonte, con una nota leggera

Per unità/soglia, completezza annuale e copertura territoriale registrare in
una nota esterna: **cosa è stato verificato — evidenza precisa — esito e ciò
che resta aperto**. Per esempio, un collegamento alla descrizione della fonte
non dimostra da solo la presenza di tutti i contributi giornalieri. Non
attribuire l'unità soltanto dal nome del campo, non interpretare automaticamente
i limiti temporali e non dedurre la copertura dei Comuni dall'inviluppo dei centri.
La nota può registrare una proposta o una verifica; non modifica gli originali
né autorizza automaticamente risultati o pubblicazioni.

### 4. Controlli prima del merge del software

Attendere tutti i check dell'ultimo commit, anche quelli rilanciati passando
la PR da draft a pronta o modificandone la descrizione, e leggere gli eventuali
rilievi della revisione. Il passaggio a pronta non equivale a controlli conclusi.
Il run della #196 rilanciato al momento del merge è fallito nel checkout perché
`refs/pull/196/merge` era già scomparso: non ha eseguito il controllo dati.
La CI su `main` e la revisione del codice sono concluse positivamente. Questo
caso non va interpretato come approvazione scientifica né come dato corrotto.

## Prossima revisione, senza nuovi invii

Per V05-02 restano da documentare l'unità e la semantica esatta del campo,
l'interpretazione del periodo e la completezza dei contributi, poi celle e
intersezioni con i 27 Comuni, compatibilità geografica e proiezione equivalente.
Non si presume che i confini siano cambiati: serve evidenza della compatibilità
pertinente. Criteri sulle lacune e tolleranze non sono introdotti automaticamente.
L'audit mantiene separati anno-obiettivo, metadati della fonte e approvazione;
non applica pesi temporali. Tutti i flag scientifici e di pubblicazione restano
falsi. H03/H04, H05, affitto e le altre revisioni conservano i rispettivi blocchi.
