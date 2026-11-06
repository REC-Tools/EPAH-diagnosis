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

Il collegamento alla tavola è individuato, ma **non abbiamo ancora trascritto e
validato il dizionario dei codici ufficiali di istruzione ed età dell'export**.
Per questo l'import richiede un CSV **normalizzato** separato dal file originale.
Non si deve interpretare la normalizzazione come ufficialmente approvata.

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
uv run --locked pytest -q tests/test_low_education_25_64_v0_3.py
python scripts/check_documentation.py
python scripts/check_v0_3_evidence.py
```
