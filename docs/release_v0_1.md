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

The complete release bundle is written to `outputs/v0.1/` and contains:

- **27x9** validated municipality profile CSV and independent-dimension comparison CSV;
- official ISTAT geometry-enriched GeoJSON, checked against 27 six-digit codes;
- eight continuous indicator maps and one **categorical SNAI** A–F map (PNG);
- `completeness.xlsx`: Overview, Municipalities, Indicators, Comparison,
  and 243-row Matrix_Evidence with source/quality/limitations;
- `diagnostic_report.pdf`: narrative municipal screening, indicator distributions,
  source-vintage table and methodological limitations;
- `RELEASE_NOTES.md`, `readiness.json` and `release_manifest.json`.


## What v0.1 does not claim

It does not identify energy-poor households, replace household-level evidence,
calculate an EPAH-certified index, or aggregate all dimensions into one score.

## Release-gate policy (PR-01)

The release checker has two phases:

- `python scripts/check_v0_1_readiness.py --phase inputs` assesses the
  completeness and basic plausibility of the 27 x 9 dataset plus human
  methodological approvals. The bundle builder uses this input gate.
- `python scripts/check_v0_1_readiness.py --phase release` additionally
  requires non-empty expected release artifacts under `outputs/v0.1/`.
  Artifact existence checks are a first safeguard. The bundle builder
  additionally performs format, geometry, report, workbook and manifest QA,
  covered by synthetic integration tests; neither check certifies raw sources.
- `--report-only --json-out outputs/quality/v0_1_readiness.json` reports
  all blockers but exits successfully. CI uses this to track progress without
  requiring a completed v0.1 on every development PR.

Validated matrix rows must include finite/plausible values, catalog-compatible
units, year, source URL, quality and limitations. The checker cannot authenticate
the origin of a source, verify legal provenance or establish that a reviewer
actually signed off; these remain human QA responsibilities.

Methodology approval is **not** derived from matrix status. Record explicit
reviews in `config/release_reviews_v0_1.json` using:

```json
{
  "indicator_id": "population_65_plus",
  "decision": "approved",
  "reviewed_by": "Name of actual reviewer",
  "reviewed_on": "YYYY-MM-DD",
  "evidence_url": "https://github.com/REC-Tools/EPAH-diagnosis/pull/..."
}
```

The reviewer must examine the evidence independently. The corresponding catalog
entry must also have maturity `OPERATIONAL` or `VALIDATED`.
All nine remain `EXPERIMENTAL` in the present baseline: do not
manufacture approvals to make the gate green.

The current `config/release_v0_1.json` includes the final artifact list, and
`scripts/build_v0_1_bundle.py` implements the gated output pipeline. The
release gate remains NOT READY until actual data, methodology approvals,
official boundaries and content QA are complete.


## PR-08 — single-command bundle, gated on real source approvals

```bash
# Only after all nine indicators have 27/27 independently verified values
# and catalog maturity + genuine human methodology approvals.
python scripts/check_v0_1_readiness.py --phase inputs
python scripts/build_v0_1_bundle.py \
  --boundaries data/geography/municipalities_2026.geojson
python scripts/check_v0_1_readiness.py --phase release
```

Generate the boundaries beforehand with
`python scripts/acquire_municipality_boundaries.py`.
The command performs **no downloads**, never fabricates missing observations,
and cannot be forced past the input gate. Its output is staged in a temporary
directory and atomically moved to the final path only after content QA.
It refuses to overwrite an existing release; `--replace` permits replacement
after building and validating the new bundle, with rollback on move failure.

The nine thematic maps use consistent indicator-specific numeric scales;
SNAI A–F is mapped with categorical colors, never a numeric risk score.
Geographic QA verifies precisely 27 distinct official ISTAT codes, complete
closed Polygon/MultiPolygon rings, nonzero geometry, valid WGS84 coordinates,
and one row per municipality. Map renderer preserves holes by orienting
interior rings opposite to outer rings. Report and workbook state that
municipal-level screening does not identify households.

**Manifest transparency:** SHA-256 and byte sizes are recorded for
15 independent artifacts (all except `release_manifest.json` and
`readiness.json`, which cannot self-hash without recursion) and for
the six canonical **processed input files** (matrix, registry, catalog,
review record, release config and boundaries).
It does **not** prove provenance of the raw ISTAT/MIM/Ministry source
archives; their hashes and acquisition records must be stored in the
indicator-specific QA evidence from PR-03 to PR-07. The output validator
checks file formats, 27x9 coverage, GeoJSON geometry, Excel sheets,
PDF signature, nine PNG headers/dimensions and all manifest hashes.
Full scientific source verification remains the responsibility of the
reviewers in PR-09.

The committed matrix is intentionally **NOT READY** (30 October 2026):
162 of 243 observations have status `Dato validato` (27 each for population,
income, building stock, heating degree days, altitude, and SNAI). The other
**81** are empty and `Da verificare` (27 each for DEA, upper-secondary schools
and rail accessibility). All nine methodologies remain `EXPERIMENTAL`
with no recorded release approval.
Therefore a production `build_v0_1_bundle.py` run should exit nonzero
with no `outputs/v0.1/` directory created. The end-to-end test uses
**synthetic fixtures** with artificial review metadata and never publishes
those fixtures as observational data.

## Live CI progress towards v0.1

The CI workflow creates an indicator-by-indicator progress table in the GitHub
Actions job summary and the `v0-1-readiness` artifact. This distinguishes
row-level prerequisites, human methodology sign-off and final bundle readiness.
Run locally:

```bash
python scripts/check_v0_1_readiness.py --phase release --report-only --json-out outputs/quality/v0_1_readiness.json
python scripts/summarize_v0_1_progress.py --readiness outputs/quality/v0_1_readiness.json --output outputs/quality/v0_1_progress.md
```

The report is read-only: it neither endorses data nor bypasses a release blocker.
