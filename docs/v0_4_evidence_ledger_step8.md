# Step 8 v0.4 — Provenienza e assenze verificabili

**Stato: technical_draft_do_not_publish; scientific_approval=false;
publication_allowed=false.** I controlli verificano integrità e coerenza tecnica,
non autenticità delle fonti, rappresentatività o approvazione scientifica.

## Diagnosi e incremento

La base dello Step 7 è la PR #170, già unita a main al controllo del 13 novembre
2026. Il modello esistente esporta fonte, periodi, stato tecnico e `not_acquired`;
H05/abitazioni conservano conteggi incorporati, H46/H50/H47 possono recuperarli
soltanto dalle anteprime corrispondenti verificate. Il catalogo editoriale contiene
ruolo e universo descrittivo: non è una fonte di denominatori numerici.

Gli artefatti locali disponibili per questa verifica sono sintetici: non sono
stati ispezionati gli originali territoriali ARPA/ISTAT/APE. La modifica aggiunge
una vista del contratto esistente, senza una seconda matrice di osservazioni:

- `evidence_ledger.json`: 27 Comuni e un record per slot, con fonte dichiarata,
  periodi, unità, ruolo, universo editoriale, stato tecnico, copertura e motivi
  di assenza; per Comune conserva presenza, periodo e conteggi documentati.
- `evidence_ledger.html`: lettura offline per tecnici, con collegamento al JSON
  completo che contiene ricevute e conteggi per Comune.
- `observations.csv`: aggiunge `scientific_approval=false` e il percorso relativo
  `evidence_ledger.json`; valori e formule restano invariati.

Il generatore comune è `evidence_ledger_v0_4.py`, invocato dall'export verificato
`atlas_observations_v0_4.py`. Il builder dell'atlante usa lo stesso export in una
cartella temporanea e incorpora soltanto i due file del registro. Report HTML/PDF,
portale e schede rimandano al registro; le schede ne includono una copia identica
al review-pack. Ogni nuovo file entra nel manifest SHA-256 del proprio output.
La sintesi PDF conserva contenuto e limite di due pagine.

## Significato dei metadati

`declared_input_evidence` conserva le ricevute già dichiarate dal manifest
originale, compresa l'evidenza pilota condivisa quando presente. Un hash in tale
ricevuta non viene promosso a verifica locale dell'originale.
`locally_verified_candidate_receipt` è presente solo se l'export ha effettivamente
verificato l'anteprima H46/H50/H47 richiesta. Il riferimento all'originale rimane
null con motivazione: consultare la ricevuta dichiarata, senza inventare un
percorso né un hash aggiuntivo.

Il ledger lega `atlas_data_sha256`; il manifest delle osservazioni lega
`atlas_manifest.json`, registro comunale e ricevute dei candidati. Il manifest del
review-pack lega anche tale manifest delle osservazioni. Il portale lega i manifest
di atlas e review-pack. Questa catena evita hash circolari: nessun file tenta di
contenere l'hash del manifest che a sua volta lo contiene.

`not_acquired` significa **assente da questo snapshot**, senza prova di
indisponibilità presso la fonte o di non applicabilità. Lo zero osservato resta
presente. Conteggi mancanti sono null con `not_preserved_in_verified_input`;
nessun denominatore viene ricostruito da percentuali o da universi editoriali.

L'atlante incorpora il registro delle sole osservazioni esportate nello snapshot.
Un review-pack con anteprime H46/H50/H47 esplicitamente fornite può documentare
ulteriori conteggi e ricevute: questi campi sono marcati come arricchimento
verificato. Senza arricchimento, il registro dell'atlante e quello del review-pack
sono identici. Le fonti, i periodi e gli stati non cambiano.

## Esecuzione e compatibilità

I comandi esistenti restano validi, sempre con destinazioni nuove:

```bash
uv run --locked python scripts/build_v0_4_visual_atlas.py --help
uv run --locked python scripts/build_v0_4_review_pack.py --help
uv run --locked python scripts/build_v0_4_output_hub.py --help
uv run --locked python scripts/build_v0_4_municipal_sheets.py --help
uv run --locked pytest -q tests/test_evidence_ledger_v0_4.py tests/test_v0_4_visual_atlas.py
uv run --locked pytest -q
uv run --locked python scripts/check_documentation.py
```

Gli snapshot dichiarati `0.4-technical-atlas` richiedono esattamente i 16 ID in
ordine di catalogo; gli snapshot precedenti restano supportati con il proprio
inventario verificato e con campi editoriali null motivati. Un review-pack storico
senza ledger può ancora essere confezionato; non viene presentato come Step 8.
Per ottenere il registro occorre rigenerare il review-pack, senza sovrascriverlo.

Checksum errati, percorsi esterni, symlink, snapshot differenti, fonte/periodo o
stati divergenti bloccano l'operazione. Il confezionamento ricostruisce il ledger
atteso dalle osservazioni e dall'atlante, verificando anche il manifest interno.
Aggiornare soltanto gli hash locali non rende coerente un ledger alterato.
Gli hash non impediscono una riscrittura coordinata di tutti gli input e non
costituiscono firme o certificazioni scientifiche.

## Revisione e rollback

Le fixture sintetiche verificano 27 × 16 slot, zeri/assenze, arricchimenti già
supportati, riproducibilità, attacchi ai manifest, link PDF e 27 schede da due
pagine con volume da 54. Sono necessarie revisione umana degli originali e prova
visiva su output reali prima di diffusione. Alcuni lettori PDF limitano l'apertura
di link relativi: l'indice HTML e i nomi stampati restano il percorso offline.

Rollback: ripristinare il codice precedente e generare in una nuova cartella;
nessuna migrazione dei dati canonici. Nessuna modifica a workflow, permessi,
release o gate scientifici. Step 9 (QA end-to-end e visuale) e Step 10 (proposte
ricorrenti in piccole PR draft con review umana) restano lavori separati; nessun
agente periodico è stato attivato da questo step.

## Verifica eseguita su fixture sintetiche

Il controllo output v0.4 ha verificato 432 osservazioni, corrispondenza HTML/CSV,
16 sezioni PDF e checksum. Controllati anche matrice canonica (27/243), intake
v0.3, contratto software stabile, riferimenti documentali e igiene repository.
La suite dedicata a ledger/atlante/report/portale/schede/catalogo passa 57 test.

L'anteprima è stata aperta in Chromium con Playwright a 390, 768 e 1280 px:
16 sezioni nel ledger, 27 righe nel report, link da portale/report e attivazione
da tastiera, nessun errore JavaScript o overflow orizzontale del ledger.
Le richieste esterne erano bloccate. La policy del browser gestito impedisce
`file://`: il controllo ha usato HTTP su loopback e **non certifica** l'apertura
diretta da file. Renderizzata e ispezionata la seconda pagina della scheda
sintetica a 16 slot: il rimando al registro resta fuori dalle celle degli indicatori.
Questa verifica limitata non completa lo Step 9 né la revisione degli output reali.
