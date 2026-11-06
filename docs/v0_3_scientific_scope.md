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

## Nuovo candidato H50: istruzione 25–64 anni (v0.3, in sviluppo)

È stata aggiunta la [pipeline di anteprima H50](v0_3_h50_education_candidate.md)
per la quota di adulti **25–64 anni con titolo inferiore alla licenza media**
(nessun titolo o sola licenza elementare), su fonte candidata ISTAT
Censimento 2024, IstatData `DF_DCSS_ISTR_LAV_PEN_2_TV_1`.
La scelta della fascia 25–64 è **operativa**, non una nuova interpretazione
attribuita alla guida EPAH. I dati 9+ per titolo senza una dimensione età
separata **non** soddisfano questa definizione.

La pipeline accetta un export normalizzato con codici comunali, età e
titoli espliciti, e conserva gli hash dell'export originale. La
**corrispondenza tra codici effettivi dell'export ISTAT e categorie
normalizzate non è ancora verificata**: la CI esegue soltanto test sintetici
e non rende disponibili valori reali dei 27 Comuni. H50 è quindi
`technical_draft_do_not_publish`, senza modifica alla matrice
canonico-v0.2. Per il percorso di progetto, la revisione complessiva
dei nuovi indicatori è rinviata alla chiusura della fase di sviluppo
v0.3; non si inventano né si promuovono valori nell'attesa.

## Nuovo candidato H46: disoccupazione 15 anni e più

È disponibile la [pipeline tecnica H46](v0_3_h46_unemployment_candidate.md)
per il tasso `100 × disoccupati / (occupati + disoccupati)` tra persone
di **15 anni e più**, proposta su tavole ISTAT Censimento permanente 2024
(F06). Non include gli inattivi nel denominatore e **non** equivale a
`100 − tasso di occupazione`. Il programma richiede una tabella
normalizzata con tutti e sei i conteggi di controllo, un export
originale conservato e i 27 codici comunali, producendo esclusivamente
CSV/QA/manifest `technical_draft_do_not_publish`.

I **codici censuari 2024** e la disponibilità dei totali comunali
nello stesso universo non sono ancora stati verificati sull'export
ISTAT originale: i test impiegano soltanto fixture sintetiche e non
costituiscono acquisizione di valori reali. La revisione scientifica
complessiva di H47, H50 e H46 è pianificata per la conclusione
dello sviluppo v0.3, senza promozione di valori nel frattempo.

## Nuovo candidato H03: HDD climatici annui stimati su griglia (2025)

È disponibile la [pipeline sperimentale H03](v0_3_h03_annual_hdd_candidate.md)
per stimare i gradi giorno 2025 da temperature **Tmin/Tmax giornaliere ARPA
NWIOI (F08)** e con convenzione climatica **Eurostat**: se
`Tmean_est = (Tmin + Tmax) / 2 ≤ 15 °C`, HDD giornaliero `18 − Tmean_est`,
altrimenti zero. La somma è riferita all'intero **anno solare 2025**.
Non confondere questa stima con gli HDD normativi statici del DPR 412/1993
presenti nella v0.2, né con le stime quindicinali ARPA per il municipio
(F07). Questo è un descrittore di esposizione climatica e **non** misura
l'incapacità delle famiglie di riscaldare l'abitazione.

L'input è una tabella normalizzata di 27×365 temperature da una sola cella
di griglia dichiarata per Comune, con NetCDF originali Tmin/Tmax conservati
e hash tracciati. Il software controlla la completezza del calendario,
la coerenza matematica dei dati e le celle dichiarate, ma **non ha ancora
verificato la decodifica originale dei NetCDF o la corrispondenza geospaziale
con i 27 Comuni**. I test sono sintetici; nessun valore climatico reale
viene promosso. Anche per H03 la verifica scientifica complessiva viene
rinviata alla conclusione dello sviluppo v0.3.

### Estrazione automatica dei NetCDF originali per H03

È ora disponibile l'[estrattore offline ARPA NWIOI](v0_3_h03_nwioi_netcdf_extraction.md):
legge direttamente le temperature dai NetCDF TN/TX, richiede la **maschera
ufficiale del Piemonte** e i poligoni ISTAT 2026, associa in modo riproducibile
una cella valida per ciascuno dei 27 Comuni e alimenta il calcolo annuale H03.
I controlli sono stati provati su **fixture NetCDF sintetiche**, non su
file climatici ARPA realmente acquisiti. L'estrazione geospaziale è soltanto
un gate tecnico; rappresentatività altimetrica e approvazione scientifica
restano da verificare nella revisione finale della v0.3.

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
