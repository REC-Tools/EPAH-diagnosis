# Indice della documentazione — EPAH Diagnosis

**Stato corrente: v0.3.0 software stabile (solo sorgenti).** Le analisi dei 27 Comuni sono output tecnici soggetti a revisione; i candidati v0.3 hanno pipeline stabili ma non sono canonici né approvati. Ogni documento della cartella compare **una sola volta** in questo indice, nella sezione che ne descrive l'uso.

## 1. Leggere prima

| Area | Documento | Uso |
| --- | --- | --- |
| Versione e limiti | [Release v0.3.0](releases/v0.3.0.md) · [Release v0.2.0](releases/v0.2.0.md) | Contratto del software stabile, stato dei candidati, non pubblicazione dei risultati |
| Ricerca v0.3 | [Registro scientifico EPAH](v0_3_scientific_scope.md) | 56 indicatori e 35 fonti; differenza tra esito diretto, proxy e descrittore |
| Mappe v0.3 | [Atlante esplorativo](v0_3_visual_atlas.md) | Generare mappe e grafici dei 9 indicatori pilota e dei candidati |
| Sviluppo v0.4 | [Revisione tecnica e roadmap](v0_4_review_and_roadmap.md) | Difetti riprodotti, correzioni, candidati prioritari e miglioramenti degli output; proposta, non release |
| Output integrati v0.4 (Step 2) | [Portale offline, sintesi PDF e CSV](v0_4_output_hub_step2.md) | Atlante navigabile come prodotto principale, rapporto tecnico e audit sullo stesso snapshot; solo anteprima |
| Prossimi passi | [Percorso in dieci passi](v0_4_ten_steps.md) | Armonizzazione EPAH, mappe, grafici, scenari aggregati sperimentali, pulizia e assistente Codex persistente |
| Output v0.4 (Step 3) | [Schede comunali A4, 2 pagine](v0_4_municipal_sheets_step3.md) | 27 profili PDF, un volume da 54 pagine e indice nel portale offline; non pubblicabili |
| Esecuzione | [Guida operativa](operational_guide.md) | Installazione, prerequisiti, report e audit |
| Comandi | [CLI unificata](unified_cli.md) · [Riferimento script](script_reference.md) | Interfacce e funzioni correnti |
| Metodo | [Framework](framework.md) · [Catalogo indicatori](indicator_catalog.md) · [Pipeline logica](pipeline.md) | Definizioni, ruoli, limiti e interpretazioni |
| Dati | [Provenance](provenance.md) · [Contratto dei dati](data_contract.md) | Fonti, riproducibilità e QA |
| Governance | [Governance](governance.md) · [Protezione PR dati](data_change_protection.md) | Dichiarazioni obbligatorie e decisioni umane |

## 2. Indicatori candidati v0.3

Gli ID `H..` sono riferimenti interni all'inventario dell'EPAH Handbook, non codici ufficiali EPAH. Nessun candidato è nel catalogo canonico.

| ID | Candidato | Documenti | Stato dei dati |
| --- | --- | --- | --- |
| H47 | Residenti 0–11 anni | [Pipeline](v0_3_population_0_11_candidate.md) · [Audit di riproduzione ISTAT](v0_3_h47_source_reproduction_audit.md) | Anteprima reale 27/27, riprodotta in modo indipendente |
| H50 | Adulti 25–64 senza licenza media | [Pipeline, normalizzazione e audit](v0_3_h50_education_candidate.md) | Anteprima reale 27/27, audit PASS |
| H46 | Disoccupazione 15+ | [Definizione e contratto](v0_3_h46_unemployment_candidate.md) · [Acquisizione, normalizzazione e audit](v0_3_h46_official_normalization_and_independent_audit.md) | Anteprima reale 27/27, audit PASS |
| H03 | HDD climatici annui 2025 | [Calcolo](v0_3_h03_annual_hdd_candidate.md) · [Estrazione NetCDF ARPA](v0_3_h03_nwioi_netcdf_extraction.md) | Solo pipeline |
| H04, H05, ADD-HOUSING-01 | CDD, APE residenziali F/G, abitazioni non occupate da residenti | [Nomenclatura armonizzata e contratti](v0_3_epah_harmonized_three_candidates.md) | Solo pipeline |

Collegamento con i nove indicatori esistenti: [crosswalk editoriale EPAH](v0_3_epah_editorial_crosswalk.md).

## 3. Prodotti v0.2 (rapporto, schede, dashboard)

| Prodotto | Documentazione |
| --- | --- |
| Rapporto PDF | [Rapporto territoriale](v0_2_territorial_report.md) · [Specifica del PDF](report_pdf_epah_v0_2_spec.md) |
| 27 schede PDF | [Schede comunali](v0_2_municipal_sheets.md) |
| Confronti descrittivi | [Analisi multidimensionale](v0_2_multidimensional_analysis.md) · [Serie coincidenti](v0_2_identical_indicators_review.md) |
| Mappe | [Scale delle mappe v0.2](v0_2_map_scales.md) · [Mappe diagnostiche](diagnostic_maps.md) |
| Dashboard HTML | [Dashboard offline](v0_2_offline_dashboard.md) |
| Pacchetto e verifiche | [Review package e audit](v0_2_review_package.md) |
| Riproducibilità | [Build riproducibile](reproducible_build.md) · [Checkout CSV su Windows](windows_csv_checkout.md) |

## 4. I nove indicatori canonici

| # | Indicatore | Documento |
| --- | --- | --- |
| 01 | Popolazione 65+ | [Scheda](indicator_01_population_65_plus.md) |
| 02 | Vulnerabilità reddituale | [Scheda](indicator_02_income_vulnerability.md) · [Protocollo di validazione](indicator_02_validation_protocol.md) |
| 03 | Patrimonio edilizio | [Scheda](indicator_03_building_stock.md) · [Procedura canonica](building_stock_finalization.md) · [Audit fonte CPA 2011](building_stock_source_audit.md) |
| 04 | Gradi-giorno normativi | [Scheda](indicator_04_heating_degree_days.md) |
| 05 | Altitudine media | [Scheda](indicator_05_mean_altitude.md) |
| 06 | Classificazione SNAI | [Scheda](indicator_06_snai_isolation.md) |
| 07 | Accessibilità DEA I/II | [Scheda](indicator_07_dea_accessibility.md) · [QA](dea_accessibility_qa.md) |
| 08 | Accessibilità scuola superiore | [Scheda](indicator_08_upper_secondary_accessibility.md) |
| 09 | Accessibilità ferroviaria | [Scheda](indicator_09_rail_accessibility.md) |

Criteri e controlli comuni: [completamento e validazione](indicator_completion_criteria.md), [coerenza del framework](framework_consistency_checks.md), [aggiornamenti sicuri della matrice](matrix_safe_updates.md), [confini comunali](geography.md), [acquisizione originali di accessibilità](accessibility_original_source_intake.md).

## 5. Pilota v0.1 e pipeline canonica

- [Procedura del pilota](v0_1_owner_accepted_release.md), [perimetro dei 27 Comuni](release_v0_1_scope_27.md), [gate canonico](release_v0_1.md), [approvazioni umane](human_approval_workflow_v0_1.md).
- Controlli: [preflight degli input](pilot_input_preflight.md), [rotte campione](v0_1_pilot_route_samples.md), [pipeline tecnica automatizzata](automated_technical_pipeline.md).
- Completezza: [report](completeness_report.md), [esportazione CSV/Excel](completeness_export.md).

Documentazione necessaria per ricostruire gli input della v0.2, ma non percorso principale di lettura.

## 6. Prototipi e intake (non fanno parte della release)

Esperimenti di indicatori e fonti, conservati per riproducibilità e sviluppo futuro:

- Indicatori 10–15: [APE F/G tutte le destinazioni](indicator_10_ape_fg_all_uses.md), [carenza impianti di riscaldamento](indicator_10_heating_facilities_gap.md), [prestazione APE SIPEE](indicator_11_sipee_ape_performance.md), [gradi-giorno di raffrescamento](indicator_12_cooling_degree_days.md), [giorni di stress termico](indicator_13_heat_stress_days.md), [mix dei combustibili](indicator_14_heating_fuel_mix.md), [accessibilità economica dell'energia](indicator_15_local_energy_affordability.md).
- APE e SIPEE: [anteprima APE nel report](v0_2_ape_pdf_preview.md), [specifica di estrazione SIPEE](sipee_extraction_specification.md).
- CIT Piemonte (**in quarantena**): [indicatori CIT](v0_2_piemonte_cit_indicators.md), [anteprima tecnica](v0_2_cit_technical_preview.md), [schemi CSV osservati](v0_2_cit_actual_wide_source_schemas.md), [confronto su 26/27 Comuni](v0_2_cit_26town_quality_review.md), [dossier Pont Canavese](cit_source_review_packet.md).
- [Roadmap degli indicatori v0.2](v0_2_epah_indicator_research.md), superata dal registro v0.3.

## 7. Storia, revisioni datate e manutenzione

Documenti datati che descrivono lo stato **di quel giorno**: non usarli come istruzioni attuali.

- Revisioni delle fonti: [CPA 2011, 29 ottobre](building_2011_source_review_20261029.md), [bozze di accessibilità, 30 ottobre](accessibility_candidate_review_20261030.md), [DEA Piemonte vs Ministero 2025, 30 ottobre](dea_2025_ministry_reconciliation_20261030.md), [recupero delle 81 osservazioni prioritarie](priority_81_evidence_recovery.md), [audit delle tre fonti prioritarie](priority_source_audit.md).
- Manutenzione: [audit di script e artefatti](repository_hygiene.md), [inventario dei file locali](local_artifact_inventory.md).
- [Archivio tecnico](archive/README.md) (audit di pipeline, migrazioni, note di promozione) e [review firmate](reviews/v0_1_owner_acceptance_20261030.md). Gli audit del 26–29 ottobre riportano stati **precedenti** al catalogo 9/243. Non cancellare le evidenze o gli originali.
