# Promozione dati prioritari 81/81: audit 29 ottobre 2026

## Risultati

I tre originali forniti dall'utilizzatore sono stati verificati in
una seconda lettura indipendente dai parser del progetto: 27 codici
ISTAT, 81 corrispondenze e 13 controlli totali con esito positivo.

- DPR 412/1993 Allegato A consolidato 09/08/2016: 27 GG, zona
  e quota casa comunale ricontrollati. Anomalia della *trascrizione
  storica* di Pratiglione: 711 m, testo consolidato 2016: **611 m**;
  GG 3270 invariato.
- ISTAT altimetria 2021: **27 valori** di quota media territoriale,
  distinti dall'altitudine della casa comunale, 7904 righe nazionali.
- SNAI 2020: **27 classi** A-F ufficiali, non scala numerica, 7903
  righe nazionali; 1 C, 17 D, 8 E, 1 F.

I byte dei documenti originali non sono committati per evitare
doppioni con le pubblicazioni istituzionali. Il file
\`data/quality/priority_81_source_evidence.json\` riporta gli SHA-256
esatti dei PDF/XLSX scaricati. I due CSV di riferimento e i rispettivi
riepiloghi sono identici ai CSV generati dal programma di audit
(confrontare i quattro SHA-256 in CI).

## Approvazione e tracciabilita

L'utente ha **espresso l'approvazione esplicita in conversazione** il
29 ottobre 2026. Questa PR prepara il diff \`Dato validato\` per 81
righe, mantenendo le 81 righe della matrice di base inalterate.

**Per completare la tracciabilita**, il committente/revisore deve
verificare il dossier e usare il controllo **Approve** della PR in
GitHub, oppure lasciare un commento firmato e persistente nel thread
della PR. Fino ad allora il record GitHub non e un'attestazione di
revisione indipendente e la PR resta **draft**. Il link alla PR e
l'autore del review verranno conservati come evidenza duratura dopo
approvazione autentica, non inventati nel codice.

Non modifichiamo \`config/release_reviews_v0_1.json\` e **non**
promuoviamo la maturita metodologica degli altri sei indicatori.
Il release gate rimane \`NOT READY\` per le 108 osservazioni ancora
mancanti e le review metodologiche delle nove dimensioni.

## Punti da controllare prima del merge

1. \`data/verification_matrix.csv\`: solo gli 81 record HDD/altitudine/
   SNAI sono passati a \`Dato validato\`, senza modificare la baseline
   storica delle 81 prime righe.
2. \`tests/test_priority_81_promotion.py\`: verifica hash esatti dei
   quattro file originati dai dati ufficiali e la corrispondenza
   dei 27 valori comunali con la matrice.
3. \`config/indicators.json\` ancora EXPERIMENTAL: modifica futura
   *solo* con metodologia e revisione effettive.
4. Pubblicazione di un GitHub review firmato, non di un'approvazione
   autogenerata in JSON.

## Prossima fase

Fase B: acquisizione e QA del patrimonio edilizio ISTAT CPA 2011.
Fase C: verifica dei 27 percorsi DEA, scuola, ferrovia su matrici
stradali ufficiali e cataloghi servizi, con attenzione alle date e
ai confini regionali.
