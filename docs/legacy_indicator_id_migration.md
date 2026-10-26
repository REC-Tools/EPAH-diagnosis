# Legacy indicator-ID migration

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
