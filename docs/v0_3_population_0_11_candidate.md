# v0.3 — candidato H47: quota residenti 0–11 anni (anteprima tecnica)

**Ambito:** 27 Comuni di Sinergie in Canavese. **Stato:** `technical_draft_do_not_publish`.
Questo documento introduce una pipeline **separata dal catalogo canonico**. Non approva né promuove nuovi dati nella matrice dei 27×9 indicatori storici.

## Definizione

Indicatore candidato `population_0_11`, riferimento interno al mapping EPAH **H47** (non ID ufficiale EPAH):

`100 × somma residenti di età intera da 0 a 11 anni / somma residenti di tutte le età`.

- Popolazione: persone residenti, non nuclei familiari né minori con disagio energetico.
- Il denominatore non è 0–14, né la popolazione scolastica.
- Il totale territoriale è il **rapporto fra le somme** dei 27 Comuni, non la media semplice delle 27 percentuali.
- È un **proxy socio-demografico di vulnerabilità**, non una stima della povertà energetica.

**Fonte:** ISTAT POSAS, popolazione residente per età e sesso al **1 gennaio 2026**, file nazionale comunale [dati POSAS](https://demo.istat.it/app/?i=POS). La stessa fonte è già registrata in `config/sources.json` con ID `istat_posas`; il file 2026 è una **stima coerente col censimento e il bilancio provvisorio 2025**. Prima di pubblicare verificare eventuali aggiornamenti/revisioni ufficiali.

## Esecuzione sicura

Scaricare manualmente lo ZIP ufficiale della fonte e conservarlo localmente (non committarlo). Non viene fatto alcun download automatico e non viene modificata la matrice canonica.

Dalla root della repository:

```powershell
uv run --locked python scripts/prepare_population_0_11_v0_3.py --source-zip data/downloads/POSAS_2026_it_Comuni.zip --reference-date 2026-01-01 --out-dir outputs/quality/population_0_11_v0_3_review_01
```

La prima implementazione accetta soltanto `--reference-date 2026-01-01`, coerentemente con l’URL POSAS 2026 indicato nel codice. Un anno successivo richiederà il relativo URL e una revisione della metodologia, non il solo cambio del parametro.

**Per un controllo più forte della provenienza**, aggiungere `--expected-sha256 <SHA256-verificato-dello-ZIP>`; in presenza di più CSV nello ZIP è obbligatorio `--member <nome esatto>`. È necessario usare una cartella `--out-dir` nuova a ogni tentativo. Non eliminare automaticamente i risultati di QA già presenti.

Artefatti scritti soltanto nella cartella richiesta:

| File | Contenuto |
| --- | --- |
| `population_0_11_preview.csv` | 27 codici ISTAT, numeratore, denominatore e percentuale comunale; stato esplicito |
| `qa.json` | 27/27, totale territoriale ponderato, controlli applicati e limiti |
| `manifest.json` | SHA-256 dello ZIP originale, CSV interno, registro comunale e due output, fonte e data |

## Controlli e limitazioni

La pipeline rifiuta: codici ISTAT ripetuti, mismatch codice/nome, assenza di uno dei 27 Comuni, **età mancanti da 0 a 100 inclusi** (100 è la classe terminale 100+ nello schema atteso), età duplicate o non supportate, valori non numerici, formati di migliaia ambigui, denominatori pari a zero, totale POSAS `999` assente o incoerente, **maschi + femmine diversi dal totale quando le due colonne sono disponibili**, ZIP ambiguo con più CSV senza `--member`, hash richiesto non corrispondente e output già esistente. Le verifiche avvengono **prima** di creare il nuovo output.

**Nota importante:** questa implementazione richiede per ciascun Comune una distribuzione completa da `0` a `100` (la classe `100` è trattata come fascia terminale 100+) e una riga di totale con codice età `999`. Il controllo della sola fascia 0–11 sarebbe insufficiente a garantire il denominatore. **Questo contratto dello schema va comunque confermato sull'originale POSAS 2026 prima di acquisire dati reali.** Se il formato ufficiale cambia, il comando deve fermarsi e la nuova semantica deve essere revisionata; non bisogna indebolire il controllo sostituendo silenziosamente valori o denominatori.

Questa fase non verifica automaticamente **l'anno realmente riportato nell'intestazione dello ZIP**, autenticità del download, licenza, copertura a livello di sezioni di censimento, comparabilità con altre annualità o approvazione metodologica. La data `--reference-date` da sola non prova che lo ZIP contenga dati del 2026: il revisore deve confrontare intestazione e pagina ufficiale. Il tentativo di scaricare l'originale ufficiale da questo ambiente è stato bloccato dalla rete; **nessun valore reale dei 27 Comuni è stato elaborato o verificato**. Il programma non determina l'incidenza della povertà energetica nei minori e non usa il dato per selezionare beneficiari. CIT/Pont Canavese rimane fuori da questo workflow.

## Test

```powershell
uv run --locked pytest -q tests/test_population_0_11_v0_3.py
uv run --locked pytest -q
python scripts/check_documentation.py
python scripts/check_v0_3_evidence.py
```

**Condizione per una successiva PR con dati reali:** recuperare l'originale ufficiale, documentare SHA-256 e data acquisizione, verificare contro POSAS un campione di età per Comuni diversi, controllare 27 codici ISTAT e la copertura completa, ottenere decisione metodologica registrata. Solo successivamente proporre l'inserimento nell'attuale sistema di indicatori, senza modificare implicitamente il contratto di release v0.1.
