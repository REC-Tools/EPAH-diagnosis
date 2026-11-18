# Esempio v0.4 senza originali territoriali

Destinatari: nuovi contributori che vogliono vedere il percorso dei prodotti
prima di acquisire fonti reali. L'esempio usa 27 Comuni fittizi, geometrie e
valori sintetici e i renderer di produzione per HTML, CSV, grafici, PDF,
schede e portale. Nessuna osservazione descrive il territorio reale.

## Installare ed eseguire

Da un checkout dei sorgenti, con Python 3.11+ e `uv`:

```powershell
uv sync --python 3.11 --locked --no-dev
uv run --locked --no-dev epah examples synthetic --out-dir work/synthetic-example-01
```

Gli stessi comandi funzionano in shell POSIX. Non servono pytest, download
ISTAT/ARPA, credenziali, dati canonici o file ignorati da Git. Il comando genera
gli input fittizi in libreria, condivide il rendering dell'atlante territoriale
e usa i normali builder del fascicolo/portale e i due audit indipendenti.
Non crea un bundle pilota verificato dalle fonti.

Scegliere ogni volta una destinazione nuova. Una directory o un file esistente
viene rifiutato prima della generazione, anche se vuoto. Non esiste un'opzione
per sovrascriverlo. Un errore restituisce un codice non zero; il risultato finale
viene esposto solo dopo entrambi gli audit. La preparazione temporanea usa lo
stesso filesystem e la pubblicazione locale riusa `publish_directory`.

Aprire `work/synthetic-example-01/hub/index.html`, mantenendo tutta la cartella
`hub/` insieme. `work/` è ignorata da Git. Il comando stampa il percorso del
portale con l'avviso **ESEMPIO SINTETICO - NON PUBBLICARE**.

## Seguire input, osservazioni e controlli

```text
synthetic-example-01/
  inputs/   registro, geometrie e snapshot sintetici deterministici
  atlas/    rendering, catalogo, grafici e registro delle evidenze
  review/   osservazioni CSV, metadati e fascicolo HTML/PDF
  hub/      portale offline, sintesi e 27 schede da due pagine
  qa/       audit del fascicolo e del portale, esterni ai prodotti
  run.json  esito, natura sintetica, disponibilità e hash
```

1. `inputs/synthetic_snapshot.json` contiene i valori generati. Nomi, geometrie
   e associazioni dei codici sono fittizi, da non unire a fonti reali.
2. `atlas/atlas_data.json` dichiara `synthetic_fixture: true`: 16 slot,
   12 serie disponibili e H03/H04/H05/ADD-HOUSING-01 assenti. Sono scelte della
   dimostrazione, non lo stato delle acquisizioni territoriali reali.
3. `review/observations.csv` contiene 432 slot, compresi zero e assenze:
   `not_acquired` non è zero. HTML, PDF e schede mostrano lo stesso snapshot.
4. `qa/pack.json` e `qa/hub.json` conservano i risultati degli audit.
   `run.json` lega con SHA-256 input, manifest dei prodotti e report QA;
   dichiara `source_ingestion_performed: false` e `synthetic_example_ready`.

Portale, atlante e copertine dei PDF dichiarano l'esempio sintetico; nomi
comunali e fonti identificano i dati fittizi. Gli input generati sono
deterministici; non si promette identità binaria dei PDF tra ambienti/versioni.
Tutti i prodotti mantengono `technical_draft_do_not_publish`, senza approvazione
scientifica o autorizzazione alla diffusione.

Per ripetere separatamente l'audit dal checkout:

```powershell
uv run --locked --no-dev python scripts/audit_v0_4_output_quality.py --hub work/synthetic-example-01/hub --json-out work/synthetic-example-01-audit.json
```

Il report QA deve essere nuovo ed esterno al portale. Un PASS riguarda
coerenza e integrità del pacchetto sintetico, non autenticità delle fonti,
accessibilità completa, revisione visiva o validazione scientifica.

## Ambiente separato e sviluppo

Per conservare l'ambiente esistente e provare un'installazione non modificabile,
impostare prima di `uv sync` una nuova directory per `UV_PROJECT_ENVIRONMENT`:

```powershell
$env:UV_PROJECT_ENVIRONMENT = Join-Path (Get-Location) ".venv-example"
uv sync --python 3.11 --locked --no-dev --no-editable
uv run --locked --no-dev --no-editable epah examples synthetic --out-dir work/synthetic-example-02
Remove-Item Env:UV_PROJECT_ENVIRONMENT
```

Solo questo comando dimostrativo funziona senza leggere risorse del checkout
durante la generazione. L'intero workflow territoriale richiede ancora script
e configurazioni del checkout: non viene dichiarato un'applicazione autonoma.

Il servizio è `epah_diagnosis.synthetic_example_v0_4.build(out_dir)`.
I test end-to-end chiamano lo stesso servizio, senza sostituire globalmente
l'ingestione territoriale. Il precedente export tramite
`EPAH_SYNTHETIC_QA_DIR` resta disponibile nei test per compatibilità con la QA
browser; non è necessario per usare il comando.

Per il software: [guida sviluppatore](v0_4_developer_guide.md).
Per i dati reali: [architettura](v0_4_architecture.md) e workflow `epah outputs`.
La dimostrazione non è un input sostitutivo per quel workflow e non chiude
le [decisioni scientifiche](v0_4_scientific_decisions.md).
