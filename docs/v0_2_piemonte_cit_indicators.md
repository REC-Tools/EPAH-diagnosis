# Nuovi indicatori CIT Piemonte: combustibile e vetustà dei generatori

Due fonti regionali ufficiali sono catalogate come Open Data del Catasto Impianti Termici (CIT), ma lo **schema dei CSV effettivi non è ancora stato verificato**. Per questo la PR introduce un ETL configurabile, testato su fixture sintetiche, senza dati o percentuali municipali inventate.

1. [Gruppi termici per Comune e combustibile](https://www.dati.gov.it/node/view-dataset/dataset?id=80540d5b-72af-4c45-901b-eb4a4f7ae9cf): quota gruppi termici con gasolio/GPL sul totale di gruppi con combustibile classificabile. Pubblicare anche N metano, GPL, gasolio, solidi, elettrici, altri, sconosciuti.
2. Gruppi termici per Comune e **data di installazione**: quota di gruppi con almeno 20 anni sul totale con anno di installazione noto. Fonte reperibile nel catalogo Piemonte per 'Numero di gruppi termici aggregati per comune e data di installazione'.

La data 2020 nei metadati catalogo non prova che il CSV scaricato sia riferito al 2020: verificare nell'originale la vera data snapshot. L'operatore la dichiara via `--snapshot-date`, e il QA indica esplicitamente che è stata fornita da chi esegue.

## Come usare dopo aver scaricato i CSV originali

Conservare due CSV in `data/downloads/` (gitignored); NON versionare dati grezzi senza una review separata.

  python scripts/prepare_piemonte_cit.py --mode fuel --input data/downloads/CIT_combustibili.csv --snapshot-date AAAA-MM-GG --out-dir outputs/quality/cit_fuel_v02 --strict

  python scripts/prepare_piemonte_cit.py --mode age --input data/downloads/CIT_data_installazione.csv --snapshot-date AAAA-MM-GG --out-dir outputs/quality/cit_age_v02 --strict

Se le colonne del download non coincidono con gli alias, specificare `--code-col`, `--category-col` e `--count-col` con i nomi esatti stampati nell'errore. Il parser rifiuta intervalli temporali ambiguamente etichettati (ad esempio '1990–2000') e numeri non interi, e segnala i Comuni senza gruppi senza introdurre valori zero fasulli.

## Interpretazione e limiti

- Un gruppo termico NON equivale a una famiglia, abitazione, impianto o edificio.
- Il mix gasolio/GPL non è automaticamente una misura di povertà energetica.
- L'anzianità non prova scarsa efficienza o costo reale; segnalare N non classificabili e date mancanti.
- Entrambe le grandezze sono candidate v0.2 finché non è controllata la copertura reale dei 27 Comuni.
- Non usare il vecchio finalizzatore ISTAT 2011 per scrivere risultati CIT recenti: denominatori diversi.
- I file `data/**`, `config/**`, i nove indicatori core e la v0.1 restano invariati.

Il nuovo renderer cartografico supporta assoluta scientifica e relativa verde/grigio/rosso; le classi CIT riceveranno tale rappresentazione solo dopo aver calcolato dati reali e scelto con motivazione la direzione di interesse.