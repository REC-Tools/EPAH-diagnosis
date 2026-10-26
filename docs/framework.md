# Framework di diagnosi territoriale EPAH

## Scopo e perimetro
Il progetto supporta la diagnosi *territoriale* della povertà energetica nei 27 Comuni della Green Community Sinergie in Canavese. Produce evidenze aggregate, confrontabili e verificabili per orientare approfondimenti e azioni locali. **Non** stima la quota di famiglie in povertà energetica e non classifica individui o nuclei familiari. È un'applicazione locale ispirata all'approccio EPAH, non una certificazione EPAH.

## Principi
1. Separare osservazioni, indicatori calcolati, proxy, interpretazioni e decisioni.
2. Documentare per ogni misura fonte, definizione, unità, anno, geografia, metodo, qualità, incertezza e limitazioni.
3. Non sostituire valori mancanti con zero. Non equiparare disponibilità del dato a validazione.
4. Conservare gli anni originali: i confronti fra vintage diversi vanno segnalati, non presentati come sincronizzati.
5. Usare codici ISTAT comunali come chiavi di raccordo quando disponibili; registrare cambiamenti amministrativi e geografie di riferimento.
6. Distinguere i risultati osservati dalle ipotesi; sottoporre a revisione umana soglie, pesi e interpretazioni.

## Cinque livelli logici
| Livello | Contenuto | Esempi | Interpretazione |
| --- | --- | --- | --- |
| 1. Evidence sources | Dataset ufficiali e metadati di origine | ISTAT, MEF, MIM, Regione Piemonte | Evidenza grezza; non un indicatore |
| 2. Territorial descriptors | Caratteristiche del territorio | altitudine, classificazione SNAI, accessibilità stradale | Contesto e possibili fattori aggravanti |
| 3. Vulnerability indicators | Proxy e misure di vulnerabilità pertinenti alla diagnosi | popolazione 65+, bassi redditi dichiarati, vetustà edilizia | Segnali indiretti; non misure individuali |
| 4. Diagnostic dimensions | Letture tematiche di indicatori e descrittori | sociale/demografica, economica, abitativa, climatica/energetica, accessibilità | Dimensioni analitiche, non automaticamente punteggi |
| 5. Diagnosis outputs | Evidenze comunali per discussione e decisione | tabelle, mappe, profili, report | Screening e prioritizzazione da verificare con attori locali |

Un indicatore può contribuire a una dimensione senza diventare una misura diretta della povertà energetica. In particolare, accessibilità ai DEA, scuole, altitudine e SNAI **non** sono equivalenti al reddito o al fabbisogno energetico domestico.

## Regole di confronto
- Preferire indicatori con denominatore e universo chiaramente specificati.
- Benchmark Green Community: esplicitare se è una media ponderata (e con quale denominatore) o non ponderata.
- Piemonte e Italia: calcolare solo se definizione, geografia e periodo sono confrontabili.
- Direzione di vulnerabilità: specificarla per ciascun indicatore; 'più alto' non significa sempre 'peggiore'.
- Sovrapposizioni di segnali oltre una soglia o benchmark sono analisi **descrittive**, non stime di famiglie colpite.
- Non proporre un indice unico o pesi universali senza una decisione metodologica documentata e analisi di sensibilità.

## Governance metodologica
La definizione di indicatori, soglie, periodi, dimensioni e criteri di validazione richiede revisione umana via PR. I cambiamenti che modificano comparabilità o interpretazione sono versionati e spiegati. L'automazione può segnalare differenze e preparare PR, non approvare autonomamente risultati metodologici.

## Stato attuale e lavori successivi
Questa pagina è un **contratto proposto**, non la descrizione di funzioni già implementate. La matrice e il modello applicativo attuali includono tre indicatori di base; altre schede e pipeline documentano ulteriori misure. Il catalogo metodologico di otto voci è in [indicator_catalog.md](indicator_catalog.md). L'integrazione nella CLI e la migrazione additiva della matrice sono fasi successive. Consultare [pipeline.md](pipeline.md) e [indicator_completion_criteria.md](indicator_completion_criteria.md).
