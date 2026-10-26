# PR G — Catalogo e matrice: migrazione additiva in anteprima

## Decisione
Il catalogo contiene ora **nove voci** con la misura ferroviaria `rail_accessibility` (`EXPERIMENTAL`, `source_registry_coverage: pending`). La definizione riguarda l'accesso stradale ai gateway ferroviari operativi e **non** deve essere confusa con la definizione storica dei poli SNAI.

Non vengono sovrascritti `data/verification_matrix.csv` o gli output precedenti. La CLI di base mantiene temporaneamente il validatore a tre indicatori: il file ampliato è una **preview**, non va passato a `validate-matrix` finché non sarà approvata la migrazione del runtime.

## Anteprima
```bash
python scripts/migrate_matrix_preview.py --output data/verification_matrix_preview.csv
```
Il comando conserva ogni campo di ogni riga esistente e aggiunge le sole coppie Comune-indicatore mancanti con `Da verificare`, valore vuoto e limiti dal catalogo. Rifiuta duplicati, Comune/ID sconosciuti, header inattesi e qualunque sovrascrittura del file di origine o di un output già esistente.

## Copertura attesa
Per lo stato osservato prima della PR: 27 Comuni × 9 voci = **243 righe**; 81 originarie + **162 nuove**. Questo conteggio è atteso, non una validazione degli indicatori aggiunti. I 54 stati validati delle righe originarie sono conservati, non ri-approvati.

## Prossimo passaggio (separato)
Collegare la CLI al catalogo, validare le 243 coppie e approvare la sostituzione della matrice solo dopo confronto/backup e test. Le pipeline `finalize_*` che assumono la matrice originaria vanno verificate prima del rilascio. Nessun nuovo indicatore è dichiarato validato dalla presente PR.
