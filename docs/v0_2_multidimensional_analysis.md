# V0.2 | Analisi multidimensionale descrittiva

Confronto comunale **non causale e senza indice sintetico**
basato sugli otto indicatori numerici già contenuti nel
bundle pilota v0.1 verificato. SNAI rimane categoriale.

~~~powershell
uv run --locked epah analysis v0.2 --bundle outputs/v0.1.0-pilot --out-dir outputs/v0.2-multidimensional-analysis
~~~

La destinazione deve essere nuova. Produce:

- `municipality_comparison_v0_2.csv`: 27 Comuni, codici ISTAT,
  valori, anno, mediana comunale, scarto e flag sopra/sotto
  mediana **per ciascuna dimensione indipendente**.
- `pairwise_overlap_v0_2.csv`: 28 coppie distinte di
  indicatori e conteggi dei Comuni sopra entrambe le
  mediane; non è un indice di vulnerabilità.
- `analysis_summary_v0_2.json`: regola, limiti e copertura.
- `analysis_manifest_v0_2.json`: hash degli output e
  del bundle originale.

Le mediane si calcolano sui **27 Comuni senza pesatura**,
usando i valori non arrotondati per la classificazione;
un valore uguale alla mediana **non** risulta sopra.
I periodi, i denominatori e il significato delle
dimensioni cambiano: `above_median` non significa
necessariamente rischio maggiore, povertà misurata o
necessità certa di intervento.

Nessun dato CIT quarantinato è incluso. Non si selezionano
beneficiari e non si attribuiscono condizioni a famiglie.
Lo status resta `technical_draft_do_not_publish`.
