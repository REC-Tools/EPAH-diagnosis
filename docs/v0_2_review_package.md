# V0.2 | Pacchetto tecnico per revisione, non una release pubblica

La PR #126 crea **un dossier interno** che riunisce soltanto
artefatti già generati e sottoposti ai controlli automatici
delle PR #122–#125: rapporto, 27 schede, confronti e dashboard.

## Ordine operativo Windows

Dopo il merge ordinato delle PR #123, #124, #125 e #126,
dalla root di EPAH-diagnosis:

~~~powershell
git pull --ff-only origin main
uv run --locked pytest -q

uv run --locked epah report v0.2 --bundle outputs/v0.1.0-pilot --out-dir outputs/v0.2-territorial-technical
uv run --locked epah sheets v0.2 --bundle outputs/v0.1.0-pilot --out-dir outputs/v0.2-municipal-sheets
uv run --locked epah analysis v0.2 --bundle outputs/v0.1.0-pilot --out-dir outputs/v0.2-multidimensional-analysis
uv run --locked epah dashboard v0.2 --analysis-dir outputs/v0.2-multidimensional-analysis --bundle outputs/v0.1.0-pilot --out-dir outputs/v0.2-offline-dashboard
uv run --locked epah review-pack v0.2
~~~

Tutte le destinazioni devono essere nuove: per
rieseguire si scelgono nuove cartelle e si passano
i rispettivi percorsi a `review-pack`.

## Pacchetto generato

`outputs/v0.2-review-candidate` contiene:
- `v0_2_technical_review_only.zip` (per circolazione
  esclusivamente interna ai revisori);
- `report/`, `sheets/`, `analysis/` e `dashboard/`;
- `qa_summary_v0_2.json` e `review_package_manifest_v0_2.json`;
- `editorial_review_checklist.json` con **tutte le
  approvazioni in stato `pending`**;
- `README_REVIEW.md`.

Il programma verifica di nuovo le firme SHA-256 dei
manifest, copertura 27x9, 27 PDF di una pagina, rapporto
PDF tecnico, otto dimensioni, 28 co-occorrenze, dati e
dashboard HTML offline. Tutti i prodotti devono derivare
**dallo stesso bundle v0.1**, altrimenti non crea nulla.

## Condizioni ancora necessarie

La verifica tecnica automatica **non** approva i contenuti
scientifici e istituzionali. Prima di pubblicare o
trasmettere all'esterno, devono essere verificate da
persone responsabili: licenze, definizioni e anni,
caveat sulla privacy, resa visiva delle 27 schede e
del rapporto PDF a 150-200 DPI, coerenza della comunicazione
EPAH, approvazione dell'Unione Montana e autorizzazione finale.

Il dossier non include il CIT ancora in quarantena.
Non identifica famiglie o persone e non propone
un indice composito. Non crea automaticamente
tag Git, GitHub Release o collegamenti pubblici.

## Verifica aggiuntiva dopo il build (audit read-only)

~~~powershell
uv run --locked epah audit v0.2 --dir outputs/v0.2-review-candidate
~~~

La procedura confronta il manifest di hash con tutti i file locali e con
il contenuto byte-per-byte dello ZIP, rifiutando archivi o file in più,
corrotti o mancanti. Durante la creazione del pacchetto il builder
verifica inoltre che le statistiche JSON del rapporto siano state
ricalcolate dal pilot v0.1, che gli hash delle mappe coincidano e che
**tutti** i dati incorporati nella dashboard e nel relativo HTML coincidano
con i valori ricostruiti indipendentemente dai 27 profili.

Questo è un controllo tecnico dei file e della loro coerenza, non una
firma indipendente delle fonti né un'autorizzazione alla pubblicazione.
