# Territorial isolation: proposed methodology

## Why include isolation in the EPAH diagnosis

EPAH explicitly treats mobility as a relevant dimension of energy poverty.
The EPAH diagnosis handbook notes that rural and urban areas provide different
mobility opportunities and that fossil-fuel-dependent mobility can worsen the
ability of vulnerable households to reach essential services such as healthcare
and education.

The 2026 EPAH measurement update further integrates mobility and transport
vulnerability into the broader energy-poverty framework.

Transport-poverty research also treats accessibility as distinct from
affordability and availability. For a rural Green Community, access to
essential services should therefore be represented explicitly rather than
collapsed immediately into a single score.

## Recommended structure for Sinergie in Canavese

Keep five separate variables during the diagnostic phase:

1. road travel time to a health-service reference point;
2. road travel time to an upper-secondary education service point;
3. road travel time to a passenger railway station;
4. mean municipal altitude;
5. official SNAI / Inner Areas class or travel time to the nearest service pole.

Do not combine these into a weighted isolation score yet.

## Service definitions

### Health

Preferred SNAI-compatible definition:
nearest hospital with DEA level I or II.

Primary official source:
Italian Ministry of Health, emergency hospital network / NSIS.

A broader sensitivity analysis may later use the nearest emergency department
or territorial health facility, but it should be kept separate from the SNAI
definition.

### Education

Preferred SNAI-compatible definition:
nearest municipality / service cluster offering a complete upper-secondary
education choice.

The SNAI methodology approximates this through the simultaneous availability
of a liceo and technical/professional education.

Primary official source:
Ministry of Education Open Data.

### Rail

Two useful variants should be distinguished:

- SNAI-compatible historical definition: nearest station at least Silver;
- current operational definition: nearest active passenger railway station.

RFI has replaced the former Platinum/Gold/Silver/Bronze system with a new
station classification, so the two measures should not be silently mixed.

Primary official source:
Rete Ferroviaria Italiana station data.

## Distance measure

The preferred measure is **road travel time in minutes**, not straight-line
distance.

For each municipality, use the municipality hall / municipal-seat point as the
initial origin. This is consistent with the territorial logic used in Italian
Inner Areas work and is reproducible.

If future data allow, a stronger version can use population-weighted origins
or inhabited localities, which would better represent large mountain
municipalities with dispersed settlements.

## Altitude

Mean municipal altitude is retained as a separate territorial exposure
indicator.

Primary source:
ISTAT, municipal altitude indicators, published April 2026 and based on
NASADEM_HGTv001 and 2021 territorial boundaries.

Altitude is not treated as a substitute for accessibility. Two municipalities
at similar mean altitude can have very different access to services, roads and
public transport.

## Interpretation

The result should initially be a dashboard / profile, not a single score.

Example:

- mean altitude: 1,150 m
- travel time to DEA hospital: 52 min
- travel time to upper-secondary service point: 41 min
- travel time to passenger station: 48 min
- SNAI class: peripheral

This is more transparent and policy-useful than a single arbitrary isolation
index.

## PR-05: acquisizione controllata e QA (ottobre 2026)

La pipeline separa **preparazione tecnica** e **promozione dei dati**. Si usano
gli identificativi ISTAT comunali a sei cifre (`istat_code`) e si verificano
anche i nomi normalizzati; non sono ammessi join esclusivamente testuali.

Fonte: file originale ISTAT
`Altimetria_Comuni-al-31_12_2021.xlsx` (geografia comunale 2021).
La media altimetrica territoriale non e l'altitudine della sede comunale.

```bash
python scripts/prepare_territorial_context.py \
  --indicator mean_altitude \
  --source-xlsx /local/Altimetria_Comuni-al-31_12_2021.xlsx \
  --out-dir outputs/quality/mean_altitude
```

Sono richiesti almeno 7.000 record nazionali, 27 codici corrispondenti,
assenza di codici duplicati, valori finiti e altitudine media entro le
eventuali quote minime e massime. L'output include tabella di 27 Comuni,
statistiche descrittive non ponderate e manifest con SHA-256 dei byte
effettivi del file originale e dei risultati.

**Non modifica la matrice.** Per promuovere i 27 valori, occorre una revisione
umana effettiva di origine, licenza, geografia 2021 versus anagrafica 2026,
e un confronto campionario documentato con l'XLSX ISTAT. Si archivia un JSON
di approvazione con identificativi, hash del file e degli output, revisore,
data, URL HTTPS della prova, note e quattro attestazioni esplicite
(`source_authenticity_reviewed`, `historical_geography_reviewed`,
`license_reviewed`, `independent_sample_reviewed`).

```bash
python scripts/finalize_mean_altitude.py \
  --source-xlsx /local/Altimetria_Comuni-al-31_12_2021.xlsx \
  --draft-dir outputs/quality/mean_altitude \
  --approval /local/altitude_approval.json
```

La verifica strutturale del JSON **non autentica** l'approvazione: la revisione
deve essere effettivamente eseguita e tracciata. Fino ad allora
`mean_altitude` resta `Da verificare` e la release v0.1 e bloccata.

