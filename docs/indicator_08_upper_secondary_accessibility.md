# Access to a complete upper-secondary education pole

## Indicator

Road travel time, in minutes, from each Green Community municipality to the
nearest municipality with a **complete upper-secondary education offer**.

## Service definition

The definition follows the SNAI / ISTAT methodology.

A municipality qualifies as an education service pole when it offers:

1. at least one classical or scientific lyceum; and
2. at least one technical or professional pathway.

This is deliberately stricter than "nearest high school" because it measures
access to a meaningful range of upper-secondary education options.

## Education sources

The Ministry of Education and Merit (MIM) Open Data Portal publishes:

- the official school registry, with school code and municipality;
- upper-secondary students by active pathway, including `TipoPercorso`,
  `Percorso` and `Indirizzo`.

The current pipeline uses school year **2024/25**, the latest school-year
distribution available for the pathway dataset at implementation time.

## Travel-time source

Travel times use the same official ISTAT municipal origin-destination matrix as
the DEA indicator:

- `TEP_TOT`: effective road travel time;
- `KM_TOT`: route distance;
- municipal geography: 1 January 2021;
- road graph: 2020.

Using the same matrix makes health and education accessibility directly
comparable.

## Interpretation

The result is a municipal territorial-accessibility proxy. It does not measure:

- actual school-bus or public-transport travel time;
- timetable compatibility;
- student choice beyond the SNAI service definition;
- capacity, quality or availability of places in individual schools.

Run:

`python scripts/finalize_upper_secondary_accessibility.py`

Outputs:

- `data/reference/upper_secondary_poles_2024_25.csv`
- `data/indicators/upper_secondary_accessibility_minutes.csv`
- `data/indicators/upper_secondary_accessibility_summary.csv`
- 27 validated rows in the verification matrix
