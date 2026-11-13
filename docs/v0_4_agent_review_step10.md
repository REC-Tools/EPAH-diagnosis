# Step 10 v0.4 — Workflow manuale autorizzato, pianificazione disattivata

Obiettivo: revisionare gli output per tecnici e amministratori e proporre una
piccola PR draft alla volta, con test e decisione umana finale. Questa consegna
prepara e prova le guardie del ciclo e un workflow `workflow_dispatch`;
**non attiva un servizio periodico**. Il workflow diventa disponibile dopo il merge
umano della PR di attivazione, non con la sola autorizzazione in chat.

## Stato verificato e limiti operativi

La PR #172 dello Step 9 è già unita a main. Il preflight reale ha verificato il
repository, il ruolo del manutentore, main e gli inventari di issue/PR. Ha risposto
`idle / no_approved_issue`: non esistono attività con `codex-ready`. Non è stato
avviato alcun modello e non è stata aperta una PR dall'agente proposto.

L'integrazione GitHub restituisce HTTP 403 per le impostazioni Actions e per la
lista dei metadati dei segreti: **non** prova che i segreti siano assenti. La ricerca
plugin non ha trovato un pianificatore Codex dedicato già utilizzabile. Le review
Codex delle PR, se abilitate dal manutentore nelle impostazioni Codex, sono un
servizio distinto dal ciclo che implementa miglioramenti.

L'utente ha autorizzato esplicitamente l'aggiunta del workflow manuale il
13 novembre 2026, come richiesto da [AGENTS.md](../AGENTS.md). La sola nuova
configurazione è [`.github/workflows/v04-agent-cycle.yml`](../.github/workflows/v04-agent-cycle.yml):
nessuna modifica ai workflow esistenti, a branch protection, segreti o AGENTS.md.
Il precedente esempio inattivo è stato sostituito da questo unico file.
Il file usa JSON valido come YAML, senza conversioni o dipendenze aggiuntive.

L'input **`dry_run=true` è predefinito**: il workflow controlla input, presenza dei
nomi dei segreti, ruolo e coda ma non invoca il modello e non pubblica PR.
Un pilot reale richiede `dry_run=false` e un numero issue esplicito approvato.
Il controllo dei nomi non certifica validità delle chiavi, permessi effettivi o billing.

## Ciclo e separazione dei privilegi

1. **Prepare:** legge GitHub con un token di sola lettura, richiede main e un
   attore umano con ruolo write/maintain/admin, una issue aperta e `codex-ready`.
   Una PR non può essere scambiata per una issue. Se esiste già qualunque PR aperta,
   si ferma: coda conservativa, nessun lavoro concorrente o duplicato.
2. **Propose:** esegue Codex su una copia dello SHA esatto. Il prompt è mantenuto
   nel codice fidato; titolo e corpo dell'issue sono dati non fidati in un JSON
   separato. Gli hash degli input e il prompt della base vengono verificati prima
   dell'avvio; il JSON viene copiato nel percorso fisso `/tmp/epah-v04-agent-input/issue_input.json`
   dichiarato nel prompt, fuori dal Git tree. Installa prima il solo ambiente locked. Non riceve il token di
   pubblicazione; il profilo `:workspace` non concede accesso di rete al processo
   del modello. Non deve fare commit, push, merge o modificare policy.
3. **Verify:** su un altro runner pulito applica solo una patch ammessa dal gate
   della base fidata. Esegue pytest e il controllo documentale con `uv --locked`,
   interrompe al primo errore e lega la ricevuta a SHA base, SHA-256 patch e file.
   Rifiuta una variazione dell'albero durante i test. La copia è usa e getta e
   rimane modificata anche se i test falliscono; non usarla come checkout di lavoro.
4. **Publish draft:** su un terzo checkout, senza importare o eseguire il codice
   candidato, riverifica ruolo, label, testo dell'attività, main, coda e patch.
   Solo qui compare il token dedicato di scrittura. Crea un branch deterministico
   per issue/base e una PR con `draft=true`. Non forza push, non fa merge, non
   promuove dati. L'eventuale chiusura dell'issue avviene solo con il merge umano.

Il modello usa runner GitHub-hosted Linux usa e getta, concorrenza 1, nessuna
cancellazione di una run in corso, timeout 5/15/20/5 minuti e azioni fissate a SHA.
Un ciclo senza patch non esegue test né pubblica PR. Un errore arresta il ciclo;
un branch riservato ma non pubblicato dopo un errore richiede esame umano, non
pulizie o tentativi automatici illimitati.

## Ambito e budget del diff

Il gate `scripts/v0_4_agent_cycle.py` ammette solo sette moduli di rendering v0.4,
quattro builder di output, regressioni sintetiche e guide `docs/v0_4_*.md`.
Esclude il proprio codice, i propri test e documenti di controllo. Limiti fissi:
**6 file, 200 righe aggiunte/eliminate e 96 KiB di patch**. Niente binari,
cancellazioni, rinomine, copie o cambi di modo, symlink compresi.

Dati, configurazioni, approvazioni, validatori scientifici, lockfile, dipendenze,
workflow e AGENTS.md rimangono esclusi. La verifica dei percorsi non dimostra che
un cambiamento in un renderer sia scientificamente corretto: restano indispensabili
review umana, fixture e i gate dei dati. Un test verde non concede approvazione
scientifica o istituzionale.

## Comandi disponibili ora

```bash
# Legge GitHub, non invoca modelli e non scrive in GitHub.
# Specificare una directory NUOVA FUORI dal checkout.
uv run --locked python scripts/v0_4_agent_cycle.py plan \
  --actor NOME_MANUTENTORE --issue 123 --out-dir /tmp/epah-agent-plan

# Simulazione esplicita su JSON sintetico: simulation=true, mai autorizzazione live.
uv run --locked python scripts/v0_4_agent_cycle.py plan \
  --snapshot /tmp/synthetic-agent-snapshot.json --out-dir /tmp/epah-agent-demo

# Controllo senza applicare la patch, su una copia pulita dello SHA esatto.
uv run --locked python scripts/v0_4_agent_cycle.py scope \
  --repo /tmp/epah-verifier --base SHA_MAIN_40_CARATTERI --patch /tmp/candidate.patch

# Applica e testa SOLO nel checkout usa e getta. Ricevuta esterna e nuova.
uv run --locked python scripts/v0_4_agent_cycle.py verify \
  --repo /tmp/epah-verifier --base SHA_MAIN_40_CARATTERI \
  --patch /tmp/candidate.patch --json-out /tmp/epah-verification.json
```

Il preflight locale con `--actor` non autentica la persona che usa il terminale:
la provenienza dell'attore deve essere il contesto fidato `GITHUB_ACTOR` del
workflow. Un JSON di piano o ricevuta non è una firma né un token di autorizzazione.
Il publisher non si limita a fidarsi del file: richiede il successo del job verify,
legge nuovamente GitHub e controlla i legami della patch. Un checkout con lavoro
locale o con HEAD diverso dallo SHA richiesto viene rifiutato prima di applicare
qualsiasi modifica. Gli artefatti del piano non possono essere scritti nel sorgente.

## Verifiche e prove ancora necessarie

I test sintetici provano testo ostile nell'issue senza esecuzione/interpolazione,
ruoli e label, issue/PR, riproducibilità, coda singola, budget, percorsi protetti,
SHA differenti, lavoro locale, binari, symlink, fallimenti dei test e variazioni
post-test. Il workflow è controllato staticamente e con esecuzione locale degli helper: azioni a SHA, separazione dei
segreti, solo avvio manuale, sintassi Python inline e shell, draft obbligatoria.

Il preflight reale è rimasto inattivo per assenza di issue approvate. Una prova
locale separata usa una patch di solo commento, esplicitamente sintetica, sulla
copia di main dello Step 9 e i comandi di verifica reali. Questa prova non dimostra
l'esecuzione dell'Action Codex, disponibilità dei segreti, autorizzazione di
pubblicazione, costo API o avvio della CI da una PR bot: questi aspetti richiedono
il primo pilot remoto dopo autorizzazione. La prova locale ha concluso 907 test e
il controllo documentale con `checks_passed`; la suite della proposta Step 10 ha
concluso 944 test, incluse 37 verifiche dedicate. Nessun output è evidenza territoriale.

## Configurazione del primo pilot manuale

La PR #173 di preparazione è già unita a main. Il workflow manuale aggiunto dopo
l'autorizzazione deve a sua volta essere revisionato e unito da un manutentore;
non viene fatto merge da questa chat. I workflow con `workflow_dispatch` devono
esistere sul branch predefinito per essere avviati dall'interfaccia Actions.

### 1. Chiave API OpenAI dedicata

Nella [piattaforma API OpenAI](https://platform.openai.com/), selezionare o creare
un progetto dedicato a EPAH, verificare il credito API e generare una chiave del
progetto in **API Keys → Create new secret key**. Salvarla direttamente come
`OPENAI_API_KEY` nei repository secrets GitHub. L'abbonamento ChatGPT non prova
la disponibilità di credito API.

In **Limits**, impostare spend limit e notifiche; abilitare **Enforce a hard limit**
se si vuole fermare il traffico al raggiungimento della soglia. I soli alert non
fermano le richieste; l'enforcement può avere un ritardo. Il timeout del workflow
limita la durata, non stabilisce da solo un tetto monetario.
[Configurazione ufficiale di progetti e limiti](https://help.openai.com/en/articles/9186755-managing-projects-in-the-api-platform).

### 2. Token GitHub per il pilot

Per la prima prova manuale, creare un [fine-grained personal access token](https://github.com/settings/personal-access-tokens/new)
con scadenza breve e questi campi:

| Campo | Valore |
| --- | --- |
| Resource owner | `REC-Tools` |
| Repository access | Only select repositories → `EPAH-diagnosis` |
| Contents | Read and write |
| Pull requests | Read and write |
| Issues | Read-only |
| Metadata | Read-only, normalmente obbligatorio automaticamente |

Non concedere Administration, Secrets, Workflows o accesso ad altri repository.
Se l'organizzazione richiede approvazione, il token deve risultare approvato prima
della prova: la sola creazione non basta. Salvarlo come `EPAH_AGENT_PUBLISH_TOKEN`.
Il token ha comunque i limiti del suo utente: deve poter creare un branch e una PR
nel repository. Il normale `GITHUB_TOKEN` rimane in sola lettura.

Un installation token GitHub App dura poco e non va usato come segreto statico
per un servizio permanente. Per una successiva automazione continuativa è preferibile
una GitHub App che generi token effimeri per job, con una nuova review della configurazione.
[Guida ufficiale GitHub ai token](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens).

### 3. Dove inserire i due segreti

Aprire [Settings → Secrets and variables → Actions](https://github.com/REC-Tools/EPAH-diagnosis/settings/secrets/actions)
e scegliere **New repository secret** due volte: nome e valore della chiave API,
poi nome e valore del token GitHub. I valori vanno inseriti solo nella UI protetta
di GitHub: non in issue, file del repository, log o chat. Questo workflow usa
repository secrets, non secrets di un environment che richiederebbe una configurazione diversa.
[Guida GitHub ai repository secrets](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets).

Non serve concedere scrittura al `GITHUB_TOKEN` globale. Se una policy Actions
blocca una delle Action fissate nel file, farne verificare l'autorizzazione
all'amministratore senza allargare automaticamente i permessi.

### 4. Prima esecuzione senza modello

Dopo il merge umano del workflow, aprire
[Actions → EPAH v0.4 agent cycle — manual pilot](https://github.com/REC-Tools/EPAH-diagnosis/actions/workflows/v04-agent-cycle.yml),
scegliere **Run workflow**, branch **main**, lasciare **dry_run selezionato** e
`issue_number` vuoto. Il job prepare deve riuscire; gli altri tre devono essere
skipped. Anche `idle/no_approved_issue` è un esito corretto di questa prova.
Non vengono verificate validità del token, della chiave o disponibilità di credito:
sono controlli da completare nel primo pilot reale.

### 5. Pilot reale su una issue innocua

Creare una issue con una piccola miglioria di output e criteri sintetici chiari,
poi applicare `codex-ready` come manutentore. Esempio di attività: mostrare un
messaggio esplicito nel report HTML quando la ricerca non trova Comuni, lasciando
invariati CSV, valori e metadati. Non usare un problema metodologico o un aggiornamento dati.

Chiudere o completare le altre PR aperte: la coda conservativa blocca il ciclo anche
quando una PR estranea è ancora aperta. Avviare nuovamente il workflow su main,
**deselezionare dry_run**, inserire il solo numero della issue (senza `#`) e avviare
una volta. Un numero vuoto per una run reale viene rifiutato prima della chiamata AI.
Verificare patch, PR draft, CI effettivamente partita, costo e assenza di modifiche
protette. Un ciclo `no_change` non apre PR. In caso di errore non ripetere alla cieca:
consultare il job fallito e la ricevuta; non condividere valori dei segreti.
[Avvio manuale dei workflow, documentazione GitHub](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow).

Codex Action resta fissata a `13e9c17417b29e9a276f73ec6ed7fb574137d3c3`, CLI `0.169.0`.
Non è stato effettuato un audit completo delle dipendenze dell'Action, né una prova
remota con il provider durante la sola preparazione. Solo dopo il pilot remoto
riuscito si può dichiarare operativo il ciclo manuale.

Solo dopo una prova remota riuscita proporre la pianificazione: ad esempio una
volta al giorno alle 07:17 UTC (08:17 Roma in inverno, 09:17 in estate), massimo
un ciclo alla volta e nessuna nuova PR finché quella precedente è aperta.
Aggiungere il solo cron non basta: occorre gestire l'assenza dell'input manuale
`issue_number` e riesaminare l'autorità dell'attore delle run pianificate.
L'attuale workflow **non contiene schedule** né trigger da commenti/issue.

Rollback: disabilitare il workflow manuale o ripristinare il commit di attivazione; revocare la sola credenziale dedicata e rimuovere le label di avvio.
Nessun merge automatico, tag, release, pubblicazione o modifica ai dati canonici.
