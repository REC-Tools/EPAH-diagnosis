# Compatibilità finalizzatori–catalogo

Questa PR uniforma **solo gli identificativi** dei quattro finalizzatori dei servizi territoriali al catalogo `config/indicators.json`:

| Script | ID precedente | ID canonico |
| --- | --- | --- |
| DEA | `dea_access_minutes` | `dea_accessibility` |
| Scuola | `upper_secondary_access_minutes` | `upper_secondary_accessibility` |
| SNAI | `snai_isolation_class` | `snai_classification` |
| Ferrovia | `rail_access_minutes` | `rail_accessibility` |

**Attenzione:** la modifica non migra eventuali CSV storici contenenti gli ID precedenti. Se presenti, vanno individuati, riconciliati e conservati prima di rigenerare output. I file attualmente tracciati in `main` non contengono queste righe nella matrice ufficiale a tre indicatori.

## Vincolo non risolto
I finalizzatori di contesto/accessibilità che aggiungono righe usano il criterio «se esiste la coppia Comune–indicatore, salta». Dopo una migrazione a 243 righe, quelle coppie esisteranno ma avranno stato `Da verificare`: **non aggiornerebbero automaticamente i valori**. Pertanto non promuovere ancora la preview a matrice ufficiale. Serve una PR successiva per distinguere una riga presente da una riga valorizzata e per scrivere in modo non distruttivo.

La CLI `validate-matrix --catalog` resta disponibile per verificare la preview; la matrice ufficiale e i suoi dati rimangono invariati.
