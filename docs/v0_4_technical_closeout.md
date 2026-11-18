# Chiusura tecnica parziale v0.4

## Ambito concordato

Utente prioritario: tecnico incaricato della diagnosi EPAH 26-IT-Unione-TA26.
Il manutentore ha confermato che il perimetro CERS FERVORES dell'incarico coincide
con i 27 Comuni di Sinergie in Canavese della repository. Questa corrispondenza
non cambia registro, codici o geografie già verificati.

La v0.4 si chiude come **strumento per preparare e revisionare un pacchetto
territoriale parziale**. Non è il completamento delle 16 serie né la chiusura
delle attività sul campo dell'incarico. Il software stabile resta v0.3.0 fino a
una release separata; questa chiusura non crea tag, merge o autorizzazioni.
I prodotti restano `technical_draft_do_not_publish`.

## Risultato disponibile e limiti

- Catena unica `epah outputs plan/run`, senza acquisizioni automatiche.
- Atlante, CSV, fascicolo HTML/PDF, portale, 27 schede e audit indipendenti.
- Snapshot reale riproducibile con 13 serie disponibili; H03/H04/H05 assenti.
- Portale con disponibilità e periodi per indicatore, separati dalla revisione.
- Modello di revisione legato all'hash dello snapshot, da compilare in una copia.

H47/H50/H46 e abitazioni sono candidati tecnici: disponibilità e replay non
attribuiscono nuove approvazioni umane o canoniche. Per il clima sono disponibili
originali, ma unità e allineamento richiedono decisioni. H05 richiede evidenza
comunale residenziale adeguata. Restano aperti i quesiti nel
[dossier scientifico](v0_4_scientific_decisions.md), non acquisizioni da ripetere
automaticamente. Le approvazioni storiche conservano il proprio ambito.

## Riprodurre il pacchetto con una configurazione locale

Creare un file locale, per esempio `work/review-inputs.json`, con i percorsi
effettivi degli input verificati. I percorsi relativi partono dalla cartella
del file JSON, non dalla directory di avvio. Esempio indicativo:

```json
{
  "schema_version": "0.4-review-inputs-1",
  "inputs": {
    "bundle": "../outputs/v0.1.0-pilot",
    "registry": "../data/municipalities.csv",
    "release_config": "../config/release_v0_1.json",
    "h47_zip": "input/h47-review-schema2.zip",
    "h50_dir": "input/h50-preview",
    "h46_dir": "input/h46-preview",
    "housing_dir": "input/housing-preview"
  }
}
```

Il file non contiene comandi, formule, approvazioni, destinazioni o opzioni per
ignorare gate. Sono ammessi soltanto `bundle`, `registry`, `release_config` e
le sette chiavi candidate già esistenti. Le prime tre sono obbligatorie; omettere
le candidate assenti, senza inventare file o usare `null`. Non mescolare la
configurazione con opzioni individuali degli input.

```powershell
uv run --locked epah outputs plan --inputs-file work/review-inputs.json --out-dir work/v04-review-01 --allow-incomplete
uv run --locked epah outputs run --inputs-file work/review-inputs.json --out-dir work/v04-review-01 --allow-incomplete
```

`plan` non crea la destinazione. `run` ricostruisce il piano consentito e applica
i controlli originali; non esegue piani JSON salvati. L'hash della configurazione
è conservato nel piano e in `run.json`. Una configurazione non certifica i file:
ricevute e audit continuano a verificare i contenuti. Non inserire in Git
configurazioni con percorsi personali, originali o l'intera directory di run.

La destinazione deve essere nuova. I log e la ricevuta di una run fallita
rimangono disponibili. Scegliere un altro nome per riprovare.

## Consultare e revisionare

Aprire `hub/index.html`, poi seguire Comune/indicatore, fonte, periodo, unità,
limiti e registro delle evidenze. La tabella iniziale descrive disponibilità
tecnica, non una validazione. CSV, fascicolo e schede leggono lo stesso snapshot.

Scaricare `review/indicator_review_template.csv` e salvarne una copia esterna
al pacchetto prima di compilarla. Ogni riga contiene l'hash dello snapshot,
l'evidenza iniziale e campi per revisore, data, decisione/limiti e domande per
il campo. `pending` riguarda questa revisione: non annulla approvazioni storiche.
Le interviste supportano pertinenza e interpretazione territoriale; non
sostituiscono verifiche di fonte, formula, unità e denominatore. Il software
non importa queste note come approvazioni automatiche.

Le dimostrazioni sintetiche mantengono avvisi anche nelle schede autonome e non
includono export intermedi non inventariati. Non usarle come input territoriale.

## Criterio di consegna e seguito

Con gli stessi input verificati, un tecnico deve produrre una nuova run senza
modificare codice, ritrovare le stesse osservazioni e superare entrambi gli audit.
La lettura deve mantenere visibili assenze e decisioni ancora aperte. La revisione
visiva completa, il confronto sul campo e la diffusione hanno ricevute distinte.

L'ampliamento degli indicatori passa alla
[metodologia v0.5](v0_5_methodology.md), senza modificare retroattivamente
lo snapshot, le definizioni o gli stati della v0.4.
