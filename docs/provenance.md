# Contratto di provenance

Il formato JSON in [`provenance_manifest.example.json`](provenance_manifest.example.json) illustra i campi minimi di tracciabilità per un artefatto. È un **esempio non operativo**: valori `null` significano informazioni da completare, non attestazioni di verifiche effettuate.

## Chiave e lineage
Per ogni file elaborato registrare identificativo indicatore, tipo di artefatto, percorso, vintage, geografia e collegamento a una o più fonti; la catena deve consentire `fonte → file originario → trasformazione → output → report`. Sorgenti diverse per lo stesso anno non vanno fuse senza nota sulla comparabilità.

## Campi
- `schema_version`, `artifact`, `sources`: identità e legami a monte.
- `processing`: commit, script/comando, parametri e timestamp.
- `quality`: copertura, controlli, esito QA ed eccezioni.
- `publication`: autorizzazione/stato editoriale e limitazioni d'uso.

`sha256` è sempre un digest a 64 cifre esadecimali del file reale: in assenza di file, scrivere `null`, non un hash inventato. Date ISO 8601 con fuso orario quando è disponibile l'ora; date calendario `YYYY-MM-DD` per la pubblicazione.

## Distinzioni
Lo stato di pubblicazione dell'artefatto (`draft/reviewed/published`) non è lo stato della riga (`Da verificare` ecc.) e non è la maturità della definizione (`EXPERIMENTAL` ecc.). Nessuno dei tre autorizza automaticamente un'affermazione sulla prevalenza di povertà energetica.

## Introduzione graduale
1. Manifest manuale per ogni output che si vuole condividere.
2. Associazione con dataset realmente presenti e checksum verificati.
3. Produzione automatica dei manifest e controlli CI in una PR tecnica separata.
4. Archiviazione/rilascio versionato degli output pubblicabili, dopo revisione umana.
