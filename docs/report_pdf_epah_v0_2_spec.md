# EPAH Diagnosis v0.2 — specifica del report PDF e delle comunicazioni

**Scopo:** rifare `diagnostic_report.pdf` come un vero *Local Energy Poverty Diagnosis Report* di screening comunale, **sviluppato nell'ambito dell'assistenza tecnica EPAH 2026**, non come pubblicazione ufficiale della Commissione europea.

## Fonte normativa e comunicativa

Documenti messi a disposizione nel progetto:
- **EPAH Handbook 1: A Guide to Energy Poverty Diagnosis**, pp. 6–7 (sette passi), pp. 15–18 (ipotesi e indicatori), pp. 32–34 (collegare dati e ipotesi), pp. 36–38 (rapporto finale e pubblico).
- **EPAH 2026 Technical Assistance Communications Guidelines**, pp. 2–3 (EPAH nametag, versioni colore/nero/bianco/negativo; non distorcere dimensioni né eliminare testo; se EC Square Sans Pro non disponibile, Arial), pp. 4–6 (condivisione dei traguardi, comunicazione comprensibile, permessi per foto, storie e citazioni).
- **EPAH-TA26_PPT Template.pptx**: riferimento visivo per gerarchia grafica, colori e spaziatura. Non importare direttamente slide nel PDF.
- ZIP allegato: `EPAH_Color.png`, `EPAH_Black.png`, `EPAH_NegativeColor.png`, `EPAH_White.png`. Sono quattro asset riutilizzabili per la visibilità nel contesto TA; preservarli nel formato originale e mantenere il rapporto d'aspetto, senza collocarli al posto di una firma ufficiale.

## Diagnosi attuale del generatore PDF

Il modulo `src/epah_diagnosis/release_artifacts.py::write_report` produce un rapporto ReportLab essenzialmente tabellare: titolo, spiegazione generica, min/mediana/max per 8 grandezze, ripartizione SNAI, tabella fonti/caveat. Le nove mappe sono generate altrove in PNG ma **non integrate nel PDF**. Mancano un frontespizio adatto al programma TA, un sommario esecutivo, la catena *ipotesi → indicatore → evidenza*, un messaggio al decisore e una governance editoriale del brand.

**Non modificare silenziosamente i PDF già distribuiti della v0.1:** creare `write_report_v0_2` o versione configurabile e nuovi test/renders.

## Struttura v0.2 consigliata (8–12 pagine, non impaginazione rigida)

1. **Copertina:** «Diagnosi territoriale della vulnerabilità alla povertà energetica — 27 Comuni», versione/dato elaborazione, `26-IT-Unione-TA26`, esperto e soggetto beneficiario dal metadato verificato; EPAH nametag originale con dimensioni proporzionali. Didascalia: «Strumento sviluppato nell'ambito dell'Assistenza Tecnica EPAH 2026».
2. **Executive summary di una pagina:** max 3 risultati numerici *realmente calcolati*, anni, e 3 elementi da approfondire. Vietate formule «n. famiglie povere» in assenza di dati individuali.
3. **Domande / ipotesi della diagnosi:** collegamento ai 7 passi EPAH; tabella di ipotesi con fonte e robustezza (alta/media/esplorativa, mai scientificamente confermata solo da un proxy).
4. **Quadro dei nove indicatori e dei gap EPAH:** le sei categorie Handbook (Climate, Facilities/Housing, Mobility, Socio-economic, Policy, Participation). Distinguere `measured`, `historical_proxy`, `unavailable`.
5. **Risultati per temi:** 2–4 mappe selezionate automaticamente dai risultati *disponibili* e tre grafici di distribuzione o contrasto tra Comuni; tutte le mappe con fonte, anno, unità e legenda leggibile. Le nove mappe integrali rimangono nell'allegato ZIP.
6. **Lettura incrociata:** esempi di sovrapposizione descrittiva tra redditi, età, edifici, clima/servizi senza sommatoria di score o nesso causale indebito; dichiarare il problema di denominatori e vintage non allineati.
7. **Implicazioni operative:** domande concrete per FERVORES e Unione Montana, separando evidenze osservate da ipotesi da discutere.
8. **Metodi, qualità e limiti:** data/fonte/licenza, definizione e denominatore, origine geografica, ISO/CRS84 vs EPSG:32632, bias APE, comparabilità, risultati non rappresentativi delle famiglie e profilo «v0.2 technical assessment».
9. **Prossimi passi e canali:** confronto con enti territoriali, versione successiva, feedback; riferimenti al repository e ai materiali EPAH.
10. **Appendice sintetica/QR/URL:** catalogo dati e hash manifest, lista delle nove mappe; dettagli di QA in file separati anziché muri di testo.

## Comunicazione e branding (vincoli funzionali)

- EPAH **nametag** preso dalla cartella fornita (originale, proporzioni e testo invariati). Non inserire automaticamente crest/loghi UE non esplicitamente autorizzati per l'output; usare gli asset forniti e, in caso di dubbio, richiedere conferma al team comunicazione.
- La formulazione deve essere **«Sviluppato nell'ambito del programma di Assistenza Tecnica EPAH 2026»**, NON «Tool ufficiale della Commissione europea» o «validato da EPAH».
- Specificare il soggetto redattore/beneficiario effettivo; i ruoli sono metadati di build, non stringhe sparse. Il codice di assistenza tecnica `26-IT-Unione-TA26` compare in copertina e colophon.
- Presentare un breve disclaimer: «Il contenuto è elaborato nell'ambito dell'assistenza tecnica. Le analisi e le interpretazioni degli autori non rappresentano necessariamente la posizione della Commissione europea o di EPAH».
- Font leggibile: EC Square Sans Pro solo se realmente disponibile e autorizzato, altrimenti **Arial o un equivalente accessibile**. Non includere/distribuire i file font ufficiali.
- Testo in italiano, contrasto sufficiente, palette accessibile, grafici con titolo/unita/anno, pagine A4, link testuali e PDF con metadata; non usare solo il colore per codificare rischi/assenze.
- Foto: includere solo se diritto d'uso, consenso e attribuzione verificati; il PDF deve funzionare anche senza foto, video o materiali identificativi.
- Fonti EPAH citate correttamente; distinguere analisi derivata e contenuti riutilizzati (Handbook 1 CC BY 4.0 con attribuzione, senza presentare la rielaborazione come originale EPAH).
- Predisporre estrazione facoltativa di una **scheda 1 pagina per comunicazione** (tre messaggi, mappa, progetto/partner, caveat). Non fare social automation.

## Proposta di implementazione

1. Aggiungere schema `report_config_v0_2.json` con titolo, versione, `ta_code`, redattore, partner/beneficiario, `brand_assets_path`, `publication_status`, `language`, `audience`, `report_date`; validare campi obbligatori e assenza di claims non supportati.
2. Nuovo renderer `src/epah_diagnosis/report_v0_2.py` con ReportLab Platypus, cover, paginazione, intro, analisi, PNG mappe embedded, appendice, font fallback e collegamenti agli allegati. Riusare mappe già calcolate, non implementare una seconda libreria GIS.
3. Separare **dati** e **narrazione**: le affermazioni numeriche nascono da valori del profilo, non da stringhe inserite manualmente; conservare (n\), anni, denominatori, fonte e confidenza.
4. Gestire gracefully indicatori non disponibili: tabella gap con status `unavailable`, **mai 0**.
5. Test automatici: PDF generato senza immagini opzionali, logo proporzionale, titolo/codice, nessuna copertura naz. inventata, 27/27 + metadata, n. pagine sensato, assenza di clipping, rendering PNG a 150–200 DPI, controllo visivo di copertina, pagine mappe e tabella.
6. Aggiungere snapshot/golden test o controllo strutturale stabile del PDF, senza aspettarsi identità byte-per-byte da ReportLab.
7. Aggiornare il builder v0.2 e `release_manifest.json`; preservare `scripts/build_v0_1_owner_accepted.py` e il PDF pilota già distribuito.

## Condizioni di accettazione

- Produzione PDF a partire dai dati aggregati ufficiali 27 Comuni, anche con due indicatori nuovi mancanti;
- colophon EPAH-TA e codice progetto verificabili in testo estratto;
- uso corretto degli asset nametag forniti **senza stiramenti**; funzionamento con Arial;
- almeno due mappe e una tabella/grafico nel PDF, con fonte e anni;
- sintesi leggibile da amministratori + documentazione scientifica tracciabile;
- nessuna pretesa di approvazione istituzionale o EPAH oltre quelle effettive.
