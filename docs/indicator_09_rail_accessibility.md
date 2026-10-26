# Accessibility to the railway network

## Indicator

Road travel time, in minutes, from each Green Community municipality to the
nearest municipality with a station listed in the current RFI public station
catalogue.

This is the third disaggregated service-access indicator after health and
upper-secondary education.

## RFI source

RFI publishes a public national station catalogue with:

- station name;
- address;
- municipality;
- province;
- current station classification.

The current RFI classification has six clusters:

- MAIN HUB
- HUB
- MAJOR
- PLUS
- LOCAL PLUS
- LOCAL

It replaces the former Platinum / Gold / Silver / Bronze system.

For this indicator all current RFI public stations in Piemonte are eligible
destinations. The current RFI class is retained as metadata and is **not**
converted into an arbitrary score.

## Relationship with SNAI

The historical SNAI method used a railway station of at least the former
Silver class as one of the service-pole requirements.

The EPAH diagnosis keeps that historical SNAI classification separate from
this current operational measure. This indicator answers a simpler question:

**How long does it take by road to reach the nearest current RFI station?**

A later sensitivity analysis may restrict destinations to higher-order RFI
classes if useful.

## Travel-time source

As for DEA and upper-secondary education, the accessibility calculation uses
the official ISTAT municipal origin-destination matrix:

- TEP_TOT: effective road travel time;
- KM_TOT: route distance;
- municipal geography: 1 January 2021;
- road graph: 2020.

## Limitations

This indicator does not measure:

- frequency of train services;
- current timetable quality;
- line closures or replacement buses;
- public-transport travel time from the municipality to the station;
- distance from individual hamlets to the station.

Run:

`python scripts/finalize_rail_accessibility.py`

Outputs:

- `data/reference/rfi_piemonte_stations_current.csv`
- `data/indicators/rail_accessibility_minutes.csv`
- `data/indicators/rail_accessibility_summary.csv`
- 27 validated rows in the verification matrix
