# Confronto tecnico CIT su 26/27 Comuni - solo QA

Il 30/10/2026 i due parser CIT con \`--quarantine-conflicts\` sono terminati correttamente sui due CSV originali Regione Piemonte con SHA verificati. Entrambi indicano \`26/27\` e Pont Canavese (ISTAT \`001199\`) escluso per conteggi **discordanti**, senza alcuna risoluzione artificiale.

- Combustibili, 2 righe di Pont Canavese: 490 e 239 gruppi; chiavi PONT CANAVESE e PONT-CANAVESE, linee 1151 e 1152.
- Età generatori, 2 righe Pont: 2246 e 866 gruppi; codice ISTAT 001199 in entrambe, linee 976 e 1280.
- Età: 6881 gruppi nell'intervallo che attraversa la soglia dei 20 anni. Questa **incertezza temporale dei 26 Comuni**, distinta dal conflitto di Pont, dev'essere espressa tramite limiti inferiore/superiore. Non equivale a 6881 record duplicati.
- Data \`2026-10-30\`: riferimento analitico dichiarato localmente, non snapshot ufficiale dei dataset.

## Nuovo comando dopo merge

\`\`\`powershell
python scripts/build_v0_2_cit_quarantine_comparison.py
\`\`\`

Legge solo le cartelle tecniche già prodotte:
- \`outputs/quality/cit_fuel_quarantine_v02\`;
- \`outputs/quality/cit_age_quarantine_v02\`.

Produce una nuova cartella \`outputs/quality/cit_quarantine_comparison_v02\` con:
- \`cit_26_municipality_technical_comparison.csv\`: valori per 26 Comuni, due denominatori distinti, quota combustibili e limiti di età;
- \`cit_26_qa_summary.json\`: numeratori, denominatori, aggregati ponderati, medie comunali non ponderate, 6881 gruppi incerti se l'input è quello verificato;
- \`cit_pont_canavese_source_review.json\`: due casi conflittuali con righe, SHA e vettori delle categorie nativi;
- \`README.md\`: divieto di pubblicare i dati come validati.

Il codice controlla SHA delle due fonti e degli estratti, 26 codici coincidenti, denominatori, percentuali, conservazione del conflitto, limiti di età e status obbligatoriamente \`technical_incomplete_do_not_publish\`. Non emette PNG/PDF e non modifica la matrice canonica o la release v0.1.

**Non invocare \`build_v0_2_cit_preview.py\` con questi file.** Prima di produrre le mappe ufficiali serve risolvere il conflitto mediante chiarimento documentato con Regione Piemonte / CSI Piemonte (contatto del catalogo pubblico: riuso@dati.piemonte.it).
