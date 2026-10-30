# EPAH Diagnosis v0.2.0 — roadmap di indicatori e metodi

**Data di definizione:** 30/10/2026. **Ambito:** gli stessi 27 Comuni della Green Community Sinergie in Canavese. **Natura:** proposta tecnica, non validazione di nuovi dati e non modifica della v0.1 pilota.

## Obiettivo

Ridurre lo scarto tra il catalogo comunale attuale (9 dimensioni) e la diagnosi descritta nell'EPAH Handbook 1, §4 (pp. 18–28) e §6–7 (pp. 32–38). Mantenere i nove campi storici comparabili e introdurre **al massimo 2 nuovi indicatori misurati realmente** nella prima iterazione v0.2; altri indicatori sono catalogati come *missing / data-needed*, mai valorizzati fittiziamente. Valutare l'aggiornabilità dei dati e l'anno prima di ogni integrazione.

### Gap tra EPAH e la v0.1

La v0.1 contiene: vulnerabilità demografica (65+), redditi dichiarati bassi, edifici prima del 1981, gradi-giorno invernali, altitudine, SNAI e tre accessibilità su elenchi di servizi selezionati.

Risultano **assenti o non ancora popolati** gli indicatori EPAH più vicini alla povertà energetica osservata:
- **Facilities/Housing:** quota abitazioni certificate in classi energetiche basse, stato/tecnologia del riscaldamento, adeguatezza dell'abitazione;
- **Socio-economic:** spesa energetica/reddito, 2M, M/2, arretrati bollette, impossibilità di riscaldare adeguatamente la casa;
- **Climate:** raffrescamento (CDD) e caldo estremo (UE/EPAH 2026);
- **Policy & Participation:** presenza di azioni, servizi e coinvolgimento della comunità (indicatori qualitativi, non inventare conteggi).

Il Handbook 1, pp. 18–22 e 24–28, raccomanda di scegliere indicatori adattati e aggiornabili, non di implementare tutti i 56. I dati socioeconomici nazionali EU-SILC non possono essere presentati come osservazioni dei singoli 27 Comuni.

## Backlog prioritizzato e condizioni per includerlo nel report

| Ordine | ID proposto | Misura e denominatore | Fonte candidata | Stato/condizione | Policy |
|---|---|---|---|---|---|
| P0 | `poor_energy_label_share` | % APE residenziali nelle classi F+G / APE residenziali validi, non % di tutte le abitazioni | Piemonte open data *APE per classe e Comune*; SIAPE ENEA | **Candidato reale, dato da acquisire e verificare**: ultimo aggiornamento, 27/27, residenziale, duplicati, validità; eventuale distinzione ACE/APE | Pubblicare solo se completo e omogeneo; mostrare N attestati e anno |
| P0 | `non_natural_gas_heating_share` oppure `heating_facilities_gap` | Quota abitazioni con vettore/impianto specifico, *denominatore dichiarato* | ISTAT censimento/CPA e fonti locali aggregate | Parser esistenti, originale da verificare e vintage potenzialmente storico | Se dati vecchi, etichettare *proxy storico*, non stima 2026 |
| P1 | `energy_expenditure_burden` | spesa energetica annua / reddito disponibile lordo o netto coerente, con unità e finestra temporale esplicite; eventuale % oltre soglia | dati aggregati messi a disposizione da enti locali / survey anonima | **Non disponibile attualmente** per 27 Comuni; redditi MEF non bastano a ricostruirlo | Non inferire da solo reddito e prezzi nazionali; non presentare 2M senza microdistribuzioni |
| P1 | `self_reported_thermal_discomfort`, `utility_arrears` | % rispondenti/utenze osservate; esplicitare campione, universo, N e bias | dati aggregati dei servizi sociali, questionario anonimo, enti locali | Solo se realmente raccolti; nessun dato personale nel tool | Mai generalizzare da campione di beneficiari a intera popolazione |
| P1 | `cooling_degree_days` / `heat_stress_days` | CDD o giorni annui UTCI oltre soglia dichiarata | Copernicus ERA5-Land/ERA5-HEAT | Codice già presente; servono veri file CDS, termini e controlli di CRS/timezone | Pubblicare se recupero reale completato; non chiamare comfort interno il clima esterno |
| P2 | `policy_and_participation` | elenco descrittivo di iniziative/partner, non graduatoria | verbali/attività EPAH territoriali | Integrare come capitolo qualitativo, non forzare nella matrice quantitativa | Dichiarare fonti e date |

### Scelta minima raccomandata per v0.2

**Indicatore nuovo principale: APE in classi F/G tra gli APE residenziali validi**, solo se fonti verificabili. Secondo: distribuzione delle fonti/impianti di riscaldamento, usando codici di acquisizione già presenti. **Terzo facoltativo**, quando disponibili dati: CDD o stress termico. Misure dirette della difficoltà economica e termica sono un **gap riconosciuto**, ma non un obbligo di produrre percentuali senza una rilevazione.

La fonte *APE per classe e Comune*, rilasciata da Regione Piemonte (CC BY 4.0), riporta metadati di modifica del 2018 nonostante la periodicità nominale mensile: non è prova che le osservazioni siano aggiornate al 2026 o includano filtri residenziali. Acquisire il CSV, verificare anno effettivo/semantica/validità e riconciliare i 27 codici. Consultare anche ENEA SIAPE, che mostra filtri comunali e dati aggiornati, ma non presumere esista un endpoint di download aggregato accessibile.

- Piemonte APE per Comune: https://www.dati.gov.it/node/view-dataset/dataset?id=63401619-1a9f-4382-8399-84c20c59dad0
- ENEA SIAPE: https://siape.enea.it/filtro-dati
- EPAH Observatory: https://energy-poverty.ec.europa.eu/observatory
- EPAH 2026 climate/health/mobility: https://energy-poverty.ec.europa.eu/observatory/publications/expanding-energy-poverty-measurement-eu-integrating-new-climate-health-and
- EPAH 2026 housing: https://energy-poverty.ec.europa.eu/observatory/publications/residential-energy-efficiency-and-energy-poverty-eu-building-conditions
- Manuale ricevuto: EPAH Handbook 1, pp. 18–28, 32–38.

## Riuso esterno Python/GIS (valutazione, non dipendenza aggiunta automaticamente)

1. **EP-0** — software per vulnerabilità socioenergetica e building data, **Apache-2.0**, source su Zenodo: https://zenodo.org/records/15910447 ; utile per schema di import GeoJSON, dati edificio e separazione fra vulnerabilità e retrofit. Non adottare senza verifica di complessità, dipendenze e perimetro.
2. **NBEM** — modello Python EPC + catasto, **MIT**: https://github.com/CarlosBeltranVelamazan/NBEM ; prendere spunto da ETL EPC, geocoding e QA, non simulare un modello catastale spagnolo per Canavese.
3. **private-rental-efficiency** — analisi Python/R EPC e bias di copertura per piccole aree: https://github.com/CaitHRobinson/private-rental-efficiency ; prendere spunto da denominatori e incertezza; licenza di riuso del codice **da verificare**, non copiarlo.
4. **Energy-poverty-US** — 10 dimensioni di hardship economica, fisica e comportamentale: https://github.com/criscres/Energy-poverty-US ; ispirazione *concettuale* (dati e modello USA non trasferibili direttamente).

**Non introdurre** deep-learning a label sintetiche, aggregazioni arbitrarie in un indice composito né modelli energetici a scala di singolo edificio se non esistono dati adeguati.

## Definition of done

- 27/27 codici comunali, unità, fonte, anno e **denominatore** per ciascun nuovo indicatore; classificare assenti come `unavailable`.
- Criteri minimi di coverage espliciti; se il dataset pubblicabile è solo storico, documentare chiaramente data e bias.
- Test con fixture sintetiche, confronto di campioni reali agli originali, hash SHA-256 e manifest.
- Matrice/catalogo v0.1 non alterati retroattivamente; output v0.2 separato.
- Nuovi indicatori disponibili nel **rapporto v0.2 con evidenza, limiti e fonte**, mai come dato misurato se mancanti.
- Unione Montana e FERVORES possono annotare osservazioni metodologiche, senza sovrascrivere la decisione tecnica già registrata.

## PR consigliate

- **PR v0.2-A**: adapter APE Piemonte + validazione vintage/27 Comuni/denominatore, schema long e status dati.
- **PR v0.2-B**: secondo indicatore (impianti/combustibili, se originale disponibile), aggancio catalogo/QA.
- **PR v0.2-C**: nuovo report PDF EPAH-TA, mantenendo intatta la v0.1 (vedere [specifica PDF](report_pdf_epah_v0_2_spec.md)).
- **PR v0.2-D**: build riproducibile e collaudo del bundle v0.2.
