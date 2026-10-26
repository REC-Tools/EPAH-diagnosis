# Criteri di completamento e validazione degli indicatori

## Distinguere tre esiti
1. **Dato acquisito**: esiste un valore grezzo/derivato, ma non è ancora stato verificato.
2. **Dato validato**: il valore riferito a Comune, indicatore e periodo ha superato i controlli previsti.
3. **Indicatore metodologicamente approvato**: definizione, interpretazione e limiti sono stati riesaminati; è distinto dallo stato del singolo dato. La codifica formale della maturità è proposta in [pipeline.md](pipeline.md) e rinviata alla PR B.

Un indicatore non è automaticamente 'chiuso' perché tutte le righe della matrice sono `Dato validato`.

## Checklist per la chiusura operativa
1. Definizione, numeratore, denominatore e universo non ambigui.
2. Fonte primaria, licenza/condizioni d'uso e versione documentate.
3. Copertura 27/27 Comuni oppure eccezioni esplicite; niente sostituzioni tacite.
4. Anno di riferimento chiarito e confronti fra anni diversi segnalati.
5. Metodo replicabile e collegato alla versione del codice.
6. Assenza di duplicati nelle chiavi Comune–indicatore–periodo.
7. Controlli su range, unità, valori mancanti e denominatori.
8. Qualità, incertezza, limiti e natura di proxy dichiarati.
9. Benchmark Green Community, Piemonte e Italia **quando applicabili e comparabili**, con pesi/denominatore.
10. Stato della matrice aggiornato coerentemente con le evidenze QA.
11. Output tabellare localizzabile o procedura di rigenerazione esplicita.
12. Procedura di aggiornamento verificabile.
13. Ruolo diagnostico e direzione di interpretazione esplicitati.
14. Revisione metodologica umana per soglie, pesi e significato del risultato.

Questa checklist è un **obiettivo di qualità**; non è ancora interamente verificata in automatico dalla CI.

## Esempio: popolazione 65+
- Fonte ISTAT POSAS, riferimento 1 gennaio 2026.
- Formula: residenti 65+ / residenti totali × 100.
- Interpretazione: proxy demografico, non misura diretta di povertà energetica.
- Limite: dati 2026 basati su stime/provvisorietà secondo la fonte.
- La verifica dello stato delle 27 osservazioni e degli output va fatta sullo snapshot effettivamente prodotto: la mera esecuzione di `scripts/finalize_population_65_plus.py` non dimostra da sola il superamento di tutti i criteri.
