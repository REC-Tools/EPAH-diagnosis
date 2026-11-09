# v0.3 — H50: istruzione inferiore alla secondaria di primo grado (25–64 anni)

**Perimetro:** 27 Comuni di Sinergie in Canavese. **Stato:** `technical_draft_do_not_publish`.
La pipeline **non integra** H50 nel catalogo v0.2 e non modifica la matrice canonica.
La revisione metodologica e l'acquisizione comunale definitiva sono rimandate alla
fase finale della v0.3, mantenendo un registro dei controlli ancora da completare.

## Definizione proposta

**Numeratore:** residenti di 25–64 anni con **nessun titolo di studio** o con la
**sola licenza elementare**. **Denominatore:** tutti i residenti di 25–64 anni
nello stesso universo censuario, compresi quelli con titolo non classificato.

`H50_candidate_pct = 100 × (none + primary) / total_residents_25_64`

La fascia 25–64 anni è una **scelta operativa del progetto**, non un parametro
esplicitamente fissato dal riferimento interno H50. È adottata per evitare di
contare i bambini che non hanno ancora terminato la scuola media.

**Distinzione obbligatoria:** *istruzione inferiore alla secondaria di primo grado*
non significa *al massimo licenza media*. Chi possiede la licenza media
(`lower_secondary`) è **escluso dal numeratore**. Non chiamare questo indicatore
tasso di abbandono scolastico, povertà educativa o misura diretta della povertà
energetica. Il suo ruolo è **proxy socioeconomico**.

## Fonte di riferimento: ISTAT 2024

- **ISTAT, Censimento permanente 2024:** popolazione residente di 9 anni e più
  per grado di istruzione **ed età**, a livello **comunale**.
- **IstatData, dataflow:** `IT1,DF_DCSS_ISTR_LAV_PEN_2_TV_1,1.0`.
- [Tavola comunale ufficiale](https://esploradati.istat.it/databrowser/#/it/censpop/categories/CPA_POP/DCSS_ISTR_LAV_PEN_2_TV/IT1,DF_DCSS_ISTR_LAV_PEN_2_TV_1,1.0).
- [Risultati ufficiali del Censimento](https://www.istat.it/statistiche-per-temi/censimenti/popolazione-e-abitazioni/risultati/).
- **Anno di riferimento:** 31 dicembre **2024** (non confondere con
  l'anno di download o con il dataset per sezione 2023).
- **Fonte nel registro EPAH:** F06, indicatore concettuale H50. Gli ID H50 e F06
  provengono dal *nostro inventario* e non sono codici ufficiali EPAH.

I codici di istruzione ed età dell'export sono ora ricondotti ai gruppi H50
da uno script che li verifica sui metadati ISTAT (vedi
[Normalizzazione dall'export ISTAT](#normalizzazione-dallexport-istat-e-audit-indipendente)).
L'import continua a richiedere un CSV **normalizzato** separato dal file
originale; la mappatura è tecnica e non ancora approvata metodologicamente.

## Contratto di input (CSV normalizzato)

Campi obbligatori, in UTF-8, mantenendo gli zeri iniziali dei codici ISTAT:

| Campo | Contratto |
| --- | --- |
| `municipality_code` | Codice ISTAT di **sei caratteri**, uno dei 27 del registro |
| `municipality` | Nome del Comune corrispondente al codice |
| `reference_year` | Esattamente `2024` |
| `sex` | Esattamente `total`, non una somma di righe `male` e `female` insieme al totale |
| `age_band` | Otto fasce `25-29`, `30-34`, ..., `60-64`, oppure una sola fascia `25-64` per *tutti* i Comuni; mai mescolare |
| `education_group` | Uno dei **sei** codici sotto riportati |
| `persons` | Conteggio **intero non negativo**, senza punti, virgole o simboli di soppressione |

Per **ogni** coppia Comune × fascia d'età devono comparire esattamente
queste categorie **esclusive**, compresi gli zeri reali:

| Codice | Interpretazione | Nel numeratore? |
| --- | --- | --- |
| `none` | Nessun titolo | Sì |
| `primary` | Scuola primaria/licenza elementare | Sì |
| `lower_secondary` | Licenza media / secondaria di primo grado | **No** |
| `upper_or_tertiary` | Titoli di livello superiore, ricondotti qui dopo controllo del dizionario | No |
| `unknown` | Titolo non classificato nel dato originale, quando previsto | No; **incluso nel denominatore** |
| `total` | Totale della stessa fascia, non una categoria aggiuntiva | Denominatore |

**Controllo per fascia:** `total = none + primary + lower_secondary + upper_or_tertiary + unknown`.
Se la tavola ISTAT non pubblica una categoria o fornisce aggregati non compatibili,
**non inserire zeri ipotetici**: la normalizzazione deve attendere il dizionario
originale. Il codice verifica anche la copertura 27/27, assenza di duplicati,
coerenza dei periodi e denominatori strettamente positivi.

Il CSV di input contiene **162 righe** con fascia `25-64` aggregata, oppure
**1.296 righe** con otto fasce quinquennali. Non vanno introdotti totali
trasversali tra sesso, età o titoli che producano doppi conteggi.

## Esecuzione in cartella tecnica, senza sovrascritture

Prima di eseguire il codice, esportare la tavola originale IstatData e
conservarla integralmente **fuori da Git**. Realizzare la normalizzazione
**solo dopo** aver riportato in un file di lavoro la corrispondenza dei codici
ISTAT ai sei gruppi sopra descritti (mappatura ancora da verificare).

```powershell
uv run --locked python scripts/prepare_low_education_25_64_v0_3.py `
  --original-export data/downloads/ISTAT_censimento_2024_istruzione_original.csv `
  --normalized-csv outputs/quality/h50_input/education_2024_normalized.csv `
  --out-dir outputs/quality/h50_review_01
```

Facoltativo: `--expected-original-sha256 <digest_del_file_originale>` per
bloccare revisioni inattese.

La cartella **nuova** contiene:

- `low_education_25_64_preview.csv`: 27 percentuali, conteggi, sconosciuti,
  anno, riferimento alla fonte e stato tecnico.
- `qa.json`: totale ponderato dei 27 Comuni, modalità di aggregazione delle età,
  copertura, numerosità delle persone con istruzione non classificata.
- `manifest.json`: hash SHA-256 dell'export originale, del CSV normalizzato,
  del registro ISTAT e dei due risultati; **nessuna approvazione**.

Se manca un Comune, una classe d'età o di titolo, se i totali non coincidono
oppure se l'output esiste già, la pipeline **si interrompe**.
I test automatici verificano il software solo con dati **sintetici**, non
presentano numeri comunali simulati come evidenze reali.

## Normalizzazione dall'export ISTAT e audit indipendente

Dal 9 novembre 2026 il CSV normalizzato non va più costruito a mano:
`scripts/normalize_h50_istat_sdmx_v0_3.py` lo ricava direttamente dall'export
originale e dai metadati SDMX del dataflow `DF_DCSS_ISTR_LAV_PEN_2_TV_1`
(stesso DSD `DCSS_ISTR_LAV_PEN_2_TV` di H46).

| Codice `EDU_ATTAIN` | Etichetta ISTAT (metadati) | Gruppo H50 |
| --- | --- | --- |
| `NED` | nessun titolo di studio | `none` |
| `PSE` | licenza di scuola elementare | `primary` |
| `LSE` | licenza di scuola media inferiore o di avviamento professionale | `lower_secondary` |
| `USE_IF` | diploma di istruzione secondaria di II grado o di qualifica professionale (3-4 anni) compresi IFTS | `upper_or_tertiary` |
| `BL` | diploma ITS o titolo terziario di primo livello | `upper_or_tertiary` |
| `ML_RDD` | titolo terziario di secondo livello e dottorato | `upper_or_tertiary` |
| `NRP` | non indicato | `unknown` |
| `ALL` | totale | `total` (solo controllo) |

Regole applicate, tutte bloccanti:

- **Età:** ISTAT pubblica `Y25-49` e `Y50-64`; vengono sommate nella sola fascia
  `25-64`. La fascia `Y9-24` non entra nell'indicatore.
- **Etichette:** se nei metadati cambia il testo italiano di un codice, o un
  codice diventa sotto-categoria di un altro, la normalizzazione si ferma.
  Un codice non documentato nei dati (per esempio `IL` analfabeti, figlio di
  `NED`) blocca per evitare doppi conteggi.
- **Celle omesse:** ISTAT non pubblica le celle a zero. Una cella assente vale 0
  **solo** se le categorie pubblicate sommano comunque al totale `ALL` di quel
  Comune e fascia. Nell'export del 6/11 sono 42 celle, tutte riconciliate.
- **Valori decimali:** 23 totali dell'export hanno rumore di rappresentazione
  (es. `63.99999999999999`). Sono accettati come interi solo entro 0,000001
  persone; un vero valore frazionario blocca, perché il contratto H50 è intero.
- `unknown=0`: `NRP` non compare per questi Comuni e le categorie chiudono sul
  totale, quindi lo zero è un'inferenza di esaustività, non un dato osservato.

L'audit `scripts/audit_h50_istat_independent_v0_3.py` **non importa** il
normalizzatore né il builder: rilegge export e metadati, ricostruisce le 162
righe e le 27 quote, verifica `M + F = T` per ogni cella (comprese le età 9-24),
categorie = totale per ogni sesso e fascia, gli hash del manifest e l'anteprima.

```powershell
$src = "data/downloads/ISTAT_censimento_2024_istruzione_original.csv"
$t = Get-Date -Format yyyyMMdd-HHmmss
$meta = "outputs/quality/h50_sdmx_metadata_$t"
New-Item -ItemType Directory $meta | Out-Null
# Una sola richiesta ISTAT per i metadati (DSD + codelist del dataflow TV_1).
Invoke-WebRequest -OutFile "$meta/ISTAT_H50_dataflow_metadata.xml" `
  -Headers @{ Accept = "application/vnd.sdmx.structure+xml;version=2.1" } `
  "https://esploradati.istat.it/SDMXWS/rest/dataflow/IT1/DF_DCSS_ISTR_LAV_PEN_2_TV_1/1.0/?detail=Full&references=Descendants"

uv run --locked python scripts/normalize_h50_istat_sdmx_v0_3.py `
  --original-export $src --metadata-xml "$meta/ISTAT_H50_dataflow_metadata.xml" `
  --expected-original-sha256 d2c4422b1ba8a9718312e0a6b205b447450e1d925bf9fa29a98e3e52b1aab7a9 `
  --out-dir "outputs/quality/h50_normalized_$t"

uv run --locked python scripts/prepare_low_education_25_64_v0_3.py `
  --original-export $src `
  --normalized-csv "outputs/quality/h50_normalized_$t/education_2024_normalized.csv" `
  --out-dir "outputs/quality/h50_preview_$t"

uv run --locked python scripts/audit_h50_istat_independent_v0_3.py `
  --original-export $src --metadata-xml "$meta/ISTAT_H50_dataflow_metadata.xml" `
  --normalized-csv "outputs/quality/h50_normalized_$t/education_2024_normalized.csv" `
  --normalization-manifest "outputs/quality/h50_normalized_$t/normalization_manifest.json" `
  --registry data/municipalities.csv `
  --preview-csv "outputs/quality/h50_preview_$t/low_education_25_64_preview.csv" `
  --out-file "outputs/quality/h50_normalized_$t/independent_audit.json"
```

**Checkpoint del 9 novembre 2026** (file non versionati):

- Export originale SHA-256: `d2c4422b1ba8a9718312e0a6b205b447450e1d925bf9fa29a98e3e52b1aab7a9`.
- XML metadati TV_1 SHA-256: `4a4b7157b01a1e244aad131b87bdbf1f356a6bcaa0429455000c0d75e5e3b410`.
- 162 righe normalizzate, **identiche** alla tabella preparata a mano il 6/11;
  42 celle omesse riconciliate a zero; 23 totali con rumore di rappresentazione.
- Audit indipendente **PASS**: 493 verifiche per sesso, 241 per titolo di studio.
- 840 adulti 25–64 su 20.058 senza licenza media: quota ponderata **4,19%**.

Il controllo delle etichette e l'audit sono verifiche **tecniche**: non
sostituiscono la revisione metodologica dei punti sotto.

## Verifiche rinviate alla fase finale v0.3

1. Scaricare l'export ISTAT 2024 e registrarne formato, data, licenza e SHA-256.
2. Confermare sul **dizionario originale** tutti i codici di titolo ed età,
   nonché la classificazione `none`/`primary`/altri.
3. Confrontare un campione di Comuni e verificare la riconciliazione di
   ogni riga normalizzata con il file originale.
4. Valutare eventuali dati non classificati, fragilità dei numeri piccoli,
   comparabilità temporale e approvazione metodologica.
5. Soltanto dopo proporre l'inserimento nella v0.3, **senza alterare** gli
   indicatori canonici v0.2 o inventare una misura di povertà energetica.

```powershell
uv run --locked pytest -q tests/test_low_education_25_64_v0_3.py tests/test_h50_sdmx_normalization_and_audit_v0_3.py
python scripts/check_documentation.py
python scripts/check_v0_3_evidence.py
```
