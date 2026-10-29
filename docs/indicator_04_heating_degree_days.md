# Heating degree days and climate zone

## Indicator

**Heating degree days (GG)** and **climate zone** for each of the 27 Green
Community municipalities.

The legal basis is **DPR 26 August 1993, no. 412, Annex A**, the national table
of municipal heating degree days and climate zones.

The current legal text of Annex A is published by the Italian Ministry of
Economy and Finance legal documentation portal and is marked as in force from
9 August 2016.

## Interpretation

Heating degree days are a conventional indicator of winter heating demand.
Higher values indicate colder climatic conditions and, all else equal, a
greater potential need for space heating.

Under DPR 412/1993:

- Zone E: more than 2,100 and up to 3,000 GG
- Zone F: more than 3,000 GG

Zone F is the coldest regulatory class.

For the EPAH diagnosis this is treated as a **climate exposure indicator**, not
as a direct measure of energy poverty or actual household consumption.

## Source strategy

The repository stores a curated 27-municipality reference snapshot in:

`data/reference/climate_dpr412_green_community.csv`

This avoids scraping a legal website at every run. The source URL and legal
basis remain recorded in the output and verification matrix.

Before promotion:

`python scripts/verify_heating_degree_days.py`

Outputs:

- `data/indicators/heating_degree_days.csv`
- `data/indicators/heating_degree_days_summary.csv`
- 27 rows promoted only after a separately documented review of the current legal annex

The Green Community summary is intentionally **unweighted** because heating
degree days describe municipal climate, not a household or population share.

### PR-03: independently checked historical table

An official **historical** Annex A PDF (Department of Finance) was consulted:
https://def.finanze.it/DocTribFrontend/getContent.do?id=%7BDEA36BB0-0D39-469B-B33C-22B29A7DBF3D%7D

`data/reference/climate_dpr412_official_2008_transcription.csv` contains
a *manual 27-municipality transcription* of pages 1–6 (1-based) from that
document. This file is not a byte-for-byte reproduction of the official PDF.
The offline command `python scripts/verify_heating_degree_days.py`
compares names, zones and GG against the local snapshot and writes JSON
evidence under `outputs/quality/`.

The 27 climate zones and degree-day values match the historical table.
Pratiglione has an **ancillary municipal-seat altitude discrepancy**:
711 m in the historical legal table, 611 m in the local snapshot.
The municipality also reports 611 m:
https://www.comune.pratiglione.to.it/it-it/vivere-il-comune/scheda

The legal portal identifies a consolidated Annex A effective 9 August 2016:
https://def.finanze.it/DocTribFrontend/getAttoNormativoDetail.do?ACTION=getArticolo&articolo=Allegato+A&codiceOrdinamento=60A+++++0000000&id=%7B0E4DC3BD-3B00-45E2-9CA6-B4DECB631C36%7D

**The historical cross-check is not a review of the 2016 text.**
Therefore the current 27 matrix rows remain `Dato acquisito`.
The finalizer now refuses to run without
`--approved-evidence /path/to/review.json`. The evidence must
identify an actual reviewer, a dated legal-version review, the exact two
local input hashes, a durable HTTPS review URL, a licensing-use decision,
and acknowledgement of any altitude differences. The command validates
the *evidence structure*, not the human signoff's authenticity.

After a genuine independent review:
```bash
python scripts/finalize_heating_degree_days.py --approved-evidence /path/to/review.json
```
The usual indicator and benchmark CSVs are then generated, and only then
can the 27 climate observations be promoted to `Dato validato`.
Do not invent review metadata or use synthetic approval files to release.

## PR-08a: verifica della versione consolidata 2016

Il riferimento **in vigore dal 09/08/2016** pubblicato dal Dipartimento
delle Finanze riporta per **Pratiglione: TO F 3270 611**. La versione
storica usata nella PR-03 riportava invece 711 metri: la differenza
**non è un errore dello snapshot locale**, che usa correttamente 611 m
per la sede comunale; i gradi-giorno sono invariati.

Fonte ufficiale: https://def.finanze.it/DocTribFrontend/getAttoNormativoDetail.do?ACTION=getArticolo&articolo=Allegato+A&codiceOrdinamento=60A+++++0000000&id=%7B0E4DC3BD-3B00-45E2-9CA6-B4DECB631C36%7D

Per approvare realmente **tutti i 27** dati occorre salvare la pagina
HTML completa (non screenshot o frammenti di motore di ricerca) e far
eseguire il confronto automatico per ogni nome, zona, GG e quota sede:

```bat
python scripts/audit_priority_sources.py --annex-html "C:\path\allegato_a_2016.html" --out-dir outputs\quality\audit_hdd_2016
```

Il report `heating_degree_days/consolidated_annex_comparison.json`
deve riportare `rows_examined=27`, `differences=[]`
e `technical_crosscheck_passed=true`. Il nuovo finalizzatore
richiede **anche** `--official-html` e un campo
`official_annex_sha256` identico all'hash dei byte della
pagina salvata, oltre a `official_annex_rows_verified=27`
nel JSON di revisione effettiva. Questi controlli impediscono di
scambiare il vecchio confronto storico per quello della versione vigente.

Un report tecnicamente positivo non autentica comunque origine,
licenza o revisore; l'approvazione metodologica è separata.
