# Automazione e source-monitoring

## Obiettivo

Il repository deve poter distinguere automaticamente tre situazioni:

1. **codice rotto** — test o validazioni falliscono;
2. **fonte rotta** — URL non raggiungibile o dataset spostato;
3. **fonte aggiornata** — è disponibile un nuovo anno/versione del dataset.

## Architettura

### 1. CI deterministica

Workflow: `.github/workflows/ci.yml`

Eseguito su pull request e push su `main`.

Controlla:

- test Python;
- integrità della matrice;
- regressioni nella logica di calcolo.

### 2. Source monitor

Workflow: `.github/workflows/source-monitor.yml`

Eseguito settimanalmente e manualmente.

Legge `config/sources.json` e verifica:

- raggiungibilità della fonte corrente;
- presenza dell'anno successivo tramite URL candidato;
- anno più recente visibile sulla landing page, quando disponibile.

Se viene rilevato un problema o una nuova versione:

- produce un report JSON + Markdown;
- apre una GitHub Issue se non esiste;
- commenta la Issue esistente se l'alert è già aperto;
- fa fallire il workflow per rendere il problema visibile.

### 3. Pipeline per indicatore

Ogni indicatore deve avere:

- modulo di acquisizione/parsing;
- script di finalizzazione;
- test;
- documentazione;
- aggiornamento della matrice;
- output versionato in `data/indicators/`.

### 4. Ruolo futuro dell'AI

L'AI non dovrebbe modificare automaticamente le definizioni degli indicatori.

Può invece:

- leggere una Issue generata dal source monitor;
- confrontare vecchio e nuovo schema;
- proporre una patch;
- aprire una pull request;
- descrivere le differenze metodologiche;
- richiedere revisione umana prima del merge.

Questa separazione mantiene la diagnosi **auditabile, replicabile e difendibile**.
