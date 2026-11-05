# CLI unificata EPAH Diagnosis (fase 1)

La CLI \`epah\` organizza i comandi già esistenti. Non implementa nuove
trasformazioni dei dati, non aggira le procedure QA e non promuove righe
nella matrice canonica. È supportata da un **checkout installato in modalità
editable**: i builder esistenti rimangono in \`scripts/\`.

Preparazione (Python 3.11 e uv installati):

\`\`\`powershell
uv sync --python 3.11 --locked --group dev
uv run --locked epah --help
\`\`\`

## Consultazione e controlli (senza modificare dati)

\`\`\`powershell
uv run --locked epah status
uv run --locked epah sources check
uv run --locked epah data validate
\`\`\`

- \`status\`: mostra il gate canonico in modalità **report-only**, poi la
  disponibilità dei 12 input locali del pilota. Ritorna 0 quando i controlli
  *vengono eseguiti*, anche se la disponibilità dei file del pilota è
  incompleta: **non** è un segnale di release pronta. Un errore del gate
  canonico o dello script torna nonzero.
- \`sources check\`: inventario offline dei file attesi dal *pilota v0.1*,
  non un downloader o un audit delle fonti online. Ritorna 1 se mancano input.
  Accetta \`--json-out <nuovo_file>\` e non sovrascrive report esistenti.
- \`data validate\`: esegue nell'ordine il validatore della matrice,
  del registro comunale e del framework. La validità strutturale non
  equivale a validazione scientifica o approvazione alla pubblicazione.

## Build (richiede selezione esplicita del profilo)

\`\`\`powershell
uv run --locked epah build --profile pilot
uv run --locked epah build --profile canonical
\`\`\`

Il profilo \`pilot\` richiama esclusivamente
\`build_v0_1_owner_accepted.py\`, con i medesimi input locali e i controlli
9/9 e i limiti già documentati. Il profilo \`canonical\` richiama
\`build_v0_1_bundle.py\` e mantiene il proprio gate 243/243 con nove
review metodologiche. Non è possibile selezionare un profilo predefinito:
\`--profile\` è obbligatorio.

Se le destinazioni esistono già, **non vengono sovrascritte**. Per un nuovo
pilota specificare entrambe le destinazioni per evitare collisioni con
l'archivio precedente:

\`\`\`powershell
uv run --locked epah build --profile pilot --output-dir outputs/v0.1.0-pilot-replay --archive outputs/epah_diagnosis_v0.1.0_pilot_replay.zip
\`\`\`

Non espone alcun flag \`--replace\`.

## Confronto fra output già generati

\`\`\`powershell
uv run --locked epah replay compare outputs/v0.1.0-pilot outputs/v0.1.0-pilot-replay
\`\`\`

Confronta i due CSV di profilo/confronto e il GeoJSON comunale usando
\`check_pilot_replay.py\`. File PDF, PNG, Excel e manifest non sono inclusi
nel confronto deterministico. Una corrispondenza tecnica non certifica
validità metodologica o approvazione istituzionale.

## Limitazioni e fasi successive

Questa CLI non automatizza download, finalizer o approvazioni umane.
Tali passaggi rimangono nello schema **originale → prepare → QA → review
documentata → finalize → PR protetta**. La versione 0.2 CIT in quarantena
non viene pubblicata tramite questa CLI.
