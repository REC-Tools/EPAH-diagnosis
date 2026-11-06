# EPAH Diagnosis v0.3 — Scientific Evidence Registry (PR 1)

**Ambito:** 27 Comuni di Sinergie in Canavese. **Data della ricognizione:** 5 novembre 2026.
**Stato:** inventario metodologico *source identified / pending review*, non release scientifica o istituzionale.

## Scopo e limiti

Il registro rende esplicito il rapporto fra gli indicatori sintetizzati dalla guida
[EPAH Handbook 1](https://energy-poverty.ec.europa.eu/system/files/2024-05/EPAHhandbook_diagnosis_finalpdf.pdf),
le fonti web individuate e le nove misure già descritte in [`config/indicators.json`](../config/indicators.json).
È una **trascrizione fedele della ricognizione**, non una verifica in tempo reale delle URL,
non un download di serie comunali e non una certificazione EPAH.

- **Indicatore diretto:** osserva l'esperienza di disagio energetico (es. incapacità di
  riscaldare la casa, arretrati di bollette). Senza una rilevazione locale idonea non
  esiste una quota comunale documentata.
- **Proxy di vulnerabilità:** condizioni che possono aumentare il rischio, come
  basso reddito fiscale o età degli edifici. Non identificano persone o famiglie
  effettivamente in povertà energetica.
- **Descrittore territoriale:** contesto climatico, altimetrico o di accessibilità.
  Non equivale a un esito di povertà energetica. In particolare, tempi stradali
  non equivalgono a tempi senza automobile.
- **Benchmark:** valori nazionali o regionali, utili come confronto soltanto con
  anno, unità e definizione comparabili. Non sono stime per i 27 Comuni.

L'ammissibilità futura di un *dato misurato* richiede: fonte primaria e licenza;
periodo e download originali; geografia/ID ISTAT coerenti; formula, popolazione e
denominatore dichiarati; unità e valori mancanti; copertura dichiarata dei 27;
QA delle elaborazioni; limiti, possibili bias e approvazione metodologica umana.
Il controllo tecnico del registro NON soddisfa tali condizioni.
Non produrre un indice composito, una classifica comunale di povertà energetica
né valutazioni individuali.

## Input e file derivati

Originale consegnato: **`EPAH_fonti_online_v03(1).xlsx`**, non inserito nella repository.
SHA-256 degli originali importati:

`770a47962959871649374dc8ef3c18a8114188a035967a33f8aafa782286ed4b`

| Foglio originale | Trascrizione CSV | Righe | Contenuto |
| --- | --- | ---: | --- |
| `Matrice_EPAH` | [`epah_v0_3_mapping.csv`](../data/reference/epah_v0_3_mapping.csv) | 56 | H01–H56, sintesi guida, fonte, reperibilità, limiti |
| `Fonti` | [`epah_v0_3_sources.csv`](../data/reference/epah_v0_3_sources.csv) | 35 | F01–F35, URL, scala, periodo, verifica descritta, limiti |
| `Priorita_v03` | [`epah_v0_3_priorities.csv`](../data/reference/epah_v0_3_priorities.csv) | 12 | Sequenza di lavoro proposta e prerequisiti |
| Revisione concettuale repository | [`epah_v0_3_crosswalk.csv`](../data/reference/epah_v0_3_crosswalk.csv) | 9 | Relazione con gli ID canonici, scarti di definizione, universo, denominatore, copertura, fonti e anni |

Gli ID **H01–H56 e F01–F35 sono assegnati dall'inventario**, non dalla guida EPAH o dagli enti titolari.
Per i tre fogli Excel sono stati mantenuti nomi delle colonne e valori delle celle. Sono
state aggiunte esclusivamente quattro colonne tecniche: `stato_evidenza`,
`workbook_sha256`, `foglio_origine`, `riga_origine`. Le date Excel sono serializzate
come ISO-8601 e le righe iniziano dal numero fisico nel foglio originale.
Il crosswalk è una **interpretazione concettuale esplicita**, non fa parte del workbook.

Le 35 righe delle fonti rimangono `source_identified`: la colonna originale
`Verifica svolta` descrive operazioni di ricognizione, non consente di impostare
`data_qa_passed` o `human_approved` senza evidenze aggiuntive. In particolare,
una URL accessibile non significa che i dati siano stati acquisiti e analizzati.

## Corrispondenze e decisioni per la v0.3

Il crosswalk distingue `partial_proxy` (stessa area, ma diverso universo o statistica),
`related_not_equivalent` (solo relazione tematica), `no_counterpart`.
**Nessuna riga è una corrispondenza esatta.** Esempi importanti:

- H48 usa nella sintesi **>65 anni**, mentre `population_65_plus` usa **>=65**.
  Verificare il wording e i dati originali prima di presentare comparabilità.
- H32 descrive vulnerabilità di persone/famiglie; `income_vulnerability` usa
  contribuenti IRPEF con reddito fino a 15.000 euro, non famiglie povere.
- H22 riguarda l'età degli edifici, ma `old_building_stock` esprime la quota
  ante-soglia in edifici residenziali 2011, non l'età media.
- H03 sono HDD annuali climatici; `heating_degree_days` usa un valore normativo
  DPR 412/1993, da mantenere separato da una eventuale serie ARPA.
- H26–H28 richiedono accessibilità o frequenza **senza auto**: i tre tempi
  stradali esistenti non li sostituiscono.
- Altitudine media e classificazione SNAI sono descrittori contestuali senza
  equivalente diretto nell'inventario H01–H56.

Le priorità per il seguito sono quelle della tabella `Priorita_v03`: età 0–11,
istruzione, disoccupazione, HDD recenti e APE residenziali sono candidati.
Non saranno integrati finché i dati reali e la loro metodologia non avranno
superato controlli separati. Gli APE *di tutte le destinazioni* non sostituiscono
una quota di **attestati residenziali validi**, né rappresentano tutto il patrimonio.
EU-SILC/EPAH/OIPE possono fornire benchmark nazionali/regionali, mai percentuali
comunali ottenute per semplice imputazione.

## Avanzamento successivo: candidato H47 (v0.3 PR 2)

È disponibile una [pipeline in anteprima per i residenti 0–11 anni](v0_3_population_0_11_candidate.md),
con import ZIP POSAS locale, controlli su codici ISTAT, **copertura completa
0–100 anni più riga 999**, riconciliazione dei totali di sesso se disponibili,
e manifest SHA-256. È ora prevista anche una [seconda ricostruzione indipendente](v0_3_h47_source_reproduction_audit.md) direttamente dallo ZIP originale con blocco dell’hash della prima acquisizione. **È soltanto una preparazione QA:** i valori comunali non
sono stati acquisiti o promossi automaticamente in questo registro.

## Rigenerazione, controlli e vincoli della PR

Con il workbook originale disponibile localmente e le dipendenze installate:

```powershell
python scripts/import_v0_3_evidence.py --workbook "EPAH_fonti_online_v03(1).xlsx" --out-dir data/reference
python scripts/check_v0_3_evidence.py
uv run --locked pytest -q
python scripts/check_documentation.py
```

L'import ricrea **solo i tre CSV di ricognizione**. Il crosswalk è mantenuto
separatamente per consentire la revisione metodologica umana. Il controllo
`check_v0_3_evidence.py` verifica schema, cardinalità, ID, riferimenti,
provenienza e stati ammessi; **non verifica la reperibilità online**, la validità
statistica dei dati o l'effettivo completamento delle attività dichiarate nel
workbook. La ricostruzione byte-per-byte richiede il file originale con lo stesso
SHA-256 e la versione di `openpyxl` risolta da `uv.lock`.

Questa PR **non modifica** `data/verification_matrix.csv`, il registro canonico,
le serie comunali o i bundle precedenti; non riapre il dossier CIT/Pont Canavese,
non promuove dati e non introduce un indice composito. Prima della pubblicazione
sono ancora necessarie verifiche dei dati originali e review scientifica e
istituzionale indipendenti.
