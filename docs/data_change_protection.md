# Protezione della matrice e delle evidenze nelle Pull Request

La protezione esegue **un controllo automatizzato del diff e delle dichiarazioni di fonte**. Non richiede un secondo account GitHub e non certifica la correttezza scientifica. La revisione delle fonti e i criteri di pubblicazione v0.1 restano separati.

## Problema affrontato

Le PR cartografiche o documentali possono accidentalmente rimuovere dataset, annullare la validazione delle 27×9 righe o eliminare evidenze e test. Inoltre due workflow programmati, MEF e ISTAT 65+, in precedenza eseguivano `git push` direttamente verso `main` dopo il download. Entrambi i percorsi sono pericolosi anche quando la suite `pytest` rimane verde, perché i test non necessariamente rilevano ogni perdita di dati.

## Che cosa protegge il controllo

Il workflow `.github/workflows/protected-data-guard.yml` esamina i percorsi modificati nell'effettivo **Git diff tra SHA base e head** (include rename e delete). Protegge:

- **qualsiasi file sotto `data/**`**, compresi matrice, anagrafe, indicatori, geografia, derivati e dossier QA. La protezione vale anche per cartelle dati aggiunte in futuro;
- `config/indicators.json`, `config/sources.json`, `config/release_v0_1.json`, `config/release_reviews_v0_1.json`.

Ogni PR che modifica un percorso protetto deve inserire **nel corpo della PR**, su righe separate:

```text
Data-change: yes
Data-evidence: docs/my_independent_source_review.md
```

La fonte/evidenza deve riferirsi a un percorso concreto (interno o URL), non a `TBD`, `pending` o un segnaposto. La dichiarazione **non** costituisce validazione scientifica: rende esplicito il perimetro e l'evidenza delle modifiche. Non basta cambiare titolo, nome branch o una descrizione generica.

Quando si elimina un file protetto, occorre inoltre **per ogni file eliminato**:

```text
Data-delete: data/quality/old_source_evidence.json
```

Anche lo spostamento/rename di un file protetto richiede la dichiarazione del **percorso di origine**, perché può rompere riferimenti e prove storiche. Non inserire `Data-delete` se non esiste una cancellazione intenzionale.

Se lo stato `Dato validato` o `Dato acquisito` regredisce, aggiungere **per ogni indicatore coinvolto**:

```text
Data-downgrade: heating_degree_days
```

La modifica di un valore, anno, unità o URL di una riga **già validata e che rimane validata** richiede:

```text
Data-revise: income_vulnerability
```

**Non sono ammesse** modifiche silenziose delle chiavi Comune × Indicatore, anche in una PR dati: la migrazione dell'universo è un progetto separato. Il controllo individua inoltre dichiarazioni contraddittorie del tipo «NON modifica dati» accanto a modifiche di file protetti.

## Gestione senza secondo account GitHub

Il workflow non consulta le review GitHub, non chiede `APPROVED` e non chiama l'API delle review: **l'autore puo gestire e unire la propria PR**, se i controlli richiesti dalla configurazione GitHub passano. Rimangono obbligatori `Data-change: yes` e `Data-evidence` per qualsiasi modifica sotto `data/**` o nei registri protetti; in caso di cancellazioni, regressioni o revisioni valgono anche le altre dichiarazioni. La decisione metodologica e l'autorizzazione istituzionale alla pubblicazione devono essere documentate separatamente, senza trasformarsi in obblighi di approvazione da un altro account. Un check verde non equivale a un dato validato.

Il workflow esegue lo script dal **commit di base**, impedendo che una PR con dati protetti eluda i controlli modificando soltanto il checker nella stessa PR. Se le regole GitHub richiedono approvazioni, l'amministratore deve rimuovere quella impostazione separatamente: questa PR non modifica automaticamente la branch protection.

## Workflow programmati: non più push su main

`.github/workflows/update-mef-income.yml` e `update-population-65plus.yml` ora:

1. scaricano, calcolano e testano i nuovi dati, quando raggiungono effettivamente i portali esterni;
2. creano un branch univoco per esecuzione;
3. **aprono una PR draft**, con `Data-change`, `Data-evidence` e `Data-revise`;
4. non eseguono `git push` su `main`.

Se l'organizzazione impedisce al `GITHUB_TOKEN` di creare PR, l'azione fallisce in modo esplicito. Configurare nelle impostazioni di GitHub Actions **Allow GitHub Actions to create and approve pull requests**, se disponibile, per abilitare la creazione; ciò non rappresenta un'approvazione delle PR. GitHub non avvia necessariamente altri workflow quando una PR è creata usando il `GITHUB_TOKEN`: dopo l'intervento umano eseguire/richiedere la CI prima della pubblicazione.

## Requisito fondamentale: protezione di main

**La CI non impedisce di per sé un merge manuale o un push diretto.** Per ottenere enforcement sul server, un amministratore deve configurare per `main`, dove consentito dal piano GitHub:

- PR obbligatoria (no push diretto) e controlli automatici; **nessuna review GitHub obbligatoria**;
- status check obbligatori: `CI / test` e `Protected data change guard / Check protected data scope`;
- blocco di bypass, force-push e cancellazioni, con eventuali eccezioni esplicite per i manutentori;
- restrizioni su modifica della stessa CI e dei gate (idealmente CODEOWNERS/reviewer dedicati).

La connessione GitHub usata in questo progetto **non ha permessi amministrativi di branch protection**. Se il repository privato o il piano non consentono ruleset/branch protection, il controllo resta un allarme automatizzato e **non** una barriera garantita contro merge e push diretti. Non dichiarare il repository protetto finché l'enforcement non sia stato verificato con un test reale sulle impostazioni.

## Casi compatibili e test

- PR cartografica/documentale senza dati: passa il controllo di scope.
- PR con dataset o matrice: richiede dichiarazioni chiare ed evidenza prima di essere pronta; nessuna review GitHub di terzi è necessaria.
- PR con fonte archiviata eliminata: si blocca senza `Data-delete`.
- PR con 81 stati validati declassati: si blocca senza `Data-downgrade` pertinente, anche se il catalogo e la matrice restano strutturalmente validi.
- PR con valori validati rivisti: richiede `Data-revise`.
- PR dati che modifica l'insieme delle chiavi Comune × Indicatore: si blocca.

Eseguire localmente:

```bash
python -m pytest -q tests/test_pr_data_guard.py
python -m pytest -q
python scripts/check_documentation.py
```

Il controllo online parte dagli eventi PR (apertura, modifica del corpo, nuovi commit, passaggio draft/ready), se GitHub Actions e abilitato e l'evento non e soppresso. Le PR dati esistenti devono mantenere le dichiarazioni di fonte richieste; non serve un'approvazione GitHub da un altro account.
