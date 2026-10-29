# Data & artifact contract

## Ambito
Regole per dati **aggregati comunali** della diagnosi EPAH Sinergie in Canavese. Questa PR documenta una convenzione futura e **non** migra, elimina, ignora o ricrea file esistenti. Nessuna informazione personale deve essere aggiunta al repository.

## Classi di artefatto e versionamento
| Percorso | Contenuto | Regola proposta |
| --- | --- | --- |
| `config/` | Definizioni, fonti, registry | Versionare e revisionare |
| `data/municipalities.csv` | Perimetro canonico | Versionare; cambiamenti amministrativi documentati |
| `data/verification_matrix.csv` | Stati e note verifiche | Versionare; mai rigenerare distruttivamente |
| `data/raw/` | Download integrali originali | Non committare per impostazione predefinita; mantenere localmente con URL, checksum, data |
| `data/cache/` | Download/trasformazioni temporanee | Non committare; ricreabili |
| `data/reference/` | Piccoli snapshot ufficiali o curati | Versionare *solo* se licenza, fonte, versione e revisione lo consentono |
| `data/indicators/` | Tabelle comunali validate | Versionare output piccoli, corredati da manifest e controlli; altrimenti documentare rigenerazione |
| `data/derived/` | Incroci, overlay, profili compositi | Preferire rigenerazione; versionare solo release motivate con manifest |
| `outputs/` | Mappe, Excel, report | Generati localmente; release selezionate come artefatti pubblicabili con revisione |
| `data/manifests/` (futuro) | Provenance per dataset/rilascio | Versionare manifest privi di dati personali o segreti |

Un percorso assente dalla repo non implica che sia già creato o utilizzato. Le regole non rendono automaticamente pubblicabile un dataset: controllare prima licenza, attribuzione, restrizioni e riservatezza.

## Convenzioni obbligatorie da implementare gradualmente
- Identificare osservazioni con **codice ISTAT comunale** e anno/periodo di riferimento, non solo nome testuale; conservare la geografia amministrativa di riferimento.
- Non sovrascrivere uno snapshot con anni o metodi diversi: usare nomi stabili con periodo, per esempio `income_vulnerability_2024.csv` e relativi manifest.
- Separare `reference_year` (periodo misurato), `publication_date` (rilascio fonte), `retrieved_at` (download) e `generated_at` (elaborazione). Distinguere anno fiscale, anno dichiarazione e anno pubblicazione quando presenti.
- Usare `sha256` dei **byte effettivi** del file, calcolato localmente; non inserire valori fittizi né hash di un URL.
- Registrare URL di landing page e download, eventuale licenza, versione/snapshot, commit del codice, parametri e dipendenze rilevanti.
- Controllare copertura dei 27 Comuni, duplicati, unità, range, denominatori, assenze, comparabilità dei benchmark. Segnalare output provvisori senza etichettarli validati.
- Conservare fonte primaria e metodo per ogni indicatore; un file di output non basta a provare la validità del dato.
- Non includere token temporanei GitHub, query con credenziali o dati sensibili nei manifest o commit.

## Pubblicazione e qualità
Livelli proposti: `draft` (sperimentale), `reviewed` (QA tecnico effettuato), `published` (revisione metodologica e autorizzazione alla diffusione). Sono **stati dell'artefatto**, distinti da maturità indicatore e stato delle righe della verification matrix.

La presenza su Git non equivale ad approvazione per la pubblicazione. Non pubblicare mappe e profili senza specificare fonti, periodi, definizioni e limiti. Non costruire un indice di famiglie vulnerabili dai proxy territoriali.

## Migrazione successiva
La PR C non cambia `.gitignore` né sposta i CSV già tracciati: applicare ignore e migrazioni solo dopo aver verificato quali pipeline scrivono in quali cartelle, così da evitare output spariti o risultati persi. Il manifest è un contratto di formato, non è ancora prodotto automaticamente.

## PR-02 - Registry identifiers and source registration

The canonical municipality registry `data/municipalities.csv` now contains a
six-digit text `istat_code` column alongside its historical `municipality` name.
Existing verification-matrix keys **remain name-based** for backward compatibility.
All new joins should resolve the six-digit code first and retain the reference
geography/vintage for every join. Do not coerce codes to integers or discard
leading zeros.

**Code provenance:** the 27 code/name pairs were extracted from the
CC BY 4.0 `RP92/comuni-italiani` Piemonte dataset (a third-party
derivative of ISTAT 2026 records). Official authority: ISTAT SITUAS
`https://www.istat.it/classificazione/codici-dei-comuni-delle-province-e-delle-regioni/`.
These mappings are structurally checked; **an independent comparison against
the official ISTAT 2026 list or boundary shapefile is still required** before
the geographic sources can be treated as scientifically verified.
No source data or indicator status is promoted by this change.

The six previously unregistered core indicators now reference registered
source metadata. Registering a URL **does not** establish accessibility,
quality, licensing, reference vintage or approval. Source metadata contains
explicit unverified flags; downstream acquisitions and reviews occur in PR-03
through PR-07. Historical sources remain unchanged.

Provenance manifests generated in PR-02 describe actual local file bytes
(SHA-256), but remain `not_assessed` / `draft` until a human
conducts QA. Never commit secrets or raw household records.
