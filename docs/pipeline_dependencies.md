# Inventario delle dipendenze operative

Questa pagina complementa [l'audit](pipeline_audit.md): il perimetro è limitato alle dipendenze osservabili nel repository, senza esecuzioni esterne.

## Ordine logico delle fasi

```text
municipalities.csv + reference datasets + external official datasets
                     |
                     v
         indicator finalizers (independent)
                     |
               QA / benchmarks
                     |
        municipal geography / profiles
                     |
            overlap and maps
```

L'ordine è **logico** e non rappresenta una DAG automatizzata. Eseguire uno script non garantisce che un altro abbia trovato gli input richiesti.

## Prerequisiti da esplicitare in una futura orchestrazione
- `finalize_*`: elenco degli input locali e dei download richiesti; output atteso; anno e tempo di acquisizione.
- `build_municipality_profile.py`: matrice delle 27 municipalità e indicatori richiesti.
- `build_multidimensional_overlap.py`: GeoJSON comunale, indicatori baseline e benchmark disponibili.
- `generate_diagnostic_maps.py`: geometrie e tabelle per le metriche da rappresentare.
- `generate_overlap_map.py`: overlay multidimensionale già prodotto.
- `check_framework.py`: non dipende dai download; non valida i dati di output.

## Regole per futuri interventi
1. Prima inventariare i file richiesti e verificarne schema e anno.
2. Non avviare automaticamente tutti i downloader in CI: i servizi pubblici possono essere temporaneamente irraggiungibili.
3. Separare verifiche offline deterministiche e test end-to-end dipendenti dalla rete.
4. Non aggiornare `verification_matrix.csv` senza salvare i valori e gli stati precedenti.
5. Per le alternative edilizie scegliere una sola procedura canonica, documentando l'altra come legacy o fallback.
