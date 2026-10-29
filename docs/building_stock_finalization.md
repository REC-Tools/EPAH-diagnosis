# Patrimonio edilizio — procedura canonica e controlli

## Scelta operativa
Usare **`scripts/finalize_building_stock_single_source.py`** come finalizzatore primario, basato sullo ZIP ufficiale ISTAT CPA 2011. L'alternativa `finalize_building_stock.py` dipende anche da ISTAT POSAS per associare i codici comunali; rimane legacy/fallback e **non deve essere eseguita nello stesso ciclo** perché scrive sugli stessi output.

## Controlli aggiunti
- I 27 nomi devono essere trovati nell'archivio e mappati a **27 codici comunali distinti**.
- Il parsing deve restituire **27 record territoriali**, non un sottoinsieme.
- La componente Piemonte del benchmark non può essere vuota.
- L'aggiornamento della matrice avviene attraverso l'upsert condiviso, con controllo di chiavi duplicate e sostituzione atomica del CSV. Il resto degli indicatori non viene aggiornato.

## Prima di dichiarare 'Dato validato'
1. Salvare checksum SHA-256, URL, data di download e licenza dello ZIP fonte.
2. Eseguire il finalizzatore in ambiente controllato, confrontando copertura, classi E3 ed E8–E12, e benchmark ponderati.
3. Verificare la coerenza dei risultati per un campione di Comuni con i dati ISTAT.
4. Archiviare report e provenance; approvare l'aggiornamento della matrice.

Il presente intervento **non scarica** la fonte e non aggiunge valori edilizi: tutte le 27 osservazioni restano da verificare fino all'esecuzione documentata. La procedura scrive gli output indicatori prima di completare l'upsert; non offre transazione atomica multi-file.

## PR-04: acquisizione offline e pubblicazione sotto revisione (2026-10-29)

La precedente procedura aggiorna direttamente la matrice senza dimostrare che
la fonte originaria sia stata verificata. Il percorso legacy
`scripts/finalize_building_stock.py` e stato disabilitato, e il finalizzatore
canonico ora richiede un'evidenza esplicita di revisione indipendente.

### Fase 1 - preparazione (non distruttiva)

Scaricare manualmente il file ISTAT CPA 2011 dalla [pagina ufficiale](
https://www.istat.it/notizia/basi-territoriali-e-variabili-censuarie/),
oppure utilizzare il download storico nel registro delle fonti. Non
committare lo ZIP integrale e conservare il file originale.

```bash
python scripts/prepare_building_stock.py \
  --source-zip /path/to/dati-cpa_2011.zip \
  --out-dir outputs/quality/building_stock_2011
```

L'operazione:
- Legge **solo il file ZIP locale**: nessuna richiesta di rete implicita.
- Richiede tutti i **27 codici ISTAT** e un archivio nazionale completo
  (almeno 7.000 Comuni e 900 Comuni piemontesi).
- Aggrega per codice ISTAT le variabili E3 ed E8-E16 e controlla denominatori,
  numeratori e classi cronologiche.
- Produce un CSV di 27 Comuni, benchmark GC/Piemonte/Italia ponderati sui
  conteggi ed evidenze QA JSON con hash SHA-256 dei byte dell'archivio
  e degli output.
- **Non** modifica `data/verification_matrix.csv`, ne crea dati validati.
- Non riscrive output esistenti: ogni download/analisi deve avere una
  directory di bozza distinta.

### Fase 2 - approvazione indipendente

Prima di procedere, occorre verificare **sul file ISTAT originale**:
1. provenance: provenienza dal dominio ISTAT, SHA-256, data di download, licenza;
2. corrispondenza dei 27 codici ISTAT 2011 con il perimetro comunale attuale;
3. i valori E3 ed E8-E12 per un campione di almeno tre Comuni;
4. completezza dell'archivio e confronto delle tre aggregazioni ponderate;
5. limiti metodologici della baseline 2011.

Registrare quindi un file JSON (creato da un revisore, **non generato
automaticamente**) con `indicator_id="old_building_stock"`,
`reference_year="2011"`, `decision="approved"`,
`archive_sha256`, `registry_sha256`,
`building_csv_sha256`, `benchmark_csv_sha256`, `reviewed_by`,
`reviewed_on`, `review_evidence_url` (HTTPS), `review_notes`, e
i quattro flag booleani:
`source_authenticity_reviewed`, `historical_geography_reviewed`,
`license_reviewed`, `independent_sample_reviewed`.

Il finalizzatore controlla la struttura delle attestazioni, gli hash,
i file CSV e *ricalcola* i 27 valori dall'archivio originale;
**non puo autenticare la veridicita della revisione umana**.

```bash
python scripts/finalize_building_stock_single_source.py \
  --source-zip /path/to/dati-cpa_2011.zip \
  --draft-dir outputs/quality/building_stock_2011 \
  --approval /path/to/building_review.json
```

Solo con l'approvazione autentica produce le due tabelle canoniche
in `data/indicators/` e promuove le 27 righe con
`upsert_indicator_rows`, preservando gli altri otto indicatori.

### Stato reale della PR-04

L'archivio ISTAT non e stato scaricato in questa PR e **non sono stati
introdotti valori inventati**. Le 27 righe rimangono `Da verificare` finche
non saranno disponibili archivio e validazione documentata.
