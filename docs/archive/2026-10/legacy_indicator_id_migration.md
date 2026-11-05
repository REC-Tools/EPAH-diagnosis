# Legacy indicator-ID migration

> **ARCHIVIO — fotografia storica (ottobre 2026).** Le cifre, gli stati, le procedure di merge e i percorsi qui riportati descrivono una fase precedente: non sono istruzioni operative per `main`. Per il lavoro corrente consultare [la guida v0.2](../../operational_guide.md) e [il catalogo attuale](../../indicator_catalog.md). Nessuna indicazione di approvazione qui contenuta sostituisce le regole correnti.


Some local verification matrices were generated before the project standardized
service-access indicator IDs.

Legacy IDs:
- `dea_access_minutes`
- `upper_secondary_access_minutes`
- `rail_access_minutes`
- `snai_isolation_class`

Current canonical IDs:
- `dea_accessibility`
- `upper_secondary_accessibility`
- `rail_accessibility`
- `snai_classification`

Run:

```
python scripts/migrate_legacy_indicator_ids.py
python scripts/check_integrated_profile_readiness.py
```

The migration:
- rewrites only the four legacy IDs;
- preserves values, status, sources, years and notes;
- creates a one-time backup at
  `data/verification_matrix.pre_indicator_id_migration.csv`;
- refuses to write if the migration would create duplicate
  municipality/indicator pairs.
