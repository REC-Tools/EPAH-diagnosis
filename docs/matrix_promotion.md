# PR L — Promozione controllata della matrice a 9 indicatori

Il catalogo comprende 9 voci per 27 Comuni: **243 coppie Comune–indicatore**.

## Evidenza della migrazione
- Matrice precedente: 81 osservazioni, conservate senza cambiare ordine o contenuto in `data/reference/verification_matrix_baseline_81.csv`.
- Matrice aggiornata: prime 81 righe conservate con gli stessi valori, stati, anni e note; 162 nuove righe inserite solo in stato `Da verificare` con valori vuoti.
- Tutti i 54 valori precedentemente `Dato validato` restano invariati. **Non sono state effettuate nuove validazioni dei dati**.
- Nessuno script di download è stato eseguito.

## Verifiche automatiche
```bash
pytest -q tests/test_matrix_promotion.py
python -m epah_diagnosis.cli validate-matrix data/verification_matrix.csv --catalog config/indicators.json
# Controllo della vecchia matrice nella modalità a tre indicatori:
python -m epah_diagnosis.cli validate-matrix data/reference/verification_matrix_baseline_81.csv
```

Il workflow CI usa il comando con `--catalog`; la modalità CLI senza opzione resta legacy e serve per la baseline storica. `init-matrix` continua a creare soltanto la matrice di 3 indicatori: **non usare il suo output per sostituire la matrice principale**. Un futuro intervento dovrà rendere il comando di inizializzazione coerente con il catalogo.

## Limitazioni
La creazione delle 162 righe non implica che le nuove misure siano disponibili o verificate. Gli aggiornamenti successivi devono avvenire tramite finalizzatori verificati, con QA e provenance per ogni indicatore. Non presentare le 243 righe come 243 valori convalidati.
