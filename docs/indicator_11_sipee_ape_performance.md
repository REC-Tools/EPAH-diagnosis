# SIPEE APE energy-performance indicator

## Why there is no public scraper

Regione Piemonte's SIPEE stores the regional Energy Performance Certificates
(APE). Public users can search and consult individual APE records. The official
SIPEE service for Public Administrations additionally provides searches and
**data extractions** useful for control activities.

For a reproducible municipal diagnosis, this project does not scrape the
public single-record interface. It ingests an official SIPEE extraction.

## Primary indicator

**Share of usable APE in energy classes E, F or G**

Formula:

`100 * (APE_E + APE_F + APE_G) / total_usable_APE`

This is aligned with EPAH's housing / energy-performance dimension, but is not
treated as prevalence across the whole dwelling stock.

## Required input

Save an official SIPEE CSV export as:

`data/raw/sipee_ape_export.csv`

The importer accepts aliases for at least:
- municipality;
- energy class;
- optional EPgl,nren.

A minimal template is provided at:

`data/reference/sipee_ape_export_template.csv`

## Output

`data/indicators/sipee_ape_performance.csv`

For each municipality:
- total usable APE;
- counts A4 through G;
- E+F+G count;
- E+F+G share;
- median EPgl,nren when present.

The verification matrix receives the indicator
`poor_energy_label_share` only after all 27 municipalities are represented
in the official export.

## Critical limitation: coverage

APE records are selective. Buildings require an APE only in specific legal and
transactional circumstances, and certificates may expire or be renewed.
Therefore the class distribution among available APE cannot be interpreted as
the class distribution of every dwelling in a municipality.

Every use of this indicator should report the number of APE records alongside
the percentage.

## Recommended official extraction request

Ask Regione Piemonte / the SIPEE PA operator for a row-level or already
aggregated export covering the 27 Green Community municipalities and including,
where available:

- municipality;
- APE identifier;
- issue / submission date;
- validity / status;
- energy class;
- EPgl,nren;
- building use / category;
- conditioned useful floor area.

No personal owner or occupant data are required for this diagnosis.
