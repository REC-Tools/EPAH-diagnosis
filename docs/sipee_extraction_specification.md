# SIPEE extraction specification for Green Community Sinergie in Canavese

Purpose: municipal-level EPAH energy-poverty diagnosis for 27 municipalities.

Requested source: Regione Piemonte SIPEE official extraction.

## Geographic scope

The 27 municipalities listed in `data/municipalities.csv`.

## Minimum fields

Required:
- municipality
- energy class (A4, A3, A2, A1, B, C, D, E, F, G)

Strongly preferred:
- APE identifier or anonymised unique record identifier
- issue / submission date
- current validity / status
- EPgl,nren
- building destination/use category
- conditioned useful floor area

## Privacy

No owner, occupant, tax code, address-level personal information or other
personal data are required.

## Desired time coverage

Prefer all currently valid APE at extraction date. If current-validity filtering
cannot be applied, include dates/status so the project can apply it locally.

## Intended aggregate outputs

For each municipality:
- number of usable APE
- distribution by energy class
- share of classes E+F+G
- median EPgl,nren
- optional area-weighted class/EPgl summaries when useful floor area is present

The project will explicitly report APE coverage and selection bias and will not
treat the APE sample as a census of the housing stock.
