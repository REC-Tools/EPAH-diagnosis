# Archivio tecnico — ottobre 2026

Questi documenti sono fotografie **storiche, non operative**. Numeri, stati di review e istruzioni di pipeline possono essere superati dalla **v0.2.0 stabile come software**; non descrivono necessariamente la situazione di `main` oggi.

- [Audit generale del 26 ottobre](2026-10/repository_quality_audit.md)
- [Quality review del 29 ottobre](2026-10/quality_review_20261029.md)
- [Preflight nazionale del 30 ottobre](2026-10/release_scientific_blockers_20261030.md)

Per lavorare usare [README](../../README.md), [guida operativa](../operational_guide.md) e [release pilota](../v0_1_owner_accepted_release.md). I file di evidenza in data/ e docs/reviews/ non sono stati modificati.

## Note di PR e prototipi precedenti alla v0.2 stabile

Le seguenti schede erano nella root di `docs/` e sono state archiviate perché descrivono transizioni, pipeline legacy o stati poi superati. **Non sono procedure correnti**, ma restano consultabili per la tracciabilità storica:

- [Migrazione storica della matrice a nove voci](2026-10/matrix_promotion.md).
- [Profilo comunale a tre indicatori](2026-10/municipality_profile.md).
- [Primo profilo integrato](2026-10/integrated_municipality_profile.md).
- [Vecchia tabella di confronto](2026-10/municipality_comparison.md).
- [Precedente overlapping a tre proxy](2026-10/multidimensional_overlap.md).
- [Storico dei controlli HDD e del patrimonio](2026-10/indicator_04_completion_status.md).

Tre note di implementazione intermedia (`automation_architecture.md`, `catalog_cli_integration.md`, `matrix_alignment.md`) sono state rimosse dall'albero corrente perché descrivevano come futuri passaggi già completati. Rimangono recuperabili nella cronologia Git. La documentazione operativa corrente è nell'[indice](../index.md).

## Audit di pipeline e migrazioni (versioni precedenti alla v0.2)

Questi file restano recuperabili come evidenza del percorso di sviluppo, **non sono guide eseguibili correnti**:

- [Audit statico della pipeline del 26 ottobre 2026](2026-10/pipeline_audit.md) — fotografa 8 indicatori, 81 righe e 19 script di allora; **ora il catalogo comprende 9 voci e la matrice 243 righe**.
- [Inventario storico delle dipendenze](2026-10/pipeline_dependencies.md) — DAG logica pre-orchestrazione v0.2.
- [Allineamento originario degli ID dei finalizzatori](2026-10/finalizer_id_alignment.md) — migrazione dei nomi già avvenuta.
- [Procedura storica di migrazione degli ID](2026-10/legacy_indicator_id_migration.md) — lo script può scrivere nella matrice canonica: **non eseguirlo come manutenzione corrente**.
- [Dossier di promozione delle 81 osservazioni del 29 ottobre](2026-10/priority_81_promotion_20261029.md) — le istruzioni originali sulle review GitHub non costituiscono una regola attuale. Fare riferimento alla [protezione PR aggiornata](../data_change_protection.md).

Per la pipeline corrente usare [guida operativa v0.2](../operational_guide.md), [contratto logico](../pipeline.md), [contratto dati](../data_contract.md) e [catalogo](../indicator_catalog.md).
