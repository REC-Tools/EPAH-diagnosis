# Revisione empirica della v0.2 - serie comunali coincidenti

L'audit visivo e di coerenza del pacchetto tecnico locale v0.2 del 5
novembre 2026 ha trovato **27 su 27 valori numericamente identici** fra
`upper_secondary_access_minutes` e `rail_access_minutes`.

Questi due indicatori conservano **definizioni e destinazioni distinte**,
ma non forniscono due segnali statistici indipendenti nel set di 27
osservazioni corrente. Questa coincidenza non dimostra da sola un errore:
puo dipendere dai poli/destinazioni, dal metodo di accessibilita o da
caratteristiche del territorio. Non rimuovere né sostituire valori in
assenza di un riesame delle fonti.

La v0.2 segnala quindi automaticamente le coppie esattamente coincidenti
in `diagnostic_facts_v0_2.json`, `analysis_summary_v0_2.json`,
nel rapporto PDF e nella dashboard offline, pur mantenendo le 28 coppie
descrittive e tutte le osservazioni originali. L'identita numerica
non e una validazione scientifica.

## Azioni per un revisore

- Verificare originali e criteri per le destinazioni di scuole
  superiori e stazioni ferroviarie, incluso eventuale servizio
  sostitutivo e periodo di riferimento.
- Documentare il perche del 27/27 e le implicazioni
  prima di interpretare le co-occorrenze.
- Controllare che la riproduzione del PDF e della dashboard
  riporti la nota e non consideri la doppia serie
  due evidenze indipendenti.
- Conservare il bundle v0.2 precedente come evidenza storica;
  rigenerare nuovi output in nuove directory dopo la modifica.

## QA editoriale ancora richiesta

L'audit visivo del rapporto di 9 pagine e delle 27 schede A4
non ha evidenziato tagli di contenuto. Diversi paragrafi occupano
solo una piccola parte della pagina e molte etichette italiane
usano trascrizioni senza accenti. Prima di divulgazione istituzionale
servono una revisione redazionale, la verifica della leggibilita
delle mappe e le firme scientifiche e istituzionali esplicite.

Questo documento non contiene dati personali né modifica
la matrice canonica.
