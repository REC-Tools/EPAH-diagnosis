# Inventario locale degli artefatti EPAH

La repository include dati **canonici versionati** e numerosi input/artefatti
di lavoro che non devono essere confusi con dati approvati per la pubblicazione.

Questa procedura **non elimina, non sposta, non promuove e non modifica** alcun file.

## Controllo ordinario

Da PowerShell, nella root del repository:

~~~powershell
uv run --locked epah local audit
~~~

Per esportare un inventario in un **nuovo** JSON locale:

~~~powershell
uv run --locked epah local audit --json-out outputs/quality/local_inventory_20261105.json
~~~

Il controllo usa Git per distinguere tre stati: `untracked` (non
versionato), `ignored` (escluso dal normale staging) e
`tracked_change` (modifica a un file già versionato). Include percorsi
`data/`, `artifacts/`, `outputs/` e archivi ZIP. Le directory
ignorate sono mostrate in forma aggregata: non è un inventario esaustivo
di ogni file conservato al loro interno.

L'inventario non interpreta i CSV, non calcola un nuovo indicatore e
non certifica fonti, licenze o approvazioni. Il report contiene percorsi
locali: valutare la riservatezza prima di condividerlo.

## Regole Git mirate

La `.gitignore` esclude per impostazione predefinita:

- `data/raw/`: originali scaricati; conservare localmente con URL, hash e data.
- `data/cache/`: cache rigenerabili.
- `artifacts/`: output di lavoro e pacchetti locali non revisionati.
- `data/downloads/` e `outputs/`: già ignorati precedentemente.

**Non sono ignorati in modo generalizzato** `data/derived/`,
`data/geography/`, `data/indicators/` e `data/reference/`.
Le eventuali nuove tabelle devono rimanere visibili per revisione
scientifica, provenienza, periodo, licenza e approvazione prima del commit.
Non è stata introdotta alcuna esclusione generalizzata per `*.zip`
o per i backup di migrazione.

Per investigare una regola di esclusione:

~~~powershell
git check-ignore -v -- data/raw/tuo_file.csv
git status --short
~~~

Un file già tracciato non viene sottratto al versionamento dall'aggiunta
della relativa regola `.gitignore`. Le PR che modificano file in
`data/**` rimangono soggette alla protezione dei dati già in vigore.

## Gestione prudente degli output locali

- Conservare gli archivi originali e gli audit. Non eliminare dati con
  `git clean -fd`, `git reset --hard` o ripristini indiscriminati.
- Per dati `derived`, geometrie, nuovi indicatori e riferimenti,
  controllare fonte, anno, licenza e reproducibilità prima di proporre
  una PR dati separata.
- L'esito del controllo non cambia lo stato del pilota v0.1 né sblocca
  la pubblicazione canonica.
