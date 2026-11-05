# Audit degli script legacy e degli artefatti — manutenzione v0.2

**Scopo:** ridurre il debito tecnico senza rompere la v0.2.0 (software stabile), il pilota v0.1, gli audit delle fonti o i prototipi v0.3. Questo è un **inventario statico non distruttivo**, non un'autorizzazione a cancellare file.

## Risultati verificabili dell'inventario Git

Ricognizione dell'albero `main` del 5 novembre 2026, commit `c1ba742c3a3e8f10f611890d3b2bbb0a0a949167`:

| Voce | Evidenza | Azione |
| --- | --- | --- |
| Script Python tracciati in `scripts/` | **78** | Classificare prima di qualsiasi eliminazione. |
| Output generati tracciati in `outputs/`, `data/derived/`, `data/downloads/`, `data/raw/`, `data/cache/`, `artifacts/` | **0** | Non esiste una pulizia dei dati derivati *committati* da fare; quelli locali restano di proprietà dell'utente. |
| Gruppi di file dati con contenuto Git identico | **5 coppie** | Preservare fino a verifica della funzione archivistica/QA. |
| Documentazione corrente | README incentrato sulla **v0.2.0** | Non riaprire la riorganizzazione dei Markdown già svolta. |

Le cinque coppie identiche (identità byte-per-byte da SHA dell'oggetto Git, **non** duplicazioni da rimuovere automaticamente) sono:

1. `data/indicators/mean_altitude_2021.csv` e `data/reference/priority_source_archive_20261029/mean_altitude_2021.csv`;
2. `data/indicators/mean_altitude_summary_2021.csv` e `data/reference/priority_source_archive_20261029/mean_altitude_summary_2021.csv`;
3. `data/indicators/snai_classification_2020.csv` e `data/reference/priority_source_archive_20261029/snai_classification_2020.csv`;
4. `data/indicators/snai_classification_summary_2020.csv` e `data/reference/priority_source_archive_20261029/snai_classification_summary_2020.csv`;
5. `data/quality/priority_81_source_evidence.json` e `data/reference/priority_source_archive_20261029/priority_81_source_evidence_original.json`.

Le copie di archivio possono documentare la **stessa** evidenza in due momenti di validazione. Conservarle; non dedurre che un hash identico significhi file inutile.

## Esecuzione riproducibile (offline)

Dalla root della repository, con Python 3.11+ e Git:

```powershell
uv run --locked python scripts/audit_repository_hygiene.py --check
uv run --locked python scripts/audit_repository_hygiene.py --json-out outputs/quality/hygiene-snapshot-NUOVO.json
uv run --locked pytest -q tests/test_repository_hygiene.py
python scripts/check_documentation.py
```

Il secondo comando richiede che `outputs/quality/` **esista già** e che il nome scelto sia nuovo. Il JSON contiene per ogni script i riferimenti trovati e una classificazione. Il controllo `--check` fallisce solo se compaiono file **generati tracciati** nelle cartelle locali, oppure se i file testuali tracciati non sono leggibili. Non tratta l'assenza di riferimenti come errore e non elimina file. Nelle esecuzioni CI, il JSON è allegato come artefatto `repository-hygiene-audit` e consultabile senza inserirlo in Git.

Categorie di riferimento usate dall'auditor: `workflow`, `production_code`, `script_code`, `test`, `current_docs`, `historical_docs` e `configuration`. Un nome richiamato da un documento storico **non** equivale a una dipendenza di runtime. Viceversa, un comando usato manualmente fuori dalla repository potrebbe non comparire in alcun file tracciato. L'inventario è basato su riferimenti **testuali/statici** (nome `.py` e import `scripts.nome`), non su esecuzioni dinamiche, entrypoint esterni o cronologia di utilizzo.

## Script da esaminare prima di un'eventuale dismissione

Questa è una **shortlist tematica**, non una lista di script dimostrati inutilizzati:

| Famiglia | Esempi concreti | Perché non cancellare ora |
| --- | --- | --- |
| Profili e overlap precedenti alla v0.2 | `build_municipality_profile.py`, `build_municipality_comparison.py`, `build_multidimensional_overlap.py`, `generate_overlap_map.py` | Possibili usi nel replay di profili storici e nei test di compatibilità; la v0.2 usa nuovi builder. |
| Migrazioni una tantum | `migrate_matrix_preview.py`, `migrate_legacy_indicator_ids.py` | Necessarie per ricostruire conversioni pregresse; la seconda può modificare la matrice se eseguita e non va usata per pulizia. |
| Guard di sicurezza legacy | `finalize_building_stock.py` | È **volutamente disabilitato** e rifiuta una finalizzazione non approvata; rimuoverlo senza verifiche può rendere meno chiaro il percorso di errore. |
| Moduli sperimentali | `download_era5_heat_utci.py` e i finalizzatori di indicatori 10–15 | Sono distinti dalla v0.2, ma possono avere valore di riproduzione e sviluppo scientifico. |

La shortlist è basata sulla semantica degli script e sulla documentazione, **non** costituisce una diagnosi di codice morto. Per ogni candidato consultare il JSON, cercare riferimenti in `src/`, `tests/`, `.github/workflows/`, documentazione e possibili chiamate manuali, poi eseguire test e ricostruzione degli artefatti interessati. Soltanto una successiva PR mirata potrà rimuovere o trasferire script, con motivazione e piano di rollback.

## Cosa rimane protetto

- **Matrice canonica:** `data/verification_matrix.csv` e relativi stati sono invariati.
- **Originali e QA:** `data/indicators/`, `data/reference/` e `data/quality/` **non sono cartelle di cache**. Rimuoverle comporterebbe rischi per provenienza e verifiche pregresse.
- **Input/derivati locali:** `data/downloads/`, `data/raw/`, `data/cache/`, `data/derived/`, `artifacts/` e `outputs/` sono generalmente ignorati da Git. L'audit non li scandisce né li cancella.
- **Release:** nessuna variazione al bundle v0.1, comandi v0.2, CIT in quarantena o registro v0.3; nessuna promozione o indice composito.

Questo controllo integra [l'inventario degli artefatti locali](local_artifact_inventory.md), che guarda invece i file ignorati/non tracciati dell'utente, senza rimuoverli. I due audit hanno scopi complementari.
