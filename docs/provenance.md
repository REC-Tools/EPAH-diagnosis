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

## Operational draft manifests (PR-02)

The offline command `scripts/write_provenance.py` generates a JSON draft from
**actual local file bytes**. It calculates SHA-256 digests for the artifact and
for each explicitly supplied raw source file. The source IDs, landing/download
URLs, years, and license-verification flags come from `config/sources.json`.
Missing download times, raw files, licenses and QA decisions are kept `null`
or `not_assessed`, never invented.

Example:

```bash
python scripts/write_provenance.py \
  --artifact data/indicators/income_vulnerability_2024.csv \
  --indicator-id income_vulnerability --reference-year 2024 \
  --output outputs/quality/income_2024_provenance.json
```

To record the checksum of the real original archive, add
`--source-file mef_irpef_comuni=/local/path/to/source.zip`.
The original archive is not committed. This generator is non-destructive:
it refuses to overwrite an existing manifest or an input file.

**Important:** The resulting manifest remains `draft` / `not_assessed`.
It does not check the source contents, licensing, methodology, completeness,
numerators or denominators. Those checks and human approval are still required
for PR-03 through PR-09. A later data-finalizer PR will attach source
retrieval timestamps and execution details as actual captured evidence.
