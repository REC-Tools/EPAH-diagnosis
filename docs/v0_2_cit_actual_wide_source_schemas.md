# CIT Piemonte v0.2 — adeguamento agli schemi CSV osservati

Il 30 ottobre 2026, l'esperto ha eseguito inspect_piemonte_cit sui due file originali e condiviso gli header. Sono file WIDE, non righe long (categoria + count). I valori delle righe originali non sono stati condivisi: nessuna percentuale reale comunale viene dichiarata da questa PR.

## Originali osservati

- Combustibili: 1183 righe. SHA256 7659242c31a4dd47d24e4d65b9075f90845a8f81829eff27cf485c24027793b4. Colonne key_classe, gas_naturale, gasolio, gpl, pellet_tronchetti_cippato, olio_combustibile, biomassa, carbone, policombustibile, termica, altro.
- Età: 1346 righe. SHA256 4b506567cb3ea3aeb355eed021a30aa83f4c55d6729e9ae99bb825e71484712a. Colonne denominazione_provincia, istat_comune, denominazione_comune, numero_fino_1950, numero_1951_1960, numero_1961_1970, numero_1971_1980, numero_1981_1985, numero_1986_1990, numero_1991_1995, numero_1996_2000, numero_2001_2005, numero_2006_2010, numero_2011_2015, numero_2016_2020, numero_dal_2021.
- Encoding UTF-8 with BOM, separatore punto e virgola, fonte CC BY 4.0 nel catalogo.

## Significato delle trasformazioni

1. Gasolio+GPL / totale gruppi termici riportati nelle categorie originarie. Mantiene tutte e dieci le categorie: pellet/biomassa/carbone sono combustibili solidi; olio combustibile/policombustibile/termica/altro rimangono in 'altri'. Il CSV NON presenta una colonna autonoma elettricità: non attribuire il valore zero di compatibilità all'assenza reale di impianti elettrici.
2. Età: i bin temporali non consentono una quota esatta di gruppi con almeno 20 anni. Il parser calcola la quota minima SICURA (intervalli terminati prima dell'anno-soglia), i gruppi nel bin ambiguo e la quota massima compatibile. Per il 30/10/2026, le classi <=2005 sono certamente antecedenti ai 20 anni; quella 2006–2010 è ambigua. Il PDF riporta la quota minima e l'intervallo, non una stima falsamente precisa.
3. L'abbinamento dei combustibili tramite key_classe non è ancora stato verificato per valore. Sono ammessi solo codici ISTAT esatti con padding a 6 cifre o denominazioni comunali esatte (normalizzate) dei 27 Comuni. Nessun matching fuzzy, join per posizione o conversione arbitraria di codici composti. In caso di chiavi non riconosciute, strict blocca e restituisce esempi.
4. --as-of YYYY-MM-DD è la data locale di analisi per la soglia dei 20 anni, NON un timestamp ufficiale di aggiornamento della fonte. Le date del catalogo open data non equivalgono a quelle dei record.

## Comandi Windows dopo il merge

    git switch main
    git pull --ff-only origin main

    python scripts/inspect_piemonte_cit.py --mode fuel --input data/downloads/CIT_combustibili.csv
    python scripts/inspect_piemonte_cit.py --mode age --input data/downloads/CIT_data_installazione.csv

    python scripts/prepare_piemonte_cit_wide.py --mode fuel --input data/downloads/CIT_combustibili.csv --as-of 2026-10-30 --out-dir outputs/quality/cit_fuel_v02 --strict
    python scripts/prepare_piemonte_cit_wide.py --mode age --input data/downloads/CIT_data_installazione.csv --as-of 2026-10-30 --out-dir outputs/quality/cit_age_v02 --strict

    python scripts/build_v0_2_cit_preview.py

I nomi delle directory sono quelli attesi dal builder precedente. Se sono già occupati, scegliere altre directory con --out-dir per le estrazioni e passare --fuel-dir / --age-dir al builder. Non sovrascrivere i risultati già generati.

Se strict blocca il file combustibili e il nuovo inspector riporta selected_27_matched inferiore a 27, le prime key_examples chiariranno il formato effettivo dei valori di key_classe. Non assumere che il solo nome del campo indichi un codice ISTAT.

## Deliverable dopo QA

- Due estratti CSV da 27 Comuni con numeratori, denominatori, mappa delle categorie e age uncertainty.
- Due cit_qa.json con SHA256 e corrispondenza alle due fonti ispezionate dall'esperto.
- Quattro mappe: scala assoluta cividis e relativa verde/grigio/rosso, centrata sulla media dei 27 Comuni.
- Un GeoJSON, un manifest SHA e un PDF di assistenza tecnica EPAH con limiti e intervallo di incertezza.

Restano invariati i nove indicatori v0.1, la matrice canonica e le approvazioni pregresse. I gruppi termici non sono famiglie, edifici né una misura diretta della povertà energetica.