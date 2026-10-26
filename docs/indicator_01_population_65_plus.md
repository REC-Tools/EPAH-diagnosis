# Indicatore 01 — Popolazione 65+

## Definizione operativa

**Quota di popolazione residente di 65 anni o più sul totale della popolazione residente comunale.**

Formula:

```text
(population_65_plus / population_total) * 100
```

La soglia è **>= 65 anni**. Nel tool usiamo quindi la denominazione `65+`, evitando l'ambiguità di “>65”.

## Fonte primaria

ISTAT — Demografia in cifre, **Popolazione residente per sesso ed età al 1° gennaio (POSAS)**.

Dataset 2026:
`https://demo.istat.it/data/posas/POSAS_2026_it_Comuni.zip`

## Anno di riferimento

1 gennaio 2026.

ISTAT specifica che la popolazione per età e sesso al 1° gennaio 2026 è una **stima** coerente con le risultanze censuarie e il bilancio provvisorio 2025.

## Unità territoriale

Comune.

## Utilizzo nella diagnosi EPAH

È un indicatore di **vulnerabilità socio-demografica** e non identifica da solo una condizione di povertà energetica.

Deve essere combinato con indicatori economici, abitativi ed energetici. Nei territori con una quota elevata di anziani, basso reddito e patrimonio edilizio inefficiente può contribuire a identificare una maggiore vulnerabilità relativa.

## Controlli di qualità

- escludere la riga ISTAT con codice età `999` (totale), per evitare doppio conteggio;
- sommare tutte le età da 65 in poi;
- verificare che `0-64 + 65+ = popolazione totale`;
- conservare codice ISTAT del Comune;
- registrare anno, fonte e carattere provvisorio/stimato del dato;
- fallire esplicitamente se uno dei 27 Comuni non è presente nel dataset.
