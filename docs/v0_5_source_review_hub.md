# Portale unico delle fonti climatiche e abitative

Per il tecnico che consulta i 27 Comuni: una tabella offline con originali,
anni, acquisizioni documentate, controlli e lacune. È una revisione delle fonti,
con stato `technical_draft_do_not_publish`, non un nuovo atlante di indicatori.
Il comando non acquisisce dati, non contatta enti e non modifica osservazioni.

## Prova senza dati privati

Da un checkout installato con il lockfile revisionato:

```powershell
uv sync --python 3.11 --locked --group dev
uv run --locked epah methodology source-portal --example --out-dir work/source-demo-01
uv run --locked epah methodology source-audit --pack work/source-demo-01
```

Aprire `work/source-demo-01/index.html` e conservare l'intera cartella.
L'esempio genera 27 identità fittizie, una tabella ATC vuota e un NetCDF sintetico
con una cella mancante. Affitto assente e tabella vuota rimangono lacune: non
diventano valori zero. Il percorso di composizione e gli audit sono quelli
di produzione. Non richiede credenziali, rete o pytest.

## Comporre le fonti locali già raccolte

Il registro è obbligatorio e deve avere esattamente 27 identità distinte.
Ogni fonte è opzionale: ometterla produce una lacuna esplicita. Se presente,
la run affitto deve usare gli stessi byte del registro e richiede la nota
del revisore. UTCI richiede il campo scelto esplicitamente; il controllo è
impostato sul riferimento 2025, senza rietichettare il tempo ricevuto nel file.

```powershell
uv run --locked epah methodology source-portal --registry work/tenure-run/inputs/registry.csv --tenure-run work/tenure-run --notes work/tenure-portal/inputs/review-notes.md --utci-source work/utci-review/source/original.nc --utci-field utci_days_below_9_daily_min --atc-index work/atc-inputs/index.json --out-dir work/source-review-01
uv run --locked epah methodology source-audit --pack work/source-review-01
```

Usare la nota conservata nel portale affitto quando si desidera riprodurre
esattamente quella versione, inclusi i terminatori di riga. Le date mancanti
non si ricavano da nome del file, data della pagina o metadati del filesystem.
La ricevuta ISTAT documenta l'acquisizione solo dove disponibile; un originale
seed senza data rimane «non documentata». Anno fonte 2021 e obiettivo 2025
restano separati, senza pesi. I decimali e i residui sono conservati integralmente.
Il totale della tavola ISTAT esclude le famiglie senza tetto.

### Associare le tabelle pubbliche ATC, un ente alla volta

Preparare un indice locale e collocare accanto ad esso le copie inalterate
delle risposte già disponibili. Non ripetere le acquisizioni. L'indice ha
esattamente questi campi; ogni codice può comparire una sola volta:

```json
{
  "provider": "ATC Piemonte Centrale",
  "entries": [
    {
      "istat_code": "001066",
      "source_selector": "CASTELLAMONTE",
      "file": "atc_001066.html",
      "reference_date": null,
      "acquired_on": null,
      "source_url": "https://giano.casaatcservizi.it/servizio/patrimonio/"
    }
  ]
}
```

`file` deve essere un semplice nome, senza directory. Date ISO `YYYY-MM-DD`
oppure null; URL pubblico senza credenziali oppure null. Il selettore documenta
l'associazione dichiarata da chi ha raccolto la risposta: non prova un codice
ISTAT fornito dalla fonte. `source_url` può indicare la pagina di accesso e non
certifica l'origine dell'export. `reference_date`, se dichiarata, resta da
verificare: il programma non la approva. Un Comune non elencato significa
«tabella non inclusa», non assenza di patrimonio.

Il controllo ATC esistente conta righe e segnala gruppi identici e celle
numeriche non interpretabili. Non somma alloggi, non elimina righe e non
deduce stock, assegnabilità o causa dello sfitto. Gli originali HTML vengono
copiati byte per byte con suffisso `.html.txt`, per consultarli come testo.
Il portale non incorpora HTML ricevuto né copie dei vecchi portali.

## Confrontare due versioni

Ripetere lo stesso comando con input aggiornati, una destinazione nuova
e `--previous work/source-review-01`, per esempio:

```powershell
uv run --locked epah methodology source-portal --registry work/tenure-run/inputs/registry.csv --tenure-run work/tenure-run --notes work/tenure-portal/inputs/review-notes.md --utci-source work/utci-review/source/original.nc --utci-field utci_days_below_9_daily_min --atc-index work/atc-inputs/index.json --previous work/source-review-01 --out-dir work/source-review-02
uv run --locked epah methodology source-audit --pack work/source-review-02
```

Il pacchetto precedente viene controllato prima del confronto, senza modificarlo.
La nuova cartella conserva una copia dei suoi input sotto `baseline/`; non
clona ricorsivamente confronti ancora precedenti. Per una storia completa
conservare anche le cartelle precedenti. Si confrontano identità comunali uguali,
stesso tipo dichiarato di input e stesso ente, quando presente in entrambe le
versioni. È possibile aggiungere o rimuovere una fonte prima assente. Non si
confrontano automaticamente gestori diversi o fonti sintetiche con fonti reali.

`comparison.json` distingue modifiche dei campi (valori originali, periodi,
date dichiarate, stati e copertura) e degli hash degli originali. Un file
cambiato con gli stessi valori non è un cambiamento del fenomeno. Non si
calcolano delta percentuali, tendenze territoriali o pesi temporali. Il pannello
UTCI confronta il file e le sue diagnostiche, non statistiche comunali.

## Contratto del pacchetto e controlli

```text
index.html         tabella e pannelli offline, senza JavaScript
inputs.json        selezione dichiarata delle fonti; nessun percorso assoluto
snapshot.json      stato dei 27 Comuni e controlli ricalcolati
comparison.json    differenze fra importazioni, oppure null
manifest.json      SHA-256 di tutti gli altri file
sources/           registro, originali, indice ATC, ricevute e note ISTAT
baseline/          input e snapshot della versione precedente, se richiesta
```

`source_review_hub_v0_5.py` compone gli adattatori affitto, ATC e UTCI esistenti.
`source_review_hub_render_v0_5.py` rende lo snapshot senza leggere le fonti.
`source_review_hub_audit_v0_5.py` controlla appartenenza e hash dei file,
ricalcola gli snapshot delle due versioni e le differenze, quindi verifica
tabella, collegamenti, blocchi JSON, avvertenze e risorse HTML ammesse senza
importare il renderer. Commenti HTML, script, risorse esterne e CSS non
revisionato sono rifiutati. Si rifiutano link simbolici e junction Windows.
Questi controlli attestano coerenza interna, non autenticità della fonte:
una nuova fonte con manifest coerente resta da revisionare.

La composizione prepara una directory temporanea, la verifica e usa
`publish_directory`; rifiuta destinazioni esistenti e sovrapposte agli input.
In caso di errore non modifica gli originali o il pacchetto precedente.
La CLI restituisce errore con prefisso `BLOCKED`. Per riprovare, usare una
destinazione nuova. Il lockfile, le dipendenze e i workflow CI restano invariati.

Questo percorso rimane in `epah methodology`: prepara la revisione delle
fonti, prima delle osservazioni. Il percorso territoriale v0.4 resta
`epah outputs plan/run`; non viene introdotta una seconda catena di indicatori.

## Limiti e prossime revisioni

- UTCI: unità non esplicite e limiti temporali dell'originale 2025 da interpretare;
  copertura e media comunale per area ancora da verificare. File presente non
  significa 27 Comuni coperti.
- ATC: le sei risposte pubbliche già raccolte non sono stock ERP completo datato;
  restano da chiarire righe identiche, perimetro, assegnabilità e cause dello sfitto.
- Affitto: resta contesto storico 2021, con universo della tavola e residui
  invariati; verificare la spiegazione ufficiale dei conteggi decimali.
- H03/H04, H05 e gli altri candidati mantengono i propri dossier aperti.

Test e audit non approvano indicatori o pubblicazione. Controllo visivo,
accessibilità con tecnologie assistive e revisione scientifica richiedono
verifiche umane distinte. Nessun merge o pubblicazione è eseguito dal comando.
