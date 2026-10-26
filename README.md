# EPAH Diagnosis — Sinergie in Canavese

Toolkit per supportare una diagnosi territoriale della povertà energetica nei **27 Comuni** della Green Community Sinergie in Canavese. È uno strumento di screening con dati aggregati: **non identifica le famiglie in povertà energetica** e non produce automaticamente un indice certificato EPAH.

## Da dove iniziare
- [Framework metodologico](docs/framework.md): cinque livelli, limiti di interpretazione e regole di confronto.
- [Contratto logico della pipeline](docs/pipeline.md): fasi, qualità, provenienza e stato dei dati.
- [Criteri di completamento](docs/indicator_completion_criteria.md): quando un indicatore può essere considerato verificato.
- [Architettura di automazione](docs/automation_architecture.md): CI e monitoraggio delle fonti.
- [Catalogo metodologico](docs/indicator_catalog.md): otto voci con ruoli e maturità.
- [Schede degli indicatori](docs/): definizioni e limiti specifici.

## Stato attuale
La v0.1 registra nel modello e nella matrice operativa tre indicatori di base: popolazione di 65 anni e più (ISTAT), vulnerabilità reddituale (MEF), vetustà del patrimonio edilizio (ISTAT). Altre schede documentano misure climatiche, territoriali e di accessibilità. Il registro `config/indicators.json` raccoglie otto voci, ma **non è ancora collegato alla CLI**. Matrice e output restano da riconciliare senza eliminare le verifiche già registrate.

- `data/municipalities.csv`: elenco dei 27 Comuni.
- `data/verification_matrix.csv`: 81 righe (27 × 3), con stati aggiornati nel tempo; **non** sono tutte ancora `Da verificare`.
- `src/epah_diagnosis/model.py` e `cli.py`: definizioni correnti e verifica di base.
- `config/sources.json`: catalogo corrente delle fonti monitorate (non ancora esaustivo).
- `tests/`: test automatici.

## Uso della matrice
```bash
python -m epah_diagnosis.cli validate-matrix data/verification_matrix.csv
```
Per **rigenerare da zero** una matrice iniziale, usare il comando seguente **con un nuovo percorso di output**: non sovrascrivere la matrice operativa esistente.

```bash
python -m epah_diagnosis.cli init-matrix --municipalities data/municipalities.csv --output data/verification_matrix_new.csv
```

Stati correnti del dato: `Da verificare` → `Fonte individuata` → `Dato disponibile` → `Dato acquisito` → `Dato validato`; in caso di indisponibilità: `Non disponibile`. L'approvazione metodologica dell'indicatore è una dimensione distinta, proposta ma non ancora implementata.

## Roadmap
1. **PR A (questa PR):** principi metodologici e contratto della pipeline, soltanto documentazione.
2. **PR B (questa PR):** catalogo metodologico di otto voci, con distinzione dei ruoli; integrazione nel runtime rinviata.
3. **PR C:** contratto dei file, provenance e regole di versionamento.
4. **PR D/E:** governance delle PR e controlli di coerenza in CI.
5. Solo in seguito: razionalizzazione degli script.

Le schede degli indicatori rimangono la fonte per formule, anni e limitazioni specifiche. Le nuove convenzioni descritte qui non implicano che siano già implementate nel codice.
