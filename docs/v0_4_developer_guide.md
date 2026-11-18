# Sviluppare e verificare il percorso v0.4

Leggere prima l'[architettura](v0_4_architecture.md), poi usare un checkout
con Python 3.11+ e `uv`. Gli originali locali non sono necessari per i test
sintetici. La costruzione territoriale richiede invece gli esatti input e QA.

Per vedere la catena dei prodotti senza fonti private usare l'
[esempio sintetico riproducibile](v0_4_synthetic_example.md): genera un portale
con i renderer e gli audit di produzione, marcando esplicitamente i dati fittizi.

```powershell
uv run --locked epah examples synthetic --out-dir work/synthetic-example-01
```

Il comando non richiede pytest; i test end-to-end chiamano il medesimo servizio
`synthetic_example_v0_4.build`. Aprire `hub/index.html` nella nuova destinazione.

## Installare e controllare il software

```powershell
uv sync --python 3.11 --locked --group dev
uv run --locked pytest -q
uv run --locked python scripts/check_documentation.py
uv run --locked epah --help
uv run --locked epah outputs plan --help
```

Per preservare un vecchio ambiente si può impostare `UV_PROJECT_ENVIRONMENT`
su una directory nuova prima di `uv sync`. Non alterare il lockfile per far
passare il collaudo di una modifica agli output.

### Configurazione Windows e controllo Bash

Su Windows installare Git for Windows anche per i controlli che chiamano Bash.
In PowerShell, aggiungere alla sessione la directory di Bash della propria
installazione; il percorso sotto è quello predefinito, da adattare se diverso:

```powershell
$gitBash = Join-Path $env:ProgramFiles "Git/usr/bin"
$env:Path = "$gitBash;$env:Path"
uv run --locked python -c "import shutil; print(shutil.which('bash'))"
uv run --locked pytest -q tests/test_bash_syntax.py tests/test_agent_cycle_v0_4.py
uv run --locked pytest -q
```

Il percorso mostrato deve riferirsi al Bash scelto, per esempio quello di Git
for Windows. Il solo nome `bash` passato a un processo Windows può selezionare
il launcher WSL in System32 prima del `PATH`. Non occorre installare una
distribuzione WSL per questi test; un Bash non disponibile è un errore di
configurazione, non un test saltato o superato.

Il controllo dei blocchi `run` del workflow usa `tests/bash_syntax.py`:
risolve l'eseguibile dal `PATH`, passa il percorso assoluto a `subprocess` e
invia lo script come byte UTF-8, mantenendo i terminatori originali. Usa sempre
`bash -n`: analizza la sintassi senza eseguire lo script e rifiuta ogni uscita
non zero, riportando passo, eseguibile e diagnostica. Non modifica il workflow.

**Diagnosi del difetto osservato nella PR #179:** stdin in modalità testo su
Windows trasformava LF (`0a`) in CRLF (`0d0a`). Il launcher WSL selezionato dal
nome generico rifiutava il medesimo script che Git Bash tollerava, con
`syntax error: unexpected end of file`. Il problema si riproduce anche fuori
da pytest con un blocco `if`/here-document: non richiede altri test né gli
atlanti. La chiamata difettosa era già presente prima della PR #179.

Per confrontare il vecchio comportamento, questo comando usa intenzionalmente
nome generico e stdin testuale; l'esito dipende dal Bash avviato dall'host:

```powershell
uv run --locked python -c "import subprocess; subprocess.run(['bash', '-n'], input='if true; then\ntrue\nfi\n', text=True, check=True)"
```

Le regressioni verificano i byte ricevuti da un vero processo figlio, un
here-document valido, l'assenza di esecuzione e il rifiuto di sorgenti malformati.
Un PASS Linux non certifica le capacità del filesystem Windows.

I test delle modalità Git generano gli attacchi nell'indice di una repository
sintetica: non dipendono da `chmod`. Due test richiedono davvero la creazione
di collegamenti simbolici: un probe rileva se l'host la consente. Se non la
consente, sono segnalati come saltati con motivazione, non come controlli
di sicurezza superati. Eseguirli anche su un host capace prima del rilascio.

## Pianificare il pacchetto senza costruirlo

Per riutilizzare gli input reali con un solo file locale vedere la
[chiusura tecnica parziale](v0_4_technical_closeout.md). `--inputs-file` accetta
solo percorsi dichiarativi, risolti rispetto al file; non esegue piani salvati.
I comandi individuali sotto restano compatibili.

Esempio con nomi indicativi: sostituire i percorsi con input locali verificati.
`plan` non scarica file e non crea la directory richiesta.

```powershell
uv run --locked epah outputs plan `
  --bundle work/input/pilot `
  --out-dir work/review-run-01
```

Il JSON distingue presenza degli input e possibilità di eseguire il piano.
Non dichiara validi contenuti, fonti o metodo. Il piano mostrato non è un file
di comandi eseguibile: `run` ricostruisce la catena consentita.

## Eseguire una catena completa

```powershell
uv run --locked epah outputs run `
  --bundle work/input/pilot `
  --h47-zip work/input/h47-review-schema2.zip `
  --h50-dir work/input/h50-preview `
  --h46-dir work/input/h46-preview `
  --h03-dir work/input/h03-preview `
  --h04-dir work/input/h04-preview `
  --h05-dir work/input/h05-preview `
  --housing-dir work/input/housing-preview `
  --out-dir work/review-run-02
```

`--registry` e `--release-config` sono opzionali: i valori predefiniti sono
il registro canonico e la configurazione del pilota. Nessun comando modifica
questi input. La configurazione del pilota non certifica una release v0.4.

Senza tutti i candidati, `run` si blocca prima di creare output. Per una
revisione intenzionalmente parziale aggiungere `--allow-incomplete`; le serie
non acquisite restano assenti e la ricevuta non dichiara uno snapshot completo.
Il comando non cerca fonti sostitutive né corregge ricevute obsolete.

## Interpretare il risultato

Aprire `hub/index.html` nella nuova directory di esecuzione. `run.json` contiene
stato, passi, disponibilità e hash dei manifest/audit. La cartella `logs/`
permette di individuare il primo errore; `qa/` contiene i controlli indipendenti.

| Stato | Significato |
| --- | --- |
| `running` | Esecuzione non terminata; non assumere che il pacchetto sia pronto |
| `failed` | Un passo o un controllo finale è fallito; i log sono conservati |
| `technical_review_incomplete` | Catena verificata, ma almeno una serie resta assente |
| `technical_review_ready` | Catena verificata con tutte le 16 serie presenti; revisione umana e diffusione ancora da deliberare |

La catena comprende già i due audit. Il [controllo browser](v0_4_end_to_end_qa_step9.md),
la verifica visiva, il lettore di schermo e la stampa sono passi distinti.
Il browser non viene scaricato automaticamente. Lo script supporta
`EPAH_CHROMIUM` per indicare un eseguibile Chromium/Chrome installato.

## Dove fare una modifica

- Nuovo percorso operativo: servizio applicativo e delega nella CLI;
  non duplicare calcoli dentro `workflow_cli.py`.
- Aspetto dei prodotti: renderer dedicato, mantenendo invariato lo snapshot.
  I builder atlante sono `visual_atlas_v0_3.build` e `visual_atlas_v0_4.build`
  in `epah_diagnosis`; i corrispondenti script restano comandi compatibili.
- Scrittura delle directory: riusare `directory_publication.publish_directory`;
  niente pulizie ricorsive di output precedenti.
- Errore di metodo o fonte: documentare la proposta e la decisione richiesta;
  non cambiare unità, griglia o universo per superare un controllo.

Test pertinenti: `tests/test_review_workflow_v0_4.py`,
`tests/test_directory_publication.py`, regressioni del renderer o audit interessato.
Il controllo documentazione include automaticamente le guide `docs/v0_4_*.md`.
