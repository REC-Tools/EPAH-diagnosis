# v0.3 H47 — audit di riproducibilità sull'originale ISTAT POSAS 2026

**Ambito:** 27 Comuni di Sinergie in Canavese · **Stato:** `independently_reproduced_technical_only` **soltanto se l'audit riesce**. Non costituisce approvazione scientifica né modifica la v0.2 stabile.

## Perché è necessario

Il workflow iniziale ISTAT ha calcolato 27 quote 0–11 anni e pubblicato un'anteprima. La prima versione dell'estrattore non riconosceva le intestazioni reali `Totale maschi` e `Totale femmine`; la PR #142 ha corretto questo problema e ha fatto passare la nuova esecuzione ufficiale. **La presenza di un flag QA nel risultato di un solo programma, tuttavia, non prova da sola la riproducibilità del calcolo.**

Il nuovo script [`audit_posas_h47_reproduction_v0_3.py`](../scripts/audit_posas_h47_reproduction_v0_3.py) rilegge **direttamente lo ZIP originale**, senza importare il calcolo di H47, e ricostruisce da zero numeratori, denominatori e percentuali, confrontandoli con le tabelle e i checksum della stessa esecuzione.

## Baseline dell'originale

Il primo run ufficiale dell'**azione GitHub** ha dichiarato i seguenti digest, tratti dalla `source_observation.json` caricata dall'utente e dal `manifest.json` dello stesso artefatto:

| Elemento | SHA-256 dichiarato |
| --- | --- |
| `POSAS_2026_it_Comuni.zip` (originale ufficiale) | `910639e5f7b1bb8256637eee824655ba76fb8459670c9559fea1ac0922667eac` |
| `POSAS_2026_it_Comuni.csv` (membro CSV originale) | `a4c0f87fdf23618578c2a8bff25425103d0e3794cfbdbeee3aff2be4b3414f87` |

La baseline è una **ricevuta di acquisizione del workflow**, non un'approvazione istituzionale. Il download originale non è stato fornito nell'artefatto e questi digest **non sono stati ricalcolati localmente su una copia dello ZIP**. Il nuovo workflow recupera la fonte dalla URL HTTPS ufficiale e verifica il digest ZIP *prima* di attestare la corrispondenza.

Una modifica anche legittima del file pubblicato da ISTAT deve far fallire il controllo `--expected-source-sha256`, in modo da richiedere una nuova valutazione documentata del vintage e della fonte. **Non aggiornare automaticamente l'hash atteso.**

## Verifiche indipendenti

L'audit blocca il risultato in caso di:

1. ZIP diverso dalla baseline, membro CSV non univoco, schema ufficiale mancante o intestazione che non attesta il 2026 provvisorio.
2. Mancanza anche di un solo Comune, età 0–100 o riga `999`; codici/nomi ISTAT non corrispondenti, età duplicate, righe malformate.
3. `Totale maschi + Totale femmine != Totale` in qualsiasi età, oppure somme di età incoerenti con il `999` (controllo indipendente per entrambi i sessi e per il totale).
4. Hash discordanti fra ZIP, membro CSV, registro comunale, ricevuta, manifest e file di output.
5. Differenza fra i **27** numeratori/denominatori ricostruiti dall'originale e il CSV anteprima; percentuali comunali o quota complessiva ponderata inconsistenti.
6. Mancanza di `sex_totals_verified: true`, esiti di pubblicazione indebitamente approvati, o file di output già esistente.

L'artefatto contiene il nuovo `h47_independent_reproduction_audit.json` solo in caso di esito positivo, insieme ai precedenti `source_observation.json`, `population_0_11_preview.csv`, `qa.json`, `manifest.json`. Non carica lo ZIP originale: occorre archiviarlo separatamente con checksum. Conservazione Actions: **7 giorni**.

La ricevuta usa ora `schema_version: "2.0"` e registra in `audited_files_sha256`
gli hash esatti di anteprima, QA, manifest e ricevuta della fonte. L'atlante
richiede questi hash e quello del registro comunale: ricalcolare il manifest
dopo una modifica non rende valido un audit precedente. Le vecchie ricevute
senza schema devono essere rigenerate dall'originale conservato, in una nuova
cartella di revisione, oppure rilanciando il workflow aggiornato. Gli hash
legano i file all'esecuzione dell'audit; non autenticano un revisore e non
sostituiscono l'approvazione scientifica.

## Esecuzione offline (PowerShell)

Dopo aver scaricato e conservato lo ZIP ufficiale, e aver estratto l'artefatto **della stessa esecuzione** in `outputs/quality/posas_h47_official_2026/`:

```powershell
uv run --locked python scripts/audit_posas_h47_reproduction_v0_3.py `
  --source-zip data/downloads/POSAS_2026_it_Comuni.zip `
  --review-root outputs/quality/posas_h47_official_2026 `
  --expected-source-sha256 910639e5f7b1bb8256637eee824655ba76fb8459670c9559fea1ac0922667eac `
  --out-file outputs/quality/posas_h47_independent_qa_01.json
```

Per testare il software senza fonte reale:

```powershell
uv run --locked pytest -q tests/test_posas_h47_reproduction_v0_3.py
```

**Interpretazione:** un esito positivo indica corrispondenza tecnica dei valori con i byte dello ZIP e del CSV originali e consistenza delle verifiche indipendenti. Rimangono aperte verifica della licenza, conferma delle eventuali revisioni ISTAT, valutazione del proxy H47 nel framework EPAH e autorizzazione umana alla diffusione. Non trasformare automaticamente il candidato in indicatore canonico o quota comunale di famiglie in povertà energetica.
