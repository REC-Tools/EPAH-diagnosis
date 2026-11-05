# Dossier per chiarimento CIT - Pont Canavese (PR #121)

Il perimetro v0.2 comprende **27 Comuni**, ma la QA tecnica CIT ha
restituito **26 Comuni non controversi**. Per Pont Canavese, ISTAT
`001199`, due righe degli originali Regione Piemonte riportano
conteggi differenti. **Non si possono selezionare né sommare le righe
per ipotesi.**

Questa procedura trasforma una run CIT conclusa con la PR #120 in un
**dossier interno da revisionare prima di contattare il titolare del
dato**. Nessun dato viene promosso alla matrice canonica, pubblicato
o corretto automaticamente.

## Prerequisiti

Una cartella `outputs/quality/cit_pipeline_<identificativo>` generata
con successo dal profilo `epah pipeline run --profile cit-quarantine`,
contenente le sottocartelle `cit_fuel`, `cit_age` e `cit_review`
e il file `pipeline_run_report.json`.

Il generatore ricontrolla gli hash SHA-256 dei due estratti verificati,
le QA dei parser, i valori di confronto dei 26 Comuni, il conflitto
di Pont e l'integrità degli output esistenti. Se la catena di
provenienza è incompleta o incoerente, non crea il dossier.

## Comando Windows PowerShell

Sostituire il percorso della run effettivamente presente sul proprio PC:

~~~powershell
uv run --locked epah cit review-packet --run-dir outputs/quality/cit_pipeline_20261105_a --out-dir outputs/quality/cit_pont_review_packet_20261105_a
~~~

La cartella di destinazione deve essere **nuova**, sempre sotto
`outputs/quality/`. Una run diversa richiede una cartella nuova;
gli audit precedenti non vengono sovrascritti.

## Output

| File | Contenuto |
| --- | --- |
| `cit_pont_evidence.json` | Hash originali e QA, linee e conteggi nativi discordanti, stato *non approvato*. |
| `request_to_region_draft.md` | Bozza italiana della richiesta di chiarimento, con tabella delle righe originali e quattro domande tecniche. |
| `human_review_checklist.md` | Checklist non compilata per recapito, licenza, risposta e review. |

**Prima dell'invio** un referente deve verificare destinatario,
licenza, correttezza della tabella ed eventuale allegazione delle righe.
Nessuna email viene inviata automaticamente. Dopo la risposta
istituzionale, conservare l'evidenza e avviare **separatamente**
la revisione dei 27 Comuni e delle definizioni metodologiche.

I 6.881 gruppi con intervallo di età ambiguo osservati nella precedente
analisi riguardano i 26 Comuni non controversi e non spiegano le
duplicazioni di Pont. Il valore esatto è ricalcolato dai file della run:
i gruppi generatori non rappresentano direttamente famiglie.
