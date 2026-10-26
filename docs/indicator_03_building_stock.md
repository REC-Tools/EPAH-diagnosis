# Indicatore 03 — Patrimonio edilizio

## Scelta metodologica

Per mantenere il livello territoriale **comunale**, la baseline utilizza ISTAT
**8milaCensus / Censimento 2011**.

Il Censimento permanente 2021 pubblica l'epoca di costruzione delle abitazioni
a livello regionale e provinciale, ma non con lo stesso dettaglio a livello comunale.
Per questo motivo non vengono interpolati o attribuiti ai Comuni valori provinciali.

## Indicatore principale

**Consistenza delle abitazioni storiche occupate**

Definizione ISTAT:

> rapporto percentuale tra le abitazioni occupate costruite prima del 1919
> e il totale delle abitazioni occupate.

Nel repository resta associato all'identificativo storico
`old_building_stock`, ma la definizione operativa è resa esplicita.

## Indicatore complementare

**Incidenza degli edifici in pessimo stato di conservazione**

Rapporto percentuale tra edifici residenziali utilizzati in pessimo stato
e totale degli edifici residenziali.

Il valore viene conservato nello stesso dataset perché aggiunge una dimensione
fisica utile alla lettura del patrimonio.

## Perché non usiamo "% edifici pre-1981" come baseline comunale

La distribuzione 2021 per epoca di costruzione è disponibile ufficialmente per
regioni e province. Una quota comunale pre-1981 richiederebbe invece una fonte
2011 di dettaglio o un'elaborazione ulteriore dei microdati/tavole censuarie.

Per la v0.1 preferiamo un indicatore comunale ufficiale già definito da ISTAT,
evitando stime territoriali non osservate.

## Limiti

- anno di riferimento 2011;
- un edificio o'abitazione antica può essere stata riqualificata;
- lo stato di conservazione non equivale alla prestazione energetica;
- l'indicatore non sostituisce APE/SIAPE o dati sui consumi;
- il benchmark della Green Community è, in questa versione, una media semplice
  dei 27 valori comunali perché la pagina 8milaCensus espone l'indicatore e non
  i denominatori assoluti necessari per una media ponderata.

## Utilizzo nella diagnosi

L'indicatore va letto congiuntamente a:

1. popolazione >=65 anni;
2. vulnerabilità reddituale MEF;
3. successivi indicatori energetici e climatici.

Non viene usato da solo per identificare famiglie in povertà energetica.
