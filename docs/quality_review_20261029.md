# Quality review della repository — 29 ottobre 2026

**Ambito e metodo.** Ispezione statica della struttura `main`, delle CLI Python, della matrice, del catalogo e dei workflow GitHub. La CI su `main` al commit `077d88f7227e2befb766c5417023b5959086062f` è risultata `success` il 29/10/2026. Questo documento **non** dichiara di aver eseguito i test localmente, di aver riprodotto download delle fonti o di aver verificato approvazioni scientifiche. I workflow dipendenti dalla rete e le versioni recenti delle API restano da validare sul campo.

## Snapshot osservato

| Controllo | Evidenza | Interpretazione |
| --- | --- | --- |
| Universo canonico | 27 Comuni × 9 indicatori = 243 record in `data/verification_matrix.csv` | struttura presente |
| Stato matrice | 135 `Dato validato`, 108 `Da verificare` | copertura validata 135/243; release bloccata |
| Catalogo | 9 voci core con `methodological_maturity=EXPERIMENTAL` | una riga validata non equivale ad approvazione metodologica |
| Script | 43 file Python in `scripts/` | percorsi QA, bozza, promozione, output e legacy da distinguere |
| CI su main | Actions `CI` conclusa con successo | verifica di codice/offline, non certificazione della fonte |
| Un run PR successivo | workflow PR terminato `failure` su SHA diverso da main | da diagnosticare separatamente; non attribuire il fallimento al commit main |

## Criticità e decisioni

### P0 — non pubblicare output scientificamente incompleti

- **Release gate intenzionalmente bloccato:** 108 righe senza validazione e approvazioni metodologiche non registrate; non modificare lo stato per far passare i controlli. Produrre soltanto inventory e report di incompletezza.
- **Promozioni invasive:** `finalize_*` possono modificare `data/verification_matrix.csv` e indicatori già versionati; una conferma tecnica non prova una revisione indipendente. Per ogni promozione richiedere originale, hash, anno, QA e revisore persistente.
- **CLI di validazione:** `validate-matrix` controlla combinazioni sui nomi presenti, non è da sola prova di copertura rispetto ai 27 nomi attesi. Usare anche anagrafe, completeness e `check_v0_1_readiness.py`.

### P1 — correttezza della rappresentazione geografica

- `src/epah_diagnosis/geography.py` esporta GeoJSON CRS84 (longitudine/latitudine WGS84), pur partendo da EPSG:32632.
- `src/epah_diagnosis/release_artifacts.py` e `scripts/generate_diagnostic_maps.py` tracciano le coordinate geografiche con `ax.set_aspect("equal")`. **Gradi uguali non sono distanze uguali** alla latitudine piemontese; le proporzioni visive possono risultare alterate.
- **PR tecnica separata raccomandata:** scegliere CRS metrico di disegno (EPSG:32632), mantenere GeoJSON CRS84, riutilizzare un renderer comune e aggiungere test visivi/dimensionali su feature con buchi e multipoligoni. Non attribuire a un errore nel dato una deformazione causata dal rendering.

### P1 — tracciabilità e documentazione

- Il vecchio README accumulava note di PR e casi cronologici, senza una guida di avvio aggiornata.
- `docs/indicator_catalog.md` e altre schede conservavano testi anteriori alla migrazione 81 → 243; `docs/release_v0_1.md` descriveva in parte la build come futura quando è già presente.
- Distinguere **stato attuale** da **dossier storici**: la promozione delle 81 osservazioni ufficiali è attestata nel dossier, ma non rende completo il core.
- Inserire `scripts/check_documentation.py` per controllare offline collegamenti locali e riferimenti agli script nelle pagine operative, con esecuzione in CI. Non sostituisce una revisione editoriale.

### P2 — miglioramenti successivi

1. Esplicitare `--help` sulle CLI senza argparse o separare una CLI unificata non distruttiva.
2. Ridurre duplicazioni fra renderer legacy e builder v0.1.
3. Aggiungere test d'integrazione controllati per download, timeout e schema delle fonti esterne; CI ordinaria resta offline.
4. Aggiungere un controllo metodologico dei dati versionati, distinto da `status` e da esito unit test.
5. Convergere sui workflow di completamento mantenendo i log e la cronologia in `docs/`, senza riportare ogni PR nel README.

## Gate prima del merge

Per questa PR di documentazione/controllo: `python -m pytest -q`, `python scripts/check_documentation.py`, `python scripts/check_framework.py`, `python -m epah_diagnosis.cli validate-matrix data/verification_matrix.csv --catalog config/indicators.json`. I test con rete e i gate di release non pronti non sono condizioni di merge per una PR puramente documentale. La matrice, le evidenze di validazione e i dati ufficiali non vengono toccati.

Per i comandi riproducibili consultare [guida operativa](operational_guide.md) e [inventario script](script_reference.md).
