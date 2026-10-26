# Automazione e source-monitoring

## Obiettivo
Distinguere tre condizioni: **errore del codice**, **fonte non utilizzabile**, **nuova versione disponibile**. Un allarme non autorizza modifiche automatiche a definizioni metodologiche o valori validati.

## Stato implementato
- `.github/workflows/ci.yml`: esegue test Python e la validazione di base della verification matrix su PR e push a `main`.
- `.github/workflows/source-monitor.yml`: controlli periodici/manuali delle fonti registrate in `config/sources.json`, con segnalazioni e report previsti dal workflow.
- `.github/workflows/update-mef-income.yml` e `update-population-65plus.yml`: workflow di aggiornamento specifici.

I controlli attuali **non** garantiscono ancora corrispondenza completa tra schede documentali, moduli, registri, file generati e benchmark; questi controlli sono previsti nella PR E.

## Contratto architetturale
Per ogni indicatore: fonte identificata → acquisizione → normalizzazione → calcolo → QA → benchmark comparabile → output documentato. Le fasi, i metadati minimi e la gestione degli errori sono descritti in [pipeline.md](pipeline.md). La distinzione fra indicatori di vulnerabilità e descrittori territoriali è in [framework.md](framework.md).

## Revisione umana obbligatoria
L'automazione può rilevare un dataset aggiornato, segnalare un URL rotto, proporre modifiche al parser o aprire una PR. Non può approvare autonomamente un nuovo denominatore, soglie, pesi, definizioni o conclusioni di povertà energetica. Un cambiamento di vintage richiede nuovi controlli anche quando il metodo non cambia.

## Lavori successivi
- PR B: registro unico indicatori e stato di maturità.
- PR C: policy degli artefatti e provenance.
- PR D: template per PR e issue metodologiche.
- PR E: controllo automatico delle coerenze del catalogo.
