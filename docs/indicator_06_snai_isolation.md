# SNAI isolation / peripherality classification

The first service-access indicator uses the official **Mappa Aree Interne 2020**
for the 2021-2027 programming cycle.

The SNAI method identifies service poles through the joint presence of:

1. a complete upper-secondary education offer;
2. a hospital with DEA level I or II;
3. a railway station with active passenger service and, in the SNAI method,
   at least the former Silver classification.

Other municipalities are classified according to effective road travel time
to the nearest pole.

Official classes:

- A: Polo
- B: Polo intercomunale
- C: Cintura
- D: Intermedio
- E: Periferico
- F: Ultraperiferico

Classes D, E and F are the official Inner Areas.

This indicator should be used as an institutional benchmark of territorial
peripherality, while the EPAH diagnosis will also calculate separate current
travel-time indicators to health, upper-secondary education and rail services.

Run:

`python scripts/finalize_snai_classification.py`

Outputs:

- `data/indicators/snai_classification_2020.csv`
- `data/indicators/snai_classification_summary_2020.csv`
- 27 validated rows in the verification matrix

## Next stage: current service travel times

For current service-access indicators, use the official ISTAT municipal
origin-destination travel-time matrices rather than straight-line distance or
a proprietary routing API.

ISTAT publishes road travel time in minutes between all Italian municipalities
using GIS and a commercial road graph. The matrix uses municipal geography at
1 January 2021 and a road graph updated to 2020.

The next three indicators will therefore be:

- minutes to nearest municipality hosting DEA I/II;
- minutes to nearest upper-secondary service municipality;
- minutes to nearest active passenger railway-station municipality.

These measures remain separate and are not immediately combined into a single
isolation score.

## PR-05: acquisizione controllata e QA (ottobre 2026)

La classificazione SNAI **2020** deriva dalla mappa ufficiale delle Aree
Interne nel ciclo 2021-2027. Le classi A-F rimangono **categorie**, non
valori numerici da sommare o confrontare linearmente.

Si usa il campo ufficiale `PROCOM_T`/equivalente come chiave comunale,
associandolo ai 27 `istat_code` del registro. Il confronto tra geografia
2020 e perimetro comunale attuale deve essere controllato e documentato.
Si richiede la copertura nazionale (almeno 7.000 righe) e una sola classe
A-F valida per ogni Comune, senza sostituzioni arbitrarie.

```bash
python scripts/prepare_territorial_context.py \
  --indicator snai_classification \
  --source-xlsx /local/20220214-mappa-ai-2020-elenco-e-classificazione-comuni.xlsx \
  --out-dir outputs/quality/snai_classification
```

L'output di bozza contiene 27 Comuni, distribuzione per classi A-F,
totale D/E/F per le Aree Interne e SHA-256 delle sorgenti/output. Tutto
resta non validato in assenza di revisione umana documentata su provenienza,
licenza, geografia 2020 e confronto campionario indipendente.

```bash
python scripts/finalize_snai_classification.py \
  --source-xlsx /local/20220214-mappa-ai-2020-elenco-e-classificazione-comuni.xlsx \
  --draft-dir outputs/quality/snai_classification \
  --approval /local/snai_approval.json
```

Il finalizzatore confronta hash e risultati ricalcolati prima di usare
l'upsert atomico sulle **sole 27 righe SNAI**. Nessuna promozione avviene
eseguendo soltanto il parser o la preparazione. L'indicatore resta
`Da verificare` finche mancano i dati ufficiali e la revisione.

