# Contratto logico della pipeline

## Flusso
```text
SOURCE REGISTRY → ACQUISITION → NORMALISATION → INDICATOR
                                           ↓
                              VALIDATION / QA
                                           ↓
                                      BENCHMARK
                                           ↓
                                   DIAGNOSTIC LAYER
                                           ↓
                               MAPS / TABLES / REPORT
```
Il diagramma indica responsabilità logiche, **non** una pipeline orchestrata già implementata end-to-end.

## Contratti per fase
| Fase | Input | Output minimo | Condizione di passaggio |
| --- | --- | --- | --- |
| Fonte | URL ufficiale, dataset, licenza/versione | identificativo, titolare, URL, periodo | fonte verificabile e utilizzabile |
| Acquisizione | origine e versione esplicite | copia o riferimento al dato originario, data di download, esito | non accettare HTML o errori come CSV |
| Normalizzazione | schema originale, geografia | tabella con codici comunali, tipi/unità, mapping di colonne | 27 Comuni attesi verificati; duplicati e mancanti dichiarati |
| Calcolo indicatore | definizione, numeratore/denominatore | valore per Comune e anno, unità, metodo | controlli di range, denominatori, coerenza |
| QA | valori, fonte, periodo | risultati dei controlli e limiti | nessun errore bloccante irrisolto |
| Benchmark | dati con definizioni compatibili | benchmark dichiarato con metodo/denominatore | comparabilità dimostrata oppure benchmark omesso |
| Diagnosi/output | indicatori + descrittori + metadati | tabelle/mappe/profili con note | nessuna inferenza impropria su famiglie |

## Tracciabilità minima di ciascun risultato
Provenienza della fonte e del dataset; anno di riferimento e, se diverso, di pubblicazione; versione/snapshot o checksum quando disponibile; codice ISTAT del Comune e versione dei confini; definizione e formula; unità e denominatore; eventuale trattamento dei mancanti; esito QA; data di elaborazione e commit/codice usato; avvertenze interpretative. Questi sono **requisiti di progetto** da realizzare progressivamente, non campi che i CSV correnti già garantiscono.

## Due assi di stato, da non confondere
**Stato del dato**, già rappresentato in italiano nella matrice: `Da verificare`, `Fonte individuata`, `Dato disponibile`, `Dato acquisito`, `Dato validato`, `Non disponibile`. Lo stato riguarda la specifica osservazione per Comune/indicatore/periodo e non certifica da solo la metodologia.

**Maturità dell'indicatore**, *proposta per la PR B* e non ancora implementata:
- `PROPOSED`: definizione candidata, non approvata;
- `EXPERIMENTAL`: procedura in prova, limiti aperti;
- `OPERATIONAL`: definizione, procedura e controlli replicabili;
- `VALIDATED`: approvazione metodologica e riesame documentato;
- `RETIRED`: non più usato, mantenuto per tracciabilità.

La maturità non deve essere dedotta automaticamente da `Dato validato`. A ogni aggiornamento annuale il dato torna a richiedere QA anche se la metodologia resta approvata.

## Errori e revisioni
Un URL irraggiungibile, uno schema mutato, un Comune mancante, un denominatore nullo o una differenza inattesa sono condizioni da registrare; non autorizzano valori inventati. L'assenza di dati va dichiarata. Modifiche a metodi, fonti sostitutive, soglie, direzione e benchmark richiedono PR e revisione umana.

## Output e versionamento
Attualmente coesistono output generati localmente e file versionati. **Non presumere** che ogni artefatto descritto nelle PR sia presente in `main`. La policy è definita in [data_contract.md](data_contract.md) e il formato del manifest in [provenance.md](provenance.md). Si tratta di regole **proposte**: percorsi, manifest automatici e migrazioni sono ancora da implementare. Documentare esplicitamente se un file è tracciato o da rigenerare.

## Criteri di accettazione
Vedere [indicator_completion_criteria.md](indicator_completion_criteria.md). La fase QA deve precedere la visualizzazione pubblica; la revisione umana deve distinguere un dataset valido da un'interpretazione approvata.
