# Indicatore 02 — Protocollo di validazione

## Indicatore

Quota di contribuenti con reddito complessivo dichiarato **<= 15.000 euro**
sul totale dei contribuenti del Comune.

## Dataset di baseline

- Fonte: Dipartimento delle Finanze — Open Data Dichiarazioni
- Dichiarazioni: 2025
- Anno d'imposta: 2024
- Pubblicazione: 23 aprile 2026
- Classificazione: Comune

## Colonne usate

- Codice Istat Comune
- Denominazione Comune
- Regione
- Numero contribuenti
- Reddito complessivo minore o uguale a zero euro - Frequenza
- Reddito complessivo da 0 a 10000 euro - Frequenza
- Reddito complessivo da 10000 a 15000 euro - Frequenza

Se disponibili vengono conservati anche:

- Reddito complessivo - Frequenza
- Reddito complessivo - Ammontare in euro

per derivare il reddito complessivo medio come informazione contestuale.

## Controlli automatici

La pipeline fallisce se:

1. non trova l'header atteso;
2. mancano colonne obbligatorie;
3. il parser non produce righe comunali valide;
4. manca anche uno solo dei 27 Comuni;
5. un Comune compare più di una volta;
6. i contribuenti totali sono zero;
7. i contribuenti <=15.000 euro superano il totale;
8. la quota calcolata non è compresa tra 0 e 100%;
9. non vengono trovati Comuni della Regione Piemonte;
10. non vengono aggiornate esattamente 27 righe nella matrice.

## Benchmark

La quota viene calcolata anche per:

- Green Community Sinergie in Canavese;
- Piemonte;
- Italia.

Il benchmark è ponderato sul numero di contribuenti e non è una media semplice delle percentuali comunali.

## Interpretazione

L'indicatore misura vulnerabilità reddituale fiscale relativa.
Non è una soglia ufficiale di povertà e non identifica direttamente persone o famiglie in povertà energetica.
