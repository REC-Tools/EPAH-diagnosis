# Heating facilities gap

## EPAH alignment

EPAH includes the availability of heating facilities among its housing/facility
indicators. At local scale, this project uses an inverse dwelling-based proxy:

**share of occupied dwellings with resident population without a heating
system**.

A higher value indicates a larger housing-equipment gap. It does not by itself
identify energy-poor households.

## Source and formula

Source: ISTAT 2011 census-section variables from the public CPA archive.

Variables:
- `A2`: occupied dwellings with resident population;
- `A24`: occupied dwellings with resident population provided with a heating
  system.

Formula:

`100 * (A2 - A24) / A2`

Section-level values are summed to municipality before calculating the share.

## Limitations

The 2011 reference year is old and should be treated as a structural baseline.
The indicator measures the presence of heating equipment, not:
- affordability of its use;
- energy expenditure;
- heating-system efficiency;
- adequacy of indoor temperature;
- thermal comfort.

It should therefore be cross-read with income vulnerability, heating degree
days, old building stock, and future expenditure / thermal-comfort indicators.

Run:

`python scripts/finalize_heating_facilities_gap.py`

Outputs:
- `data/indicators/heating_facilities_gap_2011.csv`
- `data/indicators/heating_facilities_gap_summary_2011.csv`
- 27 validated rows in the verification matrix.
