# Access to a complete upper-secondary education pole

## Indicator

Road travel time, in minutes, from each Green Community municipality to the
nearest municipality with a **complete upper-secondary education offer**.

## Service definition

The definition follows the SNAI / ISTAT methodology.

A municipality qualifies as an education service pole when it offers:

1. at least one classical or scientific lyceum; and
2. at least one technical or professional pathway.

This is deliberately stricter than "nearest high school" because it measures
access to a meaningful range of upper-secondary education options.

## Education sources

The Ministry of Education and Merit (MIM) Open Data Portal publishes:

- the official school registry, with school code and municipality;
- upper-secondary students by active pathway, including `TipoPercorso`,
  `Percorso` and `Indirizzo`.

The current pipeline uses school year **2024/25**, the latest school-year
distribution available for the pathway dataset at implementation time.

## Travel-time source

Travel times use the same official ISTAT municipal origin-destination matrix as
the DEA indicator:

- `TEP_TOT`: effective road travel time;
- `KM_TOT`: route distance;
- municipal geography: 1 January 2021;
- road graph: 2020.

Using the same matrix makes health and education accessibility directly
comparable.

## Interpretation

The result is a municipal territorial-accessibility proxy. It does not measure:

- actual school-bus or public-transport travel time;
- timetable compatibility;
- student choice beyond the SNAI service definition;
- capacity, quality or availability of places in individual schools.

The finalizer requires a reviewed draft and an explicit `--approval` file; it cannot validate by downloading sources alone.


## PR-07 — acquisizione, copertura e revisione separata

La pipeline usa il **registro MIM** e il dataset **studenti per indirizzo**
per l'anno scolastico **2024/25**, entrambi da conservare in CSV originali.
Il dataset 2024/25 non equivale all'offerta scolastica attuale nel 2026:
per la pubblicazione occorre verificare scuole, indirizzi effettivamente
attivi e l'eventuale disponibilità di dati più recenti.

Si identificano come poli soltanto i Comuni con almeno un liceo
**classico o scientifico** e almeno un percorso
**tecnico o professionale** (definizione compatibile con la proxy SNAI).
Non è il semplice tempo verso la scuola secondaria più vicina.

I tempi sono dati ISTAT \`TEP_TOT\` dal centroide della sezione del Municipio
alla **località comunale di destinazione**, non alla sede scolastica.
La matrice è riferita alla geografia 2021 e alla rete viaria 2020;
la selezione delle scuole è riferita al 2024/25.
Le destinazioni sono limitate al Piemonte: va valutata esplicitamente
la presenza di possibili poli più vicini in altre regioni.

### Preparazione offline e verifiche

\`\`\`bash
python scripts/prepare_education_rail_access.py \
  --indicator upper_secondary_accessibility \
  --road-zip /local/Piemonte.zip \
  --boundaries-zip /local/Limiti01012026_g.zip \
  --school-registry /local/SCUANAGRAFESTAT20242520250831.csv \
  --school-pathways /local/ALUSECGRADOINDSTA20242520250831.csv \
  --out-dir outputs/quality/upper_secondary_accessibility
\`\`\`

La procedura conserva il join sui codici ISTAT a 6 cifre e
verifica tutte le combinazioni **27 origini × N poli scolastici**,
non soltanto quelle verso il polo che risulta più vicino.
Controlla i valori numerici, i duplicati, l'idoneità delle destinazioni
e registra SHA-256 dei CSV e ZIP di input e degli output.
I quattro output sono: osservazioni per Comune, riepilogo, elenco poli
e JSON di audit con \`qa_status=technical_checks_only\`.

L'aggiornamento di \`data/verification_matrix.csv\` richiede una
**revisione umana effettiva** della provenienza dei file, delle licenze,
del crosswalk di codici 2021/2026, dei percorsi e dell'offerta scolastica
2024/25. Il JSON di approvazione deve dichiarare
\`indicator_id=upper_secondary_accessibility\`,
\`road_geography_year=2021\`, \`road_graph_year=2020\`,
\`service_vintage=2024/25\`, \`decision=approved\`,
i checksum del rapporto QA, \`reviewed_by\`, \`reviewed_on\`,
\`review_evidence_url\`, \`review_notes\` e tutti i sei flag:
\`road_2021_to_registry_2026_crosswalk_reviewed\`,
\`source_authenticity_reviewed\`, \`service_eligibility_reviewed\`,
\`out_of_region_service_coverage_reviewed\`, \`license_reviewed\`,
\`independent_route_sample_reviewed\`.
È inoltre richiesta la decisione esplicita
\`methodology_scope_decision=piemonte_curated_proxy_approved_with_limits\`.

\`\`\`bash
python scripts/finalize_upper_secondary_accessibility.py \
  --road-zip /local/Piemonte.zip \
  --boundaries-zip /local/Limiti01012026_g.zip \
  --school-registry /local/SCUANAGRAFESTAT20242520250831.csv \
  --school-pathways /local/ALUSECGRADOINDSTA20242520250831.csv \
  --draft-dir outputs/quality/upper_secondary_accessibility \
  --approval /local/school_access_review.json
\`\`\`

La revisione non è generata dal programma; il controllo del JSON
non autentica l'identità del revisore. In assenza di verifica reale,
i 27 valori restano \`Da verificare\`.
