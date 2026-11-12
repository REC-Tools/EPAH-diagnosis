# Script — guida rapida

Questa cartella contiene tutti i comandi Python del progetto, in un'unica lista piatta: i nomi non cambiano perché workflow, CLI `epah`, test e documentazione li richiamano per percorso. Qui sono **raggruppati per uso**. Ogni script si esegue dalla root del repository con:

```powershell
uv run --locked python scripts/<nome_script>.py --help
```

Per i flussi completi vedere la [guida operativa](../docs/operational_guide.md) e il [riferimento comandi](../docs/script_reference.md). Nessuno script cancella dati originali; quelli che scrivono output richiedono una cartella **nuova**.

## 1. Atlante e candidati v0.3

| Script | Candidato | Ruolo |
| --- | --- | --- |
| `build_v0_3_visual_atlas.py` | tutti | **Mappe e grafici**: atlante HTML offline, 9 indicatori pilota + candidati forniti |
| `check_v0_3_evidence.py`, `import_v0_3_evidence.py` | registro | Controllo e import dell'inventario EPAH (56 indicatori, 35 fonti) |
| `check_posas_2026_source_v0_3.py`, `prepare_population_0_11_v0_3.py`, `audit_posas_h47_reproduction_v0_3.py` | H47 | QA della fonte POSAS, anteprima, riproduzione indipendente |
| `normalize_h50_istat_sdmx_v0_3.py`, `prepare_low_education_25_64_v0_3.py`, `audit_h50_istat_independent_v0_3.py` | H50 | Normalizzazione dall'export ISTAT, anteprima, audit indipendente |
| `acquire_h46_istat_sdmx_v0_3.py`, `normalize_h46_istat_sdmx_v0_3.py`, `prepare_unemployment_15_plus_v0_3.py`, `audit_h46_istat_independent_v0_3.py` | H46 | Download SDMX, normalizzazione, anteprima, audit indipendente |
| `extract_nwioi_hdd_2025_v0_3.py`, `prepare_hdd_eurostat_2025_v0_3.py` | H03 | Estrazione da NetCDF ARPA, HDD annui |
| `prepare_cdd_eurostat_2025_v0_3.py` | H04 | CDD annui sugli stessi dati giornalieri |
| `prepare_v0_3_housing_candidates.py` | H05, ADD-HOUSING-01 | APE residenziali F/G, abitazioni non occupate da residenti |

## 1-bis. Output tecnici v0.4 (non release)

| Script | Ruolo |
| --- | --- |
| `build_v0_4_visual_atlas.py` | Estensione tecnica a 16 slot, senza promozioni canoniche |
| `build_v0_4_review_pack.py` | Fascicolo HTML/CSV/PDF coerente dallo stesso atlante |
| `build_v0_4_output_hub.py` | **Step 2**: portale offline + sintesi PDF 2 pagine + atlante, fascicolo e schede |
| `build_v0_4_municipal_sheets.py` | **Step 3**: 27 schede comunali A4 di 2 pagine e volume unico da 54 pagine |

## 2. Prodotti v0.2 (richiamati anche dalla CLI `epah`)

| Script | Comando `epah` | Ruolo |
| --- | --- | --- |
| `build_v0_2_territorial_report.py` | `epah report v0.2` | Rapporto PDF tecnico |
| `build_v0_2_municipality_sheets.py` | `epah sheets v0.2` | 27 schede comunali PDF |
| `build_v0_2_multidimensional_analysis.py` | `epah analysis v0.2` | 28 confronti descrittivi |
| `build_v0_2_dashboard.py` | `epah dashboard v0.2` | Dashboard HTML offline |
| `build_v0_2_review_package.py`, `check_v0_2_review_package.py` | `epah review-pack v0.2`, `epah audit v0.2` | Pacchetto di revisione e audit |

## 3. Gate di release (solo lettura)

| Script | Ruolo |
| --- | --- |
| `check_v0_3_release.py` | Contratto della release software v0.3.0 |
| `check_v0_2_stable_release.py`, `check_v0_2_source_release.py` | Gate storici di v0.2.0 e v0.2.0-rc1 |

## 4. Pilota v0.1 e base canonica 27 × 9

| Gruppo | Script |
| --- | --- |
| Build e prontezza | `build_v0_1_owner_accepted.py`, `build_v0_1_bundle.py`, `check_v0_1_readiness.py`, `summarize_v0_1_progress.py`, `prepare_v0_1_review_packets.py`, `check_pilot_inputs.py`, `check_pilot_replay.py`, `check_integrated_profile_readiness.py` |
| Profilo, geometrie, provenance | `build_municipality_profile.py`, `build_municipality_geojson.py`, `write_provenance.py`, `generate_diagnostic_maps.py` (mappe storiche, sostituite dall'atlante) |
| Acquisizione | `acquire_accessibility_inputs.py`, `acquire_istat_65plus.py`, `acquire_municipality_boundaries.py` |
| Preparazione bozze | `prepare_building_stock.py`, `prepare_dea_accessibility.py`, `prepare_education_rail_access.py`, `prepare_territorial_context.py`, `compare_dea_2025_drafts.py`, `verify_heating_degree_days.py` |
| QA delle fonti | `audit_priority_sources.py`, `audit_dea_2025_source.py`, `audit_building_stock_source.py`, `audit_accessibility_candidates.py`, `audit_v0_1_pilot_route_samples.py`, `audit_v0_1_dea_national_coverage.py` |
| **Promozione protetta** (può modificare matrice e CSV canonici, richiede approvazioni) | `finalize_population_65_plus.py`, `finalize_mef_income.py`, `finalize_building_stock_single_source.py`, `finalize_heating_degree_days.py`, `finalize_mean_altitude.py`, `finalize_snai_classification.py`, `finalize_dea_accessibility.py`, `finalize_upper_secondary_accessibility.py`, `finalize_rail_accessibility.py` |
| Disabilitato di proposito | `finalize_building_stock.py` (rifiuta la finalizzazione; usare `finalize_building_stock_single_source.py`) |

## 5. Prototipi (fuori dalla release)

| Gruppo | Script |
| --- | --- |
| Indicatori 10–15 | `finalize_cooling_degree_days.py`, `finalize_heat_stress_days.py`, `finalize_heating_facilities_gap.py`, `finalize_heating_fuel_mix.py`, `finalize_local_energy_affordability.py`, `finalize_sipee_ape_performance.py`, `download_era5_heat_utci.py`, `download_era5_land_daily_temperature.py` |
| APE Piemonte | `prepare_piemonte_ape_fg.py`, `build_v0_2_ape_preview.py` |
| CIT Piemonte (**in quarantena**) | `prepare_piemonte_cit.py`, `prepare_piemonte_cit_wide.py`, `inspect_piemonte_cit.py`, `build_v0_2_cit_preview.py`, `build_v0_2_cit_quarantine_comparison.py`, `build_cit_source_review_packet.py` |

## 6. Controlli del repository e manutenzione

| Script | Ruolo |
| --- | --- |
| `check_documentation.py`, `check_framework.py`, `check_municipality_registry.py`, `check_sources.py` | Link della documentazione, catalogo, registro dei 27 Comuni, fonti |
| `check_pr_data_guard.py`, `check_source_csv_checkout.py` | Protezione dei dati nelle PR, integrità dei CSV su Windows |
| `audit_repository_hygiene.py`, `audit_local_artifacts.py` | Inventario non distruttivo di script e file locali |
| `report_completeness.py`, `export_completeness.py` | Completezza della matrice |
| `migrate_legacy_indicator_ids.py`, `migrate_matrix_preview.py` | Migrazioni storiche: **non** usare sulla matrice attuale |

Le tre anteprime storiche di confronto e overlap sono in [`legacy/`](legacy/README.md).
