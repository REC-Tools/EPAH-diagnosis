# Indicatore 03 — Patrimonio edilizio

## Fonte definitiva

La pipeline utilizza il dataset ufficiale ISTAT **Variabili censuarie 2011**
associato alle basi territoriali:

- pagina: https://www.istat.it/notizia/basi-territoriali-e-variabili-censuarie/
- file: https://www.istat.it/storage/cartografia/variabili-censuarie/dati-cpa_2011.zip

Il file contiene valori assoluti a livello di sezione di censimento. La pipeline
li aggrega per codice ISTAT del Comune.

## Indicatore principale

**Quota di edifici residenziali costruiti prima del 1981**

Formula:

```
(E8 + E9 + E10 + E11 + E12) / E3 * 100
```

dove:

- E3 = edifici ad uso residenziale;
- E8 = costruiti prima del 1919;
- E9 = 1919-1945;
- E10 = 1946-1960;
- E11 = 1961-1970;
- E12 = 1971-1980;
- E13 = 1981-1990;
- E14 = 1991-2000;
- E15 = 2001-2005;
- E16 = dopo il 2005.

## Perché questa definizione

Rispetto alla precedente soluzione 8milaCensus/A10:

1. usa una fonte ISTAT nazionale ancora esposta nella pagina delle variabili
   censuarie;
2. evita scraping HTML e problemi TLS/403 del portale 8milaCensus;
3. utilizza valori assoluti e quindi permette aggregazioni ponderate corrette;
4. misura una fascia molto più ampia del patrimonio edilizio antecedente al 1981;
5. conserva tutte le classi di epoca per analisi future.

## Benchmark

I benchmark Green Community, Piemonte e Italia sono calcolati con la stessa
formula sui valori assoluti:

```
somma edifici pre-1981 / somma edifici residenziali
```

Non viene quindi usata la media semplice delle percentuali comunali.

## Interpretazione

L'anno di costruzione è un **proxy di vulnerabilità energetica del patrimonio**.
Non implica che tutti gli edifici precedenti al 1981 siano inefficienti: alcuni
possono essere stati riqualificati, mentre edifici più recenti possono comunque
avere prestazioni non ottimali.

La variabile non sostituisce dati APE/SIAPE, consumi reali o informazioni sugli
interventi di riqualificazione.

## Stato di conservazione

La variabile sullo stato di conservazione potrà essere aggiunta come indicatore
complementare in una fase successiva. La v0.1 privilegia l'indicatore di epoca
di costruzione, per il quale il dataset nazionale espone classi e valori assoluti
direttamente aggregabili.

## Stato operativo PR-04

Il codice implementa una separazione tra acquisizione, verifica tecnica
e revisione scientifica. Il file originario ISTAT CPA 2011 non e incluso
nella repository; nessun output statistico viene presentato come
validato fino alla revisione dell'archivio e dei 27 codici comunali.

Eseguire `scripts/prepare_building_stock.py` su uno ZIP ufficiale
locale; solo successivamente, con approvazione umana tracciata,
eseguire `scripts/finalize_building_stock_single_source.py`.
I benchmark sono ponderati e l'anno 2011 non viene confuso
con lo stato energetico degli edifici nel 2026.
