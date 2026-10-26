# Audit della pipeline — stato osservato su main

## Ambito e metodo
Audit statico del repository in data 26 ottobre 2026. Ispezionati: albero Git su `main`, catalogo `config/indicators.json`, matrice `data/verification_matrix.csv`, script di finalizzazione e percorsi di output. **Nessuna pipeline o download è stata eseguita**. Di conseguenza, "script presente" non significa "funzionante" o "dato riproducibile". Gli output non tracciati potrebbero esistere localmente e non sono osservabili qui.

## Risultati sintetici
- Il catalogo contiene **8 indicatori/descrittori**. Esiste anche la scheda ferroviaria 09 e uno script di finalizzazione: non sono ancora nel catalogo.
- La matrice contiene 81 righe per 3 indicatori: 27 `Dato validato` per popolazione 65+, 27 `Dato validato` per reddito, 27 `Da verificare` per patrimonio edilizio.
- Su `main`, in `data/indicators/`, sono tracciati soltanto `income_vulnerability_2024.csv` e `income_vulnerability_benchmarks_2024.csv`.
- In `data/reference/` sono tracciati tre snapshot: clima DPR412, DEA Piemonte e gateway ferroviari Canavese.
- I 19 script in `scripts/` includono finalizzatori, generatori derivati, controlli e acquisizioni; non formano un comando unico di orchestrazione verificato.
- Alcuni script dichiarano output in `data/derived/` e `outputs/maps/`, attualmente assenti dall'albero versionato.

## Matrice di audit
| Voce | Script entrypoint | Dipendenza principale | Output dichiarato | Presenza output su main | Evidenza attuale |
| --- | --- | --- | --- | --- | --- |
| Popolazione 65+ | `finalize_population_65_plus.py` | ISTAT POSAS, download | `population_65_plus_2026.csv` + benchmark | No | 27 righe matrice `Dato validato`; ricostruzione non testata |
| Reddito | `finalize_mef_income.py` | MEF IRPEF, download | `income_vulnerability_2024.csv` + benchmark | **Sì, entrambi** | 27 righe matrice `Dato validato`; pipeline non rieseguita |
| Patrimonio edilizio | `finalize_building_stock.py`, `finalize_building_stock_single_source.py` | ISTAT CPA 2011 (e POSAS nella prima variante) | `building_stock_2011.csv` + benchmark | No | 27 righe `Da verificare`; due procedure alternative da riconciliare |
| Gradi giorno | `finalize_heating_degree_days.py` | Snapshot DPR412 versionato | `heating_degree_days.csv` + summary | No | Sorgente locale presente; script non eseguito |
| Altitudine media | `finalize_mean_altitude.py` | ISTAT altitudine, download | `mean_altitude_2021.csv` + summary | No | Script presente; download/parser non verificati |
| SNAI | `finalize_snai_classification.py` | Mappa Aree Interne, download | `snai_classification_2020.csv` + summary | No | Script presente; riproducibilità non verificata |
| DEA I/II | `finalize_dea_accessibility.py` | Confini ISTAT, matrice viaria ISTAT, snapshot DEA | `dea_accessibility_minutes.csv` + summary | No | Snapshot DEA presente; dipendenze remote |
| Polo scolastico | `finalize_upper_secondary_accessibility.py` | MIM scuole e percorsi, confini e matrice ISTAT | `upper_secondary_accessibility_minutes.csv` + summary; snapshot poli | No | Dipendenza remota MIM; successive PR di fix non sostituiscono test end-to-end |
| Ferrovia (fuori catalogo) | `finalize_rail_accessibility.py` | Gateway locali, confini e matrice ISTAT | `rail_accessibility_minutes.csv` + summary | No | Snapshot gateway presente; aggiornare catalogo solo dopo revisione |

"Output presente" riguarda esclusivamente file tracciati su `main`, non risultati locali o artefatti di workflow.

## Pipeline derivata e prodotti
| Fase | Script | Input / criticità | Output dichiarato |
| --- | --- | --- | --- |
| Confini | `acquire_municipality_boundaries.py`, `build_municipality_geojson.py` | Download e codici geografici ISTAT | Dati geografici derivati |
| Acquisizione popolazione | `acquire_istat_65plus.py` | POSAS | Output di acquisizione |
| Overlay | `build_multidimensional_overlap.py` | Indicatori e benchmark selezionati + GeoJSON comunale | `data/derived/municipality_overlap.geojson` |
| Profili comunali | `build_municipality_profile.py` | Matrice dei tre indicatori | `data/derived/municipality_profile.csv` |
| Mappe | `generate_diagnostic_maps.py`, `generate_overlap_map.py` | GeoJSON/indicatori/overlay preliminari | `outputs/maps/` |
| Integrità | `check_framework.py` | Catalogo e registro fonti | Esito errore/warning, nessun dataset |
| Fonti | `check_sources.py` | URL e versioni, accesso rete | Report/monitoraggio |

Le dipendenze sopra riportate sono ricavate per lettura statica dei moduli/import e percorsi, non da una prova completa di successo.

## Rischi da trattare prima di ampliare il tool
1. **Disallineamento di governance:** 8 voci catalogate, 9 schede numerate, 3 voci nella matrice applicativa.
2. **Riproducibilità:** molti output dichiarati non sono tracciati; manca un manifest completo per ciascun rilascio.
3. **Doppia implementazione:** due finalizzatori del patrimonio edilizio producono gli stessi file e possono sovrascriversi.
4. **Dipendenze esterne fragili:** MIM, ISTAT e MEF possono modificare URL e schemi; distinguere guasto rete da errore metodologico.
5. **Output derivati:** profili/overlay/mappe richiedono prerequisiti non assicurati automaticamente dalla CI.
6. **Stati non equivalenti:** `Dato validato` nella matrice non dimostra la presenza del CSV versionato né un test end-to-end recente.

## Proposta di sequenza successiva
- **G:** sincronizzazione additiva catalogo ↔ matrice, dopo scelta su scheda 09 e politica delle 27×N righe; preservare i valori attuali.
- **H:** definire un manifest eseguibile/prerequisiti per ogni pipeline, con opzione di esecuzione locale senza riscrivere dati validati.
- **I:** report QA e inventory di output effettivi, con verifiche di schema e copertura.
- Solo in seguito: dashboard, mappe e rapporto finale.

## Criteri per dichiarare riproducibile una pipeline
Comando documentato; fonte e vintage identificati; esecuzione riuscita in ambiente pulito; 27 codici Comune univoci; controlli di coerenza; output verificati; manifest provenienza e limiti; nessuna mutazione distruttiva. **Nessuno di questi criteri viene attestato da questo solo audit statico.**
