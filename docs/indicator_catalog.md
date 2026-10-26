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

## Confini della PR B
Questo catalogo è **strutturato ma non ancora collegato al runtime**. `src/epah_diagnosis/model.py` e `data/verification_matrix.csv` continuano a gestire solo i 3 indicatori iniziali (81 controlli = 27 Comuni x 3). Non rigenerare la matrice con il nuovo catalogo: occorre una migrazione additiva che conservi stati, periodi, valori e note esistenti.

## Questioni aperte prima dell'integrazione
1. Registrare in `config/sources.json` le fonti mancanti, con identificativi e vintage verificati.
2. Riconciliare ID di schede, funzioni, output e file effettivamente versionati.
3. La scheda `indicator_05_mean_altitude.md` discute anche l'isolamento in generale: separare la descrizione dell'altitudine dalla metodologia generale in un intervento successivo.
4. Formalizzare criteri umani per il passaggio da `EXPERIMENTAL` a `OPERATIONAL` e `VALIDATED`.
5. Non usare questo registro per creare automaticamente un indice composito o pesi.
