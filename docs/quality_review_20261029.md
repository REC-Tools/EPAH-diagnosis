# Quality review della repository — 29 ottobre 2026

**Ambito e metodo.** Ispezione statica della struttura `main`, delle CLI Python, della matrice, del catalogo e dei workflow GitHub. **Aggiornamento:** dopo le PR #80 e #82, lo stato e i gate sono cambiati; il riepilogo seguente descrive il main osservato dopo questi merge. La CI su `main` al commit `077d88f7227e2befb766c5417023b5959086062f` è risultata `success` il 29/10/2026. Questo documento **non** dichiara di aver eseguito i test localmente, di aver riprodotto download delle fonti o di aver verificato approvazioni scientifiche. I workflow dipendenti dalla rete e le versioni recenti delle API restano da validare sul campo.

## Snapshot osservato

| Controllo | Evidenza | Interpretazione |
| --- | --- | --- |
| Universo canonico | 27 Comuni × 9 indicatori = 243 record in `data/verification_matrix.csv` | struttura presente |
| Stato matrice | 54 `Dato validato`, 27 `Dato acquisito`, 162 `Da verificare` | copertura validata 54/243; release bloccata |
| Catalogo | 9 voci core con `methodological_maturity=EXPERIMENTAL` | una riga validata non equivale ad approvazione metodologica |
| Script | 45 file Python in `scripts/` | percorsi QA, bozza, promozione, output e legacy da distinguere |
| CI su main | il workflow sul commit `0a73a58` è fallito nel passaggio `Run tests` | controllare i test della documentazione e gli altri controlli; non equivale a fallimento scientifico |
| Un run PR successivo | workflow PR terminato `failure` su SHA diverso da main | da diagnosticare separatamente; non attribuire il fallimento al commit main |

## Criticità e decisioni

### P0 — non pubblicare output scientificamente incompleti

- **Release gate intenzionalmente bloccato:** 162 righe da verificare e 27 acquisite non approvate e approvazioni metodologiche non registrate; non modificare lo stato per far passare i controlli. Produrre soltanto inventory e report di incompletezza.
- **Promozioni invasive:** `finalize_*` possono modificare `data/verification_matrix.csv` e indicatori già versionati; una conferma tecnica non prova una revisione indipendente. Per ogni promozione richiedere originale, hash, anno, QA e revisore persistente.
- **CLI di validazione:** `validate-matrix` controlla combinazioni sui nomi presenti, non è da sola prova di copertura rispetto ai 27 nomi attesi. Usare anche anagrafe, completeness e `check_v0_1_readiness.py`.

### P1 — cartografia corretta nella PR #80

- Il GeoJSON resta CRS84 (lon/lat WGS84), mentre il rendering PNG avviene in EPSG:32632, con rapporto 1:1 in metri.
- La [PR #80](https://github.com/REC-Tools/EPAH-diagnosis/pull/80) ha consolidato i renderer, introdotto il supporto a fori e multipoligoni e aggiunto test sintetici. **Non occorre ripetere questo refactor.**
- **Attenzione al diff della PR #80:** oltre alla cartografia, ha riportato 81 osservazioni prima promosse allo stato non approvato e rimosso CSV/dossier/hash di evidenza; ciò contrasta con la dichiarazione di PR che non sarebbero stati modificati dati e matrice. Gli artefatti originali sono recuperati nell'[archivio tecnico](priority_81_evidence_recovery.md), senza ripromuovere alcun dato. La #79 non registra review GitHub: occorrono evidenze originali e approvazione effettiva prima della promozione.

### P1 — tracciabilità e documentazione

- Il vecchio README accumulava note di PR e casi cronologici, senza una guida di avvio aggiornata.
- `docs/indicator_catalog.md` e altre schede conservavano testi anteriori alla migrazione 81 → 243; `docs/release_v0_1.md` descriveva in parte la build come futura quando è già presente.
- Distinguere **stato attuale** dallo storico: la PR #79 proponeva/promuoveva 81 osservazioni; la successiva PR #80 ne ha annullato gli stati. Il materiale conservato nell'[archivio tecnico](priority_81_evidence_recovery.md) permette verifiche ripetibili, **non** equivale a una validazione corrente.
- `scripts/check_documentation.py` controlla offline collegamenti locali e riferimenti agli script nelle pagine operative. Il merge concorrente di #80 e #82 ha lasciato due link al dossier rimosso, intercettati da questo controllo. Correggere i link senza disabilitare il test.

### P2 — miglioramenti successivi

1. Esplicitare `--help` sulle CLI senza argparse o separare una CLI unificata non distruttiva.
2. Mantenere un unico renderer e controllare la compatibilità dei vecchi wrapper, come impostato nella PR #80.
3. Aggiungere test d'integrazione controllati per download, timeout e schema delle fonti esterne; CI ordinaria resta offline.
4. Aggiungere un controllo metodologico dei dati versionati, distinto da `status` e da esito unit test.
5. Convergere sui workflow di completamento mantenendo i log e la cronologia in `docs/`, senza riportare ogni PR nel README.

## Gate prima del merge

Per questa PR di documentazione/controllo: `python -m pytest -q`, `python scripts/check_documentation.py`, `python scripts/check_framework.py`, `python -m epah_diagnosis.cli validate-matrix data/verification_matrix.csv --catalog config/indicators.json`. I test con rete e i gate di release non pronti non sono condizioni di merge per una PR puramente documentale. La matrice, le evidenze di validazione e i dati ufficiali non vengono toccati.

Per i comandi riproducibili consultare [guida operativa](operational_guide.md) e [inventario script](script_reference.md).
