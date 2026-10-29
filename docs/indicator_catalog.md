# Catalogo metodologico degli indicatori

Il registro [`config/indicators.json`](../config/indicators.json) è il riferimento metodologico proposto per gli **nove indicatori/descrittori documentati**. Non attribuisce a tutte le voci lo status di indicatori diretti di povertà energetica.

| ID | Ruolo | Dimensione |
| --- | --- | --- |
| `population_65_plus` | vulnerability | demographic |
| `income_vulnerability` | vulnerability | economic |
| `old_building_stock` | vulnerability | housing |
| `heating_degree_days` | context | climate_energy |
| `mean_altitude` | context | territorial |
| `snai_classification` | context | accessibility |
| `dea_accessibility` | accessibility | accessibility |
| `upper_secondary_accessibility` | accessibility | accessibility |
| `rail_accessibility` | accessibility | accessibility |

## Semantica dei campi
- `id`: identificatore stabile (snake_case), da cambiare solo con migrazione esplicita.
- `role`: `vulnerability` = proxy di vulnerabilità; `context` = contesto territoriale/climatico; `accessibility` = tempo di accesso ai servizi.
- `dimension`: gruppo diagnostico per report e mappe, non uno score.
- `interpretation_direction`: `higher` indica un potenziale aggravio all'aumentare del valore; `contextual` e `ordinal_contextual` non autorizzano una normalizzazione automatica. Non è una diagnosi familiare.
- `methodological_maturity`: `PROPOSED`, `EXPERIMENTAL`, `OPERATIONAL`, `VALIDATED`, `RETIRED`. Tutte le voci sono prudentemente `EXPERIMENTAL` finché non esiste una revisione metodologica esplicita. Questo **non** altera gli stati già validati nella matrice.
- `source_ids`: chiavi del registro `config/sources.json`; array vuoto significa **fonte da registrare nel source monitor**, non assenza della fonte ufficiale.
- `definition`, `unit`, `documentation`, `caveat`: base descrittiva, riferimento alla scheda e principali limitazioni.

## Stato attuale dell'integrazione

Il catalogo è collegato alle CLI canoniche e alla matrice a **243 righe** (27 Comuni × 9 dimensioni); la precedente matrice a 81 righe resta come baseline storica in `data/reference/verification_matrix_baseline_81.csv`. `src/epah_diagnosis/model.py` conserva un elenco legacy a tre indicatori per compatibilità con vecchie API; usare sempre `config/indicators.json` per i nuovi controlli. `init-matrix` crea solo una matrice nuova e non deve sovrascrivere `data/verification_matrix.csv`. La maturità metodologica rimane distinta dallo stato di ogni osservazione.

## Questioni aperte prima dell'integrazione
1. Registrare in `config/sources.json` le fonti mancanti, con identificativi e vintage verificati.
2. Riconciliare ID di schede, funzioni, output e file effettivamente versionati.
3. La scheda `indicator_05_mean_altitude.md` discute anche l'isolamento in generale: separare la descrizione dell'altitudine dalla metodologia generale in un intervento successivo.
4. Formalizzare criteri umani per il passaggio da `EXPERIMENTAL` a `OPERATIONAL` e `VALIDATED`.
5. Non usare questo registro per creare automaticamente un indice composito o pesi.
