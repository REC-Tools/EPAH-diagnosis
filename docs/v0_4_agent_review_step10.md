# Step 10 v0.4 — Ciclo agente proposto, non attivo

Obiettivo: revisionare gli output per tecnici e amministratori e proporre una
piccola PR draft alla volta, con test e decisione umana finale. Questa consegna
prepara e prova le guardie del ciclo; **non attiva un servizio persistente**.

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

Il vincolo locale è esplicito in [AGENTS.md](../AGENTS.md):

> Do NOT alter CI permissions, branch protections, repository secrets,
> workflows, or this AGENTS.md without explicit human authorization.

Per questo il modello di workflow è salvato come
[`v0_4_agent_workflow.yml.example`](v0_4_agent_workflow.yml.example), nella cartella
documentale: non viene eseguito da GitHub. È JSON valido, utilizzabile come YAML
senza conversione; non è un nuovo file in `.github/workflows/`.

## Ciclo e separazione dei privilegi

1. **Prepare:** legge GitHub con un token di sola lettura, richiede main e un
   attore umano con ruolo write/maintain/admin, una issue aperta e `codex-ready`.
   Una PR non può essere scambiata per una issue. Se esiste già qualunque PR aperta,
   si ferma: coda conservativa, nessun lavoro concorrente o duplicato.
2. **Propose:** esegue Codex su una copia dello SHA esatto. Il prompt è mantenuto
   nel codice fidato; titolo e corpo dell'issue sono dati non fidati in un JSON
   separato. Installa prima il solo ambiente locked. Non riceve il token di
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

## Verifiche della proposta

I test sintetici provano testo ostile nell'issue senza esecuzione/interpolazione,
ruoli e label, issue/PR, riproducibilità, coda singola, budget, percorsi protetti,
SHA differenti, lavoro locale, binari, symlink, fallimenti dei test e variazioni
post-test. Il template è controllato staticamente: azioni a SHA, separazione dei
segreti, solo avvio manuale, sintassi Python inline e shell, draft obbligatoria.

Il preflight reale è rimasto inattivo per assenza di issue approvate. Una prova
locale separata usa una patch di solo commento, esplicitamente sintetica, sulla
copia di main dello Step 9 e i comandi di verifica reali. Questa prova non dimostra
l'esecuzione dell'Action Codex, disponibilità dei segreti, autorizzazione di
pubblicazione, costo API o avvio della CI da una PR bot: questi aspetti richiedono
il primo pilot remoto dopo autorizzazione. La prova locale ha concluso 907 test e
il controllo documentale con `checks_passed`; la suite della proposta Step 10 ha
concluso 944 test, incluse 37 verifiche dedicate. Nessun output è evidenza territoriale.

## Attivazione da approvare, prima manuale

Il file proposto è pronto per una review del flusso, **non dichiarato collaudato
remotamente**. Per autorizzarne l'aggiunta attiva occorre una decisione umana
esplicita sul nuovo workflow; nessun workflow esistente viene modificato qui.

Il manutentore dovrà configurare in GitHub Settings, senza incollare valori in chat:

- `OPENAI_API_KEY`, con limiti di spesa nel progetto API. L'abbonamento ChatGPT non
  dimostra disponibilità di credito API. Il timeout limita la durata, non un costo
  monetario; il budget del provider è un requisito separato.
- `EPAH_AGENT_PUBLISH_TOKEN`, GitHub App token o credenziale dedicata al solo repo,
  con lettura necessaria al preflight e scrittura contenuti/PR. Non deve poter
  amministrare repository, segreti o workflow. Il normale `GITHUB_TOKEN` non va
  considerato sufficiente a innescare la CI delle PR bot.

La proposta pinna Codex Action a `13e9c17417b29e9a276f73ec6ed7fb574137d3c3` e la CLI
alla versione pubblicata `0.169.0`; input e profili sono stati confrontati con
l'[action.yml ufficiale](https://github.com/openai/codex-action/blob/13e9c17417b29e9a276f73ec6ed7fb574137d3c3/action.yml).
Non è stato effettuato un audit completo delle dipendenze dell'Action.

Dopo l'autorizzazione: aggiungere il file come `.github/workflows/v04-agent-cycle.yml`
e aggiornare, nella stessa review, il test che oggi ne richiede l'inattività.
Fare merge solo umano; poi applicare `codex-ready` a una issue innocua e avviare
manualmente una volta. Verificare patch, PR draft, CI effettivamente partita,
assenza di modifiche protette e costo reale. Se uno di questi controlli manca,
non dichiarare il servizio operativo.

Solo dopo una prova remota riuscita proporre la pianificazione: ad esempio una
volta al giorno alle 07:17 UTC (08:17 Roma in inverno, 09:17 in estate), massimo
un ciclo alla volta e nessuna nuova PR finché quella precedente è aperta.
Aggiungere il solo cron non basta: occorre gestire l'assenza dell'input manuale
`issue_number` e riesaminare l'autorità dell'attore delle run pianificate.
L'attuale template **non contiene schedule** né trigger da commenti/issue.

Rollback: mantenere inattivo il template o disabilitare il workflow se in futuro
approvato; revocare la sola credenziale dedicata e rimuovere le label di avvio.
Nessun merge automatico, tag, release, pubblicazione o modifica ai dati canonici.
