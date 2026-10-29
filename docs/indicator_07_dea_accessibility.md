# Access to DEA I/II hospitals

## Indicator

Road travel time, in minutes, from each Green Community municipality to the
municipality hosting the nearest **DEA level I or II** hospital.

This is the first disaggregated service-access indicator in the territorial
isolation block.

## Why DEA I/II

The SNAI methodology uses the presence of a DEA level I/II hospital as one of
the three service requirements for identifying service poles.

For the Canavese context this distinction matters. Cuorgne has an emergency
department / Pronto Soccorso for a disadvantaged area, but is not treated as a
DEA I/II destination in this indicator. A later sensitivity analysis can add
"access to any emergency-care facility" as a separate variable.

## Road travel time source

ISTAT publishes updated origin-destination matrices containing road distance
and travel time between all Italian municipalities.

The current matrix:
- uses municipal geography at 1 January 2021;
- uses a commercial road graph updated to 2020;
- calculates routes by minimizing travel time and accounting for road type and
  traffic assumptions;
- is distributed as regional ZIP files containing CSV data.

Piemonte download:
`https://www.istat.it/storage/cartografia/matrici_distanze/Piemonte.zip`

## DEA network source

The Ministry of Health publishes an annual national register of emergency
hospital facilities. The 2025 release includes facility name, code, address,
type and emergency level (DEA I, DEA II, emergency department and paediatric
emergency department).

Because the Ministry download page may enforce browser validation, the
repository stores a versioned Piemonte DEA reference snapshot and documents
the official source for annual review.

The Piemonte network is cross-checked against Regione Piemonte hospital-network
documents.

## Interpretation

The indicator is a municipal accessibility proxy. It does **not** represent:
- the door-to-door travel time of each resident;
- ambulance response time;
- actual access by public transport;
- waiting time at the hospital.

For large mountain municipalities, using a single municipal origin can
understate or overstate the travel burden of dispersed hamlets. A later
version may use populated localities or population-weighted origins.

Run the offline, review-gated preparation and finalization described in [DEA QA procedure](dea_accessibility_qa.md). Outputs are not validated automatically; the current 27 matrix rows remain `Da verificare` until independent review.
