# Indice della documentazione — EPAH Diagnosis

**Stato corrente: v0.2.0 software stabile (solo sorgenti).** Le analisi dei 27 Comuni sono output tecnici soggetti a revisione; la v0.3 è una ricerca sperimentale non ancora canonica. Questo indice distingue guide **operative** da materiali **storici**.

## Leggere prima

| Area | Documento | Uso |
| --- | --- | --- |
| Versione e limiti | [Release v0.2.0](releases/v0.2.0.md) | Contratto del software stabile, non pubblicazione dei risultati |
| Esecuzione | [Guida operativa v0.2](operational_guide.md) | Installazione, prerequisiti, report e audit |
| Comandi | [CLI unificata](unified_cli.md) · [Riferimento script](script_reference.md) | Interfacce e funzioni correnti |
| Metodo | [Framework](framework.md) · [Catalogo indicatori](indicator_catalog.md) · [Pipeline logica](pipeline.md) | Definizioni, ruoli, limiti e interpretazioni |
| Dati | [Provenance](provenance.md) · [Contratto dei dati](data_contract.md) | Fonti, riproducibilità e QA |
| Sicurezza delle modifiche | [Protezione PR dati](data_change_protection.md) · [Governance](governance.md) | Dichiarazioni obbligatorie e decisioni umane |
| Manutenzione | [Audit script e artefatti](repository_hygiene.md) · [Inventario file locali](local_artifact_inventory.md) | Triage senza cancellazione automatica |

## Output v0.2

| Prodotto | Documentazione |
| --- | --- |
| Rapporto PDF | [Rapporto territoriale](v0_2_territorial_report.md) |
| 27 schede PDF | [Schede comunali](v0_2_municipal_sheets.md) |
| Confronti descrittivi | [Analisi multidimensionale](v0_2_multidimensional_analysis.md) |
| Dashboard HTML | [Dashboard offline](v0_2_offline_dashboard.md) |
| Pacchetto e verifiche | [Review package e audit](v0_2_review_package.md) |
| Riproducibilità | [Build riproducibile](reproducible_build.md) |

## Precedenti e sviluppo sperimentale

- **Pilota v0.1:** [procedura](v0_1_owner_accepted_release.md), [perimetro](release_v0_1_scope_27.md), [gate canonico](release_v0_1.md). Documentazione necessaria per ricostruire gli input della v0.2, ma non percorso principale di lettura.
- **v0.3 in ricerca:** [registro scientifico EPAH](v0_3_scientific_scope.md) e [candidato H47 / popolazione 0–11 anni](v0_3_population_0_11_candidate.md) con [audit indipendente ISTAT](v0_3_h47_source_reproduction_audit.md), e [candidato H50 / istruzione degli adulti](v0_3_h50_education_candidate.md) e [candidato H46 / disoccupazione 15+](v0_3_h46_unemployment_candidate.md). Questi file non dimostrano validazione di nuove osservazioni.
- **Prototipi e intake:** i file `indicator_10_*`–`indicator_15_*`, le anteprime APE, ERA5 e CIT e le relative guide documentano esperimenti; **non fanno parte** della release tecnica stabile.
- **Storia:** [archivio tecnico](archive/README.md) (inclusi audit di pipeline, migrazioni e note datate di promozione) e [review firmate](reviews/v0_1_owner_acceptance_20261030.md). Gli audit del 26–29 ottobre riportano stati **precedenti** al catalogo 9/243; non usarli come istruzioni attuali. Non cancellare le evidenze o gli originali.
