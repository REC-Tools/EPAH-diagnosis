# Criteri per considerare un indicatore "chiuso"

Un indicatore della diagnosi EPAH è considerato **chiuso** quando soddisfa tutti i criteri seguenti:

1. **Definizione operativa** non ambigua.
2. **Fonte primaria** identificata e documentata.
3. **Scala territoriale comunale** disponibile per tutti i 27 Comuni.
4. **Anno di riferimento** uniforme.
5. **Metodo di calcolo** replicabile nel repository.
6. **Controlli di completezza**: nessun Comune mancante.
7. **Controlli di coerenza** sul numeratore e denominatore.
8. **Qualità e limiti** del dato documentati.
9. **Benchmark territoriale** calcolato almeno per Green Community, Piemonte e Italia quando applicabile.
10. **Matrice di verifica aggiornata** a `Dato validato`.
11. **Output tabellare** salvato in `data/indicators/`.
12. **Procedura di aggiornamento** automatizzabile e ripetibile.

## Indicatore 01 — Popolazione 65+

Con l'esecuzione di `scripts/finalize_population_65_plus.py`, l'indicatore soddisfa i criteri sopra:

- fonte: ISTAT POSAS;
- data di riferimento: 1 gennaio 2026;
- formula: residenti di età >=65 / residenti totali * 100;
- copertura: 27/27 Comuni richiesta;
- benchmark: Green Community, Piemonte, Italia;
- aggiornamento della matrice: 27 righe portate a `Dato validato`;
- limitazione principale: il dato per età e sesso al 1 gennaio 2026 è una stima ISTAT in linea con le risultanze censuarie e il bilancio provvisorio 2025.

La classificazione rispetto alla media Green Community è **descrittiva** e non deve essere interpretata come classificazione di povertà energetica.
