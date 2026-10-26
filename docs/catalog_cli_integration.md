# Validazione CLI con catalogo completo

Questa modifica aggiunge l'opzione **esplicita** `--catalog` al comando `validate-matrix` senza cambiare la logica di generazione `init-matrix` o la matrice ufficiale.

## Comandi
```bash
# Modalità originale a tre indicatori: resta compatibile con la CI
python -m epah_diagnosis.cli validate-matrix data/verification_matrix.csv

# Dopo aver generato una preview senza sovrascrivere la matrice ufficiale
python scripts/migrate_matrix_preview.py --output data/verification_matrix_preview.csv
python -m epah_diagnosis.cli validate-matrix data/verification_matrix_preview.csv --catalog config/indicators.json
```

Con i nove ID attuali, l'anteprima completa ha **243 coppie** Comune-indicatore (27 × 9). La validazione controlla stati ammessi, ID, duplicati, copertura delle combinazioni e conteggio; **non** verifica la correttezza sostanziale dei valori né certifica la fonte.

## Limiti della transizione
- Senza `--catalog` la CLI conserva i tre ID originari e valida la matrice ufficiale di 81 righe.
- La nuova opzione valida un CSV già generato; **non** modifica il file e non lo promuove automaticamente a matrice canonica.
- `init-matrix` resta deliberatamente a tre indicatori, così nessuno può distruggere accidentalmente stati o note con un comando esistente.
- Quando approveremo la migrazione definitiva, dovremo verificare i finalizzatori che scrivono la matrice.
