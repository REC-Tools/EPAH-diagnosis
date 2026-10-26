# Controlli di coerenza del framework (PR E)

Eseguire offline:

```bash
python scripts/check_framework.py
pytest -q tests/test_framework_consistency.py
```

Il controllo legge il catalogo `config/indicators.json` e il source registry `config/sources.json`; non effettua download, non rigenera la matrice e non modifica file.

**Errori bloccanti:** JSON illeggibile, struttura non valida, ID duplicati o malformati, campi obbligatori mancanti, valori enumerati non ammessi, fonte referenziata sconosciuta, incoerenza dello stato delle fonti, documentazione assente.

**Warning non bloccanti:** indicatori con `source_ids: []` e copertura `pending`; schede numerate esistenti ma ancora non presenti nel catalogo (per esempio la scheda ferroviaria 09). L'integrazione delle fonti e l'ampliamento del catalogo saranno PR metodologiche distinte.

Questa PR non confronta i dati comunali né verifica i CSV generati, le formule, gli anni o i benchmark. Non modifica il runtime di `model.py` o la matrice di 81 righe. È il primo controllo automatico di integrità **strutturale**, non un certificato di qualità dei risultati.
