# Step 9 v0.4 — Gate di qualità end-to-end

Destinatari: tecnici che preparano il pacchetto e manutentori che revisionano una
PR. Questo step verifica i prodotti dello stesso snapshot, senza acquisire nuove
fonti, cambiare indicatori o autorizzare la pubblicazione.

## Controllo del pacchetto integrato

Il comando storico `--pack` resta disponibile. Il nuovo `--hub` controlla anche
atlante, schede, sintesi, grafici e navigazione locale:

```bash
uv run --locked python scripts/audit_v0_4_output_quality.py \
  --hub work/pacchetto-da-verificare \
  --json-out work/qa-step9.json
```

Usare un percorso nuovo per il report QA e tenerlo fuori dal pacchetto immutabile.
Il comando rifiuta un report QA dentro una directory d'ingresso. L'audit è di sola lettura e fallisce su checksum incoerenti, file fuori manifest,
symlink, stato di approvazione incompatibile, snapshot diversi, metadati delle
schede divergenti o ledger diverso dalla copia del report. Verifica inoltre:

- 27 Comuni, copertura per slot, corrispondenza delle osservazioni atlante/CSV;
- intestazioni, fonte, unità, periodi e righe visualizzate nel PDF tecnico contro
  gli stessi metadati e CSV, anche quando il PDF è stato riscritto e ricalcolato
  il suo hash;
- 27 schede A4 da due pagine, volume da 54 pagine e sintesi A4 da due;
- identità del testo delle pagine individuali e del volume, in ordine ISTAT;
- collegamenti HTML `href`/`src`, frammenti HTML e URI relativi dei PDF;
- PNG/SVG presenti per ogni serie disponibile: intestazione/dimensioni PNG,
  struttura/dimensioni SVG e assenza di riferimenti SVG esterni. I raster PNG
  incorporati dagli SVG Matplotlib sono locali e ammessi. I link web opzionali
  alle fonti sono elencati senza consultarli; non devono essere dipendenze degli output.

Non sono firme di autenticità. Una riscrittura coordinata di tutti gli input e
manifest non diventa una fonte verificata. Il controllo testuale PDF non misura
sovrapposizioni, contrasto, qualità tipografica o leggibilità su carta.

## Fixture sintetica riproducibile

La fixture usa il vero builder v0.4, i veri renderer di mappe/grafici, export,
ledger, report, schede e portale. Sostituisce soltanto l'ingestione del vecchio
pilota con osservazioni e geometrie generate dal test: **non** prova l'ingestione
scientifica degli originali. Nomi, geometrie, valori e fonti sono sintetici;
12 slot sono presenti e quattro sono assenti; lo zero osservato rimane zero.
Gli originali territoriali e le cartelle `data/` e `outputs/` non vengono usati.

```bash
EPAH_SYNTHETIC_QA_DIR=work/step9-synthetic \
  uv run --locked pytest -q tests/test_output_bundle_quality_v0_4.py
uv run --locked python scripts/audit_v0_4_output_quality.py \
  --hub work/step9-synthetic --json-out work/step9-audit.json
```

`EPAH_SYNTHETIC_QA_DIR` è un export facoltativo del test, verso una directory
inesistente. Non inserirlo nel pacchetto sotto test. In PowerShell impostare
`$env:EPAH_SYNTHETIC_QA_DIR="work/step9-synthetic"` prima del comando pytest.
Senza variabile il test usa soltanto le directory temporanee di pytest.

## Browser, tastiera, contrasto e screenshot

Il controllo browser è separato dalla suite Python: richiede Node, un'installazione
esistente di Playwright e Chromium. Non scarica dipendenze o browser e non modifica
workflow, permessi o lockfile. Nel runtime verificato erano disponibili Playwright
1.62.1 e Chromium 156.0.8078.79. Su altre macchine rendere disponibile `playwright`
a Node e indicare l'eseguibile con `EPAH_CHROMIUM` se diverso da `/usr/bin/chromium`.

```bash
node scripts/check_v0_4_browser.js work/step9-synthetic work/step9-browser-qa
```

Il runner avvia un server HTTP solo su loopback con porta libera, blocca le
richieste esterne e lo chiude al termine. A 390/768/1280 px verifica tutti i 16
indicatori e confronta ogni riga visibile con lo snapshot; prova ricerca senza
accenti, nessun risultato, reset, scelta del Comune da tastiera e relativo focus,
skip link e focus visibile. Carica PNG e controlla i link PNG/SVG per tutte le
serie presenti; sulle assenti non devono comparire grafici inventati.

Controlla l'overflow della pagina e il contenitore scorrevole della tabella mobile.
Misura contrasto testo/sfondo solo per cinque note/controlli opachi noti, richiedendo
4,5:1. Non verifica ogni elemento, placeholder, colore delle mappe, focus ring,
stato hover o screen reader: **non è un audit WCAG**.

Produce screenshot di portale, atlante, focus, registro e campioni di grafici,
più `browser_qa.json` con versioni, larghezze, esiti, hash del manifest d'ingresso e
checksum degli screenshot. Una directory QA preesistente non viene sovrascritta.
L'esito non equivale a revisione umana: `visual_review_completed=false`.

Nel browser gestito `file://` è bloccato dalla policy: il runner registra il
blocco e procede con HTTP locale, senza aggirare o modificare la policy.
Questo prova assenza di dipendenze esterne, **non** il funzionamento dell'archivio
aperto direttamente da disco su un altro computer.

## Risultato della revisione sintetica e correzione

Il gate integrato ha verificato 432 osservazioni, 48 grafici, 49 riferimenti HTML
e 55 URI PDF. Il browser ha completato le tre larghezze senza richieste esterne,
errori JavaScript o overflow della pagina; il contrasto minimo nei cinque campioni
è 5,58:1. Sono stati renderizzati e ispezionati campioni di scheda, report e sintesi
A4, oltre a mappa PNG/SVG e dot plot.

La verifica visiva ha riprodotto una collisione fra il titolo del dot plot e la
legenda della mediana. Il titolo prima partiva dal margine interno degli assi,
ristretto dalle etichette dei Comuni. Ora occupa un'area sopra il grafico, con
ritorno a capo e larghezza della figura. Il test misura i bounding box renderizzati:
il titolo rimane entro il foglio e non interseca la legenda. Nessun valore,
mediana, unità o ordinamento è cambiato; i nuovi PNG/SVG hanno nuovi checksum.

## Checklist umana prima della diffusione

| Verifica | Evidenza necessaria | Stato di questo step |
| --- | --- | --- |
| Integrità e coerenza degli export | Audit del pacchetto esatto con report QA separato | Verificato su fixture sintetica |
| Navigazione, focus e ricerca mobile | Browser a 390/768 px, tastiera e confronto con CSV | Verificato su fixture sintetica |
| Grafici, fonti e assenze | Ispezione PNG/SVG con 27 nomi consultabili | Campioni sintetici ispezionati |
| Stampa A4 leggibile | Schede e report stampati al 100%, nomi lunghi e casi con denominatori | Da verificare su output reali e carta |
| Lettura assistiva e contrasto completo | Screen reader, zoom 200%, stati dei controlli e mappe | Da verificare manualmente |
| Archivio offline trasferibile | Copia su altro computer, apertura diretta senza server | Da verificare: `file://` bloccato nel runtime |
| Originali e metodo | Revisione indipendente delle fonti territoriali ARPA/ISTAT/APE | Non eseguita; nessuna nuova validazione |
| Autorizzazione alla pubblicazione | Decisione scientifica e istituzionale separata | Non concessa |

Il gate automatico indica `technical_bundle_consistency_passed` o
`technical_browser_checks_passed`; `scientific_approval=false` e
`publication_allowed=false` restano fissi. La checklist reale non può essere
chiusa da una fixture o da un agente. Lo Step 10 (miglioramenti ricorrenti in PR
draft, con review umana) richiede una proposta separata; nessuna automazione
periodica è stata creata.

Rollback: ripristinare il codice precedente e rigenerare in directory nuove.
Nessuna migrazione di dati, nessun cambiamento a CI o impostazioni del repository.
