# Contribuire a EPAH Diagnosis

Partire dall'[architettura](docs/v0_4_architecture.md) e dalla
[guida sviluppatore](docs/v0_4_developer_guide.md). Gli esempi sintetici permettono
di verificare il software senza archivi locali o dati privati.

## Un incremento, un branch, una PR

Preservare le modifiche locali prima di aggiornare la base. Da un checkout pulito:

```powershell
git switch main
git pull --ff-only
git switch -c feat/v05-local-collection-protocol
uv sync --python 3.11 --locked --group dev
uv run --locked epah examples synthetic --out-dir work/contributor-01
```

Usare `feat/`, `fix/`, `docs/` o `release/` e un nome che descriva lo scopo.
Non lavorare direttamente su main. Limitare ogni PR a un comportamento
verificabile; aggiungere regressioni significative e aggiornare gli esempi.
Creare commit mirati, controllare il diff e aprire una draft PR con problema,
soluzione, comandi di verifica, limiti e rollback. Renderla pronta solo dopo
revisione e CI; l'unione deve essere deliberata, senza aggirare le protezioni.

```powershell
uv run --locked pytest -q
uv run --locked python scripts/check_documentation.py
uv run --locked python scripts/check_v0_5_release.py
```

Su Windows seguire la configurazione Bash della guida. Segnalare separatamente
capacità mancanti dell'host e test superati. Se cambiano gli output, eseguire
anche gli audit pertinenti e ispezionare prodotti rappresentativi.

## Dati e decisioni

Non aggiungere originali, pacchetti territoriali, percorsi privati o credenziali
ai commit. Non sovrascrivere prodotti esistenti. Gli output restano
`technical_draft_do_not_publish`; una CI verde non cambia gli stati scientifici.
Formule, unità, anni, geografie e denominatori richiedono una decisione documentata.
Tenere distinti H03/H04, H05 e revisioni degli altri candidati.

Gli incrementi successivi possono completare acquisizioni e protocolli locali
per le 23 proposte già censite, senza inventare osservazioni municipali. Acquisizione, calcolo e approvazione richiedono evidenze successive.

## Release separate dallo sviluppo

Un branch `release/vX.Y.Z` aggiorna insieme versione del progetto, pacchetto,
sola voce del progetto nel lockfile, note e contratto di release. Le dipendenze
non si aggiornano incidentalmente. I gate delle versioni precedenti restano
storici e sono provati con fixture delle rispettive versioni.
Il merge non pubblica automaticamente: il rilascio software usa un workflow
manuale sul commit revisionato, con ambito esplicito degli asset consentiti.
La pubblicazione territoriale richiede una decisione separata.
