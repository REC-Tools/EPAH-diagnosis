# Indicator 14 - Heating fuel mix

## EPAH alignment

EPAH recommends considering the dwelling heating system and final-energy fuel
mix together with income and energy efficiency. Different heating fuels expose
households to different price, availability, infrastructure and transition
risks.

## Official source

ISTAT 2011 Population and Housing Census, municipal tables on occupied
dwellings with a heating system by **type of fuel or energy feeding the heating
system**.

The census dissemination plan includes municipality-level tables A2.4/A2.5
covering heating facilities and type of fuel/energy.

Categories retained by this project:

- natural gas / methane;
- diesel / gas oil;
- LPG;
- solid fuel, including wood/coal;
- fuel oil;
- electricity;
- other fuel or energy.

## Primary indicator

**Share of heated occupied dwellings using a fuel/energy source other than
natural gas**

Formula:

`100 * (heated dwellings - natural gas dwellings) / heated dwellings`

The full fuel mix is always retained. The primary percentage is a descriptive
territorial indicator, not an energy-poverty score.

## Required input

Export the official ISTAT municipality table to:

`data/raw/istat_heating_fuel_mix_2011.csv`

A template is available at:

`data/reference/istat_heating_fuel_mix_2011_template.csv`

The parser accepts common Italian aliases for the municipality and fuel
columns.

## Pipeline

`python scripts/finalize_heating_fuel_mix.py`

Outputs:
- `data/indicators/heating_fuel_mix_2011.csv`
- `data/indicators/heating_fuel_mix_summary_2011.csv`
- 27 validated verification-matrix rows.

## Interpretation

A high non-natural-gas share is **not automatically a vulnerability**. In an
Alpine municipality it may reflect wood/biomass availability, LPG dependence,
electric heating, or other local conditions.

The detailed fuel composition should therefore be cross-read with:
- Heating Degree Days;
- income vulnerability;
- old building stock;
- heating-facilities gap;
- SIPEE energy performance when available;
- current fuel prices and affordability indicators.

## Limitation

The 2011 census is a structural baseline. Heating technologies and local gas
network coverage may have changed substantially since then. A future version
should replace or complement this baseline with newer municipal or distributor
data where available.
