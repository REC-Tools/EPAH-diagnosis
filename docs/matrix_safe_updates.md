# PR K — Aggiornamenti sicuri della matrice

Sei finalizzatori territoriali (gradi giorno, altitudine, SNAI, DEA, scuola e ferrovia) ora passano le nuove osservazioni a `upsert_indicator_rows`. Una riga `Da verificare` già inizializzata viene **valorizzata** anziché saltata; la medesima coppia Comune–indicatore non viene aggiunta due volte.

La funzione legge la matrice prima della modifica, rifiuta chiavi duplicate o payload incoerenti, conserva le righe degli altri indicatori e scrive su un file temporaneo nella stessa directory. La sostituzione con `os.replace` avviene soltanto dopo il completamento della scrittura. Non è un sistema di transazioni multiprocesso: lanciare una sola pipeline alla volta sul medesimo CSV.

## Limiti
- Nessun aggiornamento automatico della matrice ufficiale da 81 a 243 righe in questa PR.
- I finalizzatori di popolazione, reddito e patrimonio edilizio restano invariati e saranno esaminati separatamente.
- I finalizzatori continuano a scrivere i propri CSV di output prima della matrice: l'atomicità riguarda **solo** `verification_matrix.csv`, non l'intera pipeline.
- I test verificano l'upsert offline con fixture; non attestano l'esito dei downloader.
