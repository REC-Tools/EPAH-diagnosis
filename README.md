# EPAH Diagnosis — Sinergie in Canavese

Tool operativo per supportare la diagnosi locale della povertà energetica nei 27 Comuni della Green Community **Sinergie in Canavese**.

## Obiettivo della v0.1

La prima versione implementa un approccio incrementale coerente con la metodologia EPAH:

- partire da pochi indicatori locali, aggiornabili e verificabili;
- mantenere separati **dato**, **fonte**, **qualità** e **limiti**;
- usare proxy territoriali per descrivere la vulnerabilità, senza identificare singole famiglie come energy poor;
- rendere la struttura estendibile fino al set completo di 12 indicatori.

### Indicatori prioritari

1. **Popolazione ≥65 anni** — ISTAT
2. **Vulnerabilità reddituale** — MEF, Dichiarazioni fiscali
3. **Vetustà del patrimonio abitativo** — ISTAT, Censimento/patrimonio edilizio

Il file `data/verification_matrix.csv` contiene **81 verifiche iniziali**: 27 Comuni × 3 indicatori, tutte impostate su `Da verificare`.

## Stati della verifica

`Da verificare` → `Fonte individuata` → `Dato disponibile` → `Dato acquisito` → `Dato validato`

Quando il dato non può essere reperito: `Non disponibile`.

## Struttura

- `data/municipalities.csv` — perimetro dei 27 Comuni
- `data/verification_matrix.csv` — matrice operativa
- `src/epah_diagnosis/model.py` — definizioni indicatori e stati
- `src/epah_diagnosis/cli.py` — generazione e controllo della matrice
- `tests/` — test minimi

## Uso

```bash
python -m epah_diagnosis.cli init-matrix \
  --municipalities data/municipalities.csv \
  --output data/verification_matrix.csv
```

Verifica della matrice:

```bash
python -m epah_diagnosis.cli validate-matrix data/verification_matrix.csv
```

## Prossimo sviluppo

1. acquisizione automatizzata dei dati demografici ISTAT;
2. acquisizione dei redditi dichiarati MEF;
3. verifica della disponibilità comunale dei dati sul patrimonio edilizio;
4. normalizzazione dei tre indicatori per la prima mappa di vulnerabilità;
5. successiva estensione agli altri 9 indicatori EPAH/locali.

> La soglia per la “vulnerabilità reddituale” e la soglia temporale per gli “edifici vecchi” non sono ancora fissate: verranno definite solo dopo aver verificato la struttura effettiva dei dataset disponibili.
