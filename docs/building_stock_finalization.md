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
