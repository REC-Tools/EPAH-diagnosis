# EPAH v0.4 — Step 4: contratto editoriale per 16 indicatori

**Decisione:** atlante, fascicolo HTML/PDF, portale offline e 27 schede comunali usano un'unica descrizione del **significato** di ogni indicatore. Restano invariati ID, nomi tecnici, periodi effettivi, valori, numeratori e denominatori dei builder. È una revisione **editoriale**, non un nuovo audit scientifico.

## Contratto verificabile

La fonte unica è `src/epah_diagnosis/editorial_catalog_v0_4.py`, che definisce per ciascuno dei **16 ID**: ruolo descrittivo, dimensione EPAH orientativa, popolazione/universo di riferimento, definizione operativa, limite di interpretazione e stato di non-approvazione. Il builder `scripts/build_v0_4_visual_atlas.py` aggiunge i campi come `editorial` in `atlas_data.json`. L'atlante visualizza il significato sotto la fonte dell'indicatore e salva `catalogo_editoriale.json` con hash SHA-256 nel manifest.

Il rapporto tecnico v0.4 riusa **esattamente quei metadati dello snapshot dell'atlante**, senza inventare definizioni a partire dalla colonna `value`. Espone ruolo, universo, metodo e limiti nell'HTML e nel PDF, e crea il proprio `catalogo_editoriale.json` verificabile. Le 27 schede comunali conservano **due pagine A4**: la prima può mostrare il riferimento sintetico per le serie evidenziate, la seconda rimanda al catalogo allegato per tutte le definizioni. Il portale collega il catalogo solo se presente e coerente con l'atlante.

L'input dello Step 4 è un **nuovo atlante v0.4** creato dopo l'aggiornamento. Gli snapshot precedenti v0.3/v0.4 non vengono sovrascritti né retro-modificati: per essi il catalogo può risultare vuoto e gli output continuano a riportare i metadati originari.

## Differenze da non cancellare

| ID | Universo da dichiarare | Confusione da evitare |
| --- | --- | --- |
| `population_65_plus`, `H47` | Residenti; popolazione provvisoria 2026 per H47 | Non sono famiglie povere |
| `income_vulnerability` | Contribuenti IRPEF | Non coincide con numero di famiglie o AROP |
| `H46` | Forze di lavoro 15+, occupati + disoccupati | Non includere inattivi; non arrotondare conteggi ISTAT |
| `H50` | Residenti 25–64 nella definizione censuaria | Senza licenza media non include chi ha licenza media |
| `old_building_stock` | Edifici residenziali censiti | Età edilizia ≠ prestazione energetica |
| `H05` | Solo certificati APE residenziali validi | Il campione APE ≠ intero patrimonio abitativo |
| `ADD-HOUSING-01` | Abitazioni censite | Non occupate da residenti ≠ case vuote |
| `heating_degree_days` | Parametro comunale normativo DPR 412 | Non equivale a H03 |
| `H03`, `H04` | Celle ARPA NWIOI associate ai Comuni | HDD/CDD stimati ≠ consumi reali o disagio familiare |
| `mean_altitude`, `snai_classification` | Territorio comunale | Non trasformare categorie o altitudine in rischio |
| `dea_accessibility`, `upper_secondary_accessibility`, `rail_accessibility` | Tempi di accessibilità stradale modellati | Non sono accessibilità con trasporto pubblico |

Le categorie EPAH sono **corrispondenze parziali** con il manuale, non attestazioni di equivalenza tra proxy e misura della povertà energetica. Gli ID `H..` usati qui sono etichette **interne all'inventario del progetto**.

## Integrità e modalità di controllo

- L'atlante v0.4 rifiuta un catalogo che non copra tutti i 16 ID nell'ordine previsto.
- Il codice conserva senza ricalcolo i campi originali `name`, `source`, `unit`, `available`, `years` e le serie comunali.
- Se il catalogo del fascicolo cambia rispetto all'atlante, il portale blocca la generazione **anche se il manifest viene aggiornato**.
- Test su fixture sintetiche con 16 slot, sia con osservazioni mancanti sia con valori fittizi, verificano HTML, PDF, schede da 54 pagine e portale. Le fixture non sono evidenze territoriali.
- Gli hash provano integrità dello snapshot, **non** approvazione del mapping originale o della metodologia.

## Comandi

Ricreare i prodotti in **cartelle nuove** seguendo nell'ordine:

1. `scripts/build_v0_4_visual_atlas.py` (per i nuovi metadati editoriali);
2. `scripts/build_v0_4_review_pack.py` (stesso atlante, preview opzionali identiche);
3. `scripts/build_v0_4_output_hub.py` (atlante + fascicolo verificati).

Controlli CI:

```powershell
uv run --locked pytest -q tests/test_editorial_catalog_v0_4.py
uv run --locked pytest -q
uv run --locked python scripts/check_documentation.py
```

**Non pubblicare:** `technical_draft_do_not_publish`, `scientific_approval=false`, `publication_allowed=false`. La release software stabile resta v0.3.0 e questa PR non modifica `data/`, fonti originali, catalogo canonico, matrice di verifica o approvazioni.

**Step 5:** migliorare la cartografia (leggibilità dei nomi, legende e confronto tra mappe) senza cambiare valori o significato degli indicatori.
