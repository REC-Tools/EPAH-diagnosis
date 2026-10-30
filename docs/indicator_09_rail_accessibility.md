# Accessibility to active passenger rail gateways

## Why the implementation uses a versioned reference snapshot

The public RFI national station catalogue is dynamically rendered in the web
browser. A simple HTTP client does not reliably receive the full station table,
which makes automated scraping fragile.

For reproducibility, this project therefore stores a small, versioned reference
snapshot of **active passenger rail gateways relevant to the Canavese study
area**, verified against official RFI station pages and SFM Torino service
information.

The current snapshot includes nearby active gateways on the RFI/SFM network.
It deliberately excludes stations on the Rivarolo-Pont section while that
section is operated by replacement bus rather than passenger rail.

The SFM Torino page states that the Rivarolo-Chieri section of SFM1 is operated
by train, while Rivarolo-Pont Canavese is currently managed by bus.

## Indicator

For each of the 27 municipalities:

1. resolve official ISTAT municipality codes;
2. restrict candidate destinations to the validated active rail-gateway
   snapshot;
3. select the minimum ISTAT `TEP_TOT` road travel time;
4. retain `KM_TOT` as route-distance metadata.

This is a territorial access-to-rail indicator, not an indicator of rail
service quality.

## Limitations

The gateway snapshot should be reviewed whenever the regional railway timetable
or infrastructure operating status changes.

The indicator does not include:
- train frequency;
- journey time after boarding;
- timetable compatibility;
- replacement bus quality;
- access from individual hamlets.

The finalizer now requires a precomputed draft and explicit independent QA evidence; no automatic promotion.


## PR-07 — gateway passeggeri e revisione dell'operatività

Il riferimento nella repository è una selezione di **gateway ferroviari
attivi** di interesse per il Canavese. Non è un censimento completo
delle stazioni italiane e non equivale all'insieme delle stazioni
SNAI almeno "Silver". Sono esclusi i servizi sostituiti da autobus:
la pagina ufficiale SFM1 indica ancora la tratta
**Rivarolo–Pont Canavese** come effettuata con bus.
Lo status va ricontrollato alla data di effettiva pubblicazione.

La misura è il minimo \`TEP_TOT\` ISTAT dal Comune origine (geografia 2021,
rete viaria 2020) al **Comune che ospita una stazione della lista**.
Non stima tempi casa–binario, coincidenze, frequenze ferroviarie,
accessibilità dei mezzi pubblici o tempi di viaggio in treno.

### Preparazione di bozza

\`\`\`bash
python scripts/prepare_education_rail_access.py \
  --indicator rail_accessibility \
  --road-zip /local/Piemonte.zip \
  --boundaries-zip /local/Limiti01012026_g.zip \
  --rail-gateways data/reference/canavese_active_rail_gateways.csv \
  --out-dir outputs/quality/rail_accessibility
\`\`\`

La bozza contiene 27 righe, summary, elenco versionato dei gateway
e JSON di QA con SHA-256 delle fonti. Sono controllati 27×N percorsi
stradali, codici ISTAT, valori invalidi, duplicati, stato
\`active passenger rail\` e link di provenienza HTTPS.
Non modifica la matrice e rifiuta la sovrascrittura di bozze.

Prima di promuovere a \`Dato validato\` occorre documentare la verifica
**RFI/SFM** per i nove gateway della lista selezionata, dell'ambito
geografico limitato, della compatibilità dei codici 2021/2026 e di
almeno tre tempi riscontrati nel CSV ISTAT. Il censimento esteso delle
stazioni 2026 (incluso Germagnano–Ceres) è rinviato alla v0.2.

I campi del JSON di approvazione sono quelli definiti nella sezione
istruzione, sostituendo \`indicator_id=rail_accessibility\` e
\`service_vintage=2026 snapshot, to verify\`; per l'hash della
sorgente si usa \`rail_snapshot_sha256\` invece di quelli MIM.
Sono necessari cinque flag umani v0.1 (provenienza, ammissibilità del
riferimento, crosswalk 2021/2026, licenza e campioni), e la decisione
di ambito \`piemonte_curated_proxy_approved_with_limits\`.
\`out_of_region_service_coverage_reviewed\` rimane \`false\` salvo
verifica effettivamente svolta.

\`\`\`bash
python scripts/finalize_rail_accessibility.py \
  --road-zip /local/Piemonte.zip \
  --boundaries-zip /local/Limiti01012026_g.zip \
  --rail-gateways data/reference/canavese_active_rail_gateways.csv \
  --draft-dir outputs/quality/rail_accessibility \
  --approval /local/rail_access_review.json
\`\`\`

Solo con evidenza di revisione autentica verranno aggiornate le 27
osservazioni \`rail_accessibility\`, lasciando inalterati gli altri
indicatori. SFM1: https://www.sfmtorino.it/le-linee-sfm/sfm1-pont-rivarolo-chieri/
