# Roadmap to v0.1

## Definition of v0.1

Version 0.1 is a **territorial screening toolkit**, not a final energy-poverty
measurement system.

A v0.1 release is considered ready when:

1. all 27 municipalities are represented;
2. the nine core indicators are present, validated and non-empty for every municipality;
3. the integrated municipality profile is reproducible;
4. the per-dimension comparison table is reproducible;
5. the profile can be joined to official ISTAT municipality boundaries;
6. diagnostic maps can be generated from the integrated profile;
7. completeness and release readiness can be checked offline;
8. no composite energy-poverty score is produced;
9. external-data extensions are explicitly reported as non-blocking.

## Core v0.1

The core remains the nine already integrated dimensions:

1. population aged 65+;
2. income vulnerability;
3. old residential building stock;
4. heating degree days;
5. mean altitude;
6. SNAI classification;
7. road accessibility to DEA I/II;
8. road accessibility to upper-secondary education;
9. road accessibility to an active rail gateway.

## Extensions already implemented

The repository also contains post-core modules:

- heating facilities gap;
- SIPEE poor energy-label share;
- Cooling Degree Days;
- Heat Stress Days / UTCI;
- heating fuel mix;
- local energy affordability and thermal comfort.

These are deliberately **not release blockers** for v0.1 because some depend on
external extraction, authentication or new local data collection.

## Release commands

    pytest -q
    python scripts/check_framework.py
    python scripts/check_v0_1_readiness.py
    python scripts/build_v0_1_bundle.py

For canonical maps:

    python scripts/build_municipality_profile.py
    python scripts/build_municipality_geojson.py
    python scripts/generate_diagnostic_maps.py

For completeness inventory:

    python scripts/report_completeness.py
    python scripts/export_completeness.py

## Release artifacts

The bundle is written to outputs/v0.1/ and contains:

- integrated municipality profile;
- municipality comparison table;
- enriched GeoJSON;
- machine-readable readiness report;
- release manifest;
- release notes.

## What v0.1 does not claim

It does not identify energy-poor households, replace household-level evidence,
calculate an EPAH-certified index, or aggregate all dimensions into one score.
