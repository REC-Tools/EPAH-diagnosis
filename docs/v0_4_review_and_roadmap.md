# v0.4 development review and proposed roadmap

Review date: 12 November 2026. Baseline: `1a7c9eb203498ccac87bf7f71d6bba987b07a416` (v0.3.0 software). This is a code and development-workflow review, not a scientific approval of territorial observations.

The recommended v0.4 is an **evidence and output integration release**: make the existing candidates usable across products, close validation gaps, and acquire the missing sources before expanding into more ambitious indicators. Keep the nine canonical indicators separate from experimental candidates until their methodology has been reviewed. Do not create a composite energy-poverty score.

## What was checked

- Reviewed the CLI and matrix/profile validation, candidate input contracts, atlas and report paths, provenance and audit handling, climate prototypes, local survey ingestion, release checks, CI, and current scientific/source documentation. This is a targeted review across those components; it does not establish that every line or possible input is defect-free.
- Ran the full suite after the code fixes: **732 passed**. The previous baseline had 716 tests; 16 regression cases were added. Targeted regressions reproduced the affected validation behavior before the fixes.
- Ran `epah data validate`, the v0.3 evidence and software-release checks, documentation links, repository hygiene, and historical heating-degree-day checks. Framework validation reports eight advisory warnings about uncatalogued dossiers; the climate comparison reports one ancillary altitude discrepancy and no HDD/climate-zone mismatches.
- Built a complete synthetic v0.1 bundle, v0.2 report, 27 municipal sheets, analysis, dashboard, review ZIP, and v0.3 atlas. These are software exercises with invented test observations and geometry, not local evidence or approvable territorial products.
- Exercised the generated atlas and dashboard using Playwright and system Chromium: 27 rows, 13 atlas choices, working search by ISTAT code, missing-candidate state without charts, loaded chart images, identical-series warning, no JavaScript errors, and no page overflow at a 390-pixel mobile width. Checked the desktop screenshot visually. Chromium's policy blocked `file://`; browser validation used a temporary local HTTP server, so direct file opening was not verified here.
- Reproduced two remaining defects with isolated synthetic inputs: stale H47 audit acceptance and wrong-year/incomplete legacy CDD calculation. Details are below.

Local review outputs are in ignored `artifacts/v04-review-synthetic/`. These artifacts are not a replacement for the real pilot bundle. Original pilot inputs and real candidate previews were unavailable in this cloud checkout. Release notes report real H47/H50/H46 audits, but those real-data results were **not independently rerun in this review**. Source availability, licences, and external APIs were not revalidated online.

## Fixes implemented in this review

| Area | Reproduced problem | Change and practical effect |
| --- | --- | --- |
| Municipality coverage | Matrix validation derived its expected scope from the municipalities already present. Removing an entire municipality, or substituting its name, could leave a structurally complete matrix. | Added an explicit municipality-registry option and wired it into `epah data validate`. The standard check now requires exact registered coverage. The generic API retains its previous behavior unless a registry is supplied. |
| Integrated profiles | A second municipality/indicator row silently replaced the first; numeric conversion accepted `NaN` and infinity. | Reject duplicate keys and non-finite observations before producing profiles. Downstream checks already rejected some such values; this closes the earlier entry point. |
| H46 atlas ingestion | Very large fixed-point strings became floating-point infinity. Reconciliation and percentage checks could then accept a `NaN` ratio. | Require finite parsed estimates and use an explicit absolute reconciliation tolerance. |
| Local survey counts | Blank answers became zero; fractional counts were truncated; duplicate municipality records were silently replaced during selection. | Require explicit nonnegative integer counts and reject duplicate normalized municipality names. Integer-valued spreadsheet forms such as `20.0` and `20,0` remain accepted. Missing answers now block this aggregate format; a future format should record per-question valid-response denominators. |
| Python warning | A Windows path in an accessibility-intake docstring produced an invalid-escape warning. | Made the docstring raw. |

No territorial observations, canonical definitions, approvals, dependency declarations, or lockfiles were changed. Existing generated releases were not rewritten. The software version remains 0.3.0; this work does not release v0.4.

## Remaining findings, ordered by priority

### P0 — fix before using the affected path for new evidence

**R1. An H47 audit is not bound to the exact preview consumed by the atlas.**

`load_h47_zip` checks the preview against its manifest and checks that the audit names the same original ZIP. The audit output does not contain the preview/QA digests, and the consumer does not recompute against the original source. A preview and its manifest can therefore be changed while retaining an older independent audit. The synthetic reproduction supplied 162 children in the preview with an audit of 135 children; the atlas accepted it as independently reproduced.

For v0.4, emit a versioned audit receipt containing the preview, QA, registry, raw source and normalization/mapping digests. Require those digests at ingestion; retain per-indicator audit identity in the shared observation model. Regenerate older receipts rather than silently upgrading their evidence level. Hash consistency proves integrity relative to a receipt, not the identity or authority of a reviewer. Acceptance: altering the preview or mapping and updating its local manifest still fails against the retained receipt. Apply the same receipt contract to H50/H46; the current atlas labels those as unreviewed mapping even when a separate independent audit exists.

**R2. Legacy climate prototypes accept incomplete annual evidence.**

`compute_municipal_cdd_from_netcdf` iterates all timestamps without enforcing the requested year or a complete calendar and silently skips unusable days. It also assumes Kelvin. A synthetic file containing only one day in 2024 produced 5 CDD labelled 2025. The UTCI prototype filters the year but similarly skips missing days and infers temperature units from the value. These are separate from the stricter v0.3 NWIOI H03/H04 path.

Before reuse, require CF units, exact calendar/year, daily or hourly frequency, unique timestamps, explicit missing-data policy and expected coverage. Bound and disclose spatial fallback distance. Route v0.4 climate candidates through validated adapters, with tests for wrong years, leap years, missing days/hours, units and duplicate timestamps. Never interpret a partial year as an annual measure. This prototype was not used to validate real climate results here.

**R3. Older finalizers bypass the newer candidate workflow.**

For example, `finalize_local_energy_affordability.py` writes to `data/indicators` and appends four uncatalogued indicators to the canonical matrix, marking reportable samples `Dato validato` without a methodology approval receipt or a reference period. Climate finalizers also append prototype indicators. These commands are not the guarded v0.3 candidate builders. Re-running the survey finalizer can overwrite its tables while retaining earlier matrix rows because existing keys are skipped.

Replace these entry points with preview-only builders targeting a fresh directory. Require explicit, reviewed promotion as a separate transaction; validate the catalog, period and complete update before any write. Stage multi-file outputs and promote atomically. Until migrated, do not use these prototype finalizers as v0.4 acquisition steps. The survey documentation now carries this warning.

**R4. Survey suppression currently leaves raw counts visible.**

The survey finalizer blanks percentages below ten respondents but still writes respondents and all four positive-answer counts. Those counts reconstruct the suppressed percentages. The minimum sample size is also not a test of representativeness or statistical precision.

Create separate restricted QA and shareable products. Suppress sensitive counts as well as percentages in shareable exports, and review complementary totals and cross-output disclosure. Record sampling, period, valid answers per question and nonresponse. Acceptance: a suppressed result cannot be reconstructed from the shareable CSV, HTML, PDF, or aggregate totals. This finding comes from inspection of the finalizer; no real survey was ingested.

### P1 — resolve in the v0.4 integration work

| Finding | Evidence and required change |
| --- | --- |
| Fixed indicator inventories | Atlas definitions, CLI flags, years and `13` slot counts are hardcoded. H04, H05 and ADD-HOUSING-01 have builders but no atlas slots; v0.2 PDFs/sheets have no shared candidate model. Introduce a separate versioned candidate catalog and validated adapters, leaving the canonical catalog unchanged. |
| Denominators disappear in presentation | `check_preview` verifies counts but returns only value/year. Show the numerator, denominator, population/stock universe, source vintage, audit state and small-denominator warning beside candidate percentages. Preserve H46 fractional estimates. |
| Pilot is a mandatory atlas dependency | The atlas requires the entire historical bundle, including unrelated products. Add a separately validated candidate-only review mode using the official municipality registry and geometry. Never silently bypass the pilot validator. |
| Ties are presented as distinct ranks | `_rank_descending` sorts equal values alphabetically and assigns successive ranks. Keep archived products unchanged; in v0.4 omit rank columns or specify a tie-aware rule. Value sorting alone is sufficient for descriptive charts. |
| Statistical independence wording | Some output text calls the eight dimensions independent while the analysis correctly states independence is not established. Use “separate indicators”; keep the identical-series warning. Identical school/rail series are documented, not newly proven erroneous here. |
| Documentation has mixed time states | The scientific registry preserves early-stage H50/H46 descriptions, while release notes report real audits. Label historical acquisition stages and point to a single current status table. The source workbook transcription should remain historical evidence, not be rewritten as a live status registry. |
| Freshness is not semantic validity | Source monitoring checks reachability and potential next-year URLs. A 200 response does not establish a valid archive, schema, geography or unchanged definition. Add content/schema probes and separate reachability, acquisition, QA and review states. |

## Indicator choices for v0.4

“Available pipeline”, “source identified”, “real preview reported” and “approved indicator” are different states. The sources below are those already documented in the repository; current download access and usable 27/27 coverage remain to be demonstrated where stated.

| Priority | Indicator | Source / existing work | v0.4 scope and acceptance |
| --- | --- | --- | --- |
| A: integrate | H47 residents 0–11 | ISTAT POSAS 2026; original-source reproduction exists | Carry age, date, population counts and provisional flags into all products. Align the vintage with the older-age series before combining demographic context. |
| A: integrate | H50 adults 25–64 without lower-secondary completion | ISTAT Census 2024; normalization and audit scripts exist | Preserve the exact educational categories and adult denominator; validate original metadata and mapping receipt. Do not relabel this as all low education. |
| A: integrate | H46 unemployment among labour force 15+ | ISTAT Census 2024; acquisition, normalization and audit exist | Show employed/unemployed/active denominators and prominent small-denominator notes. Do not round estimated people to integers. Never use one minus employment. |
| A: acquire jointly | H03 annual estimated HDD and H04 CDD | ARPA NWIOI daily Tmin/Tmax; strict builders already exist | Acquire and checksum originals and mask; validate complete year, units, spatial alignment and mountain-cell representativeness. Keep normative DPR HDD separate. Share the validated daily input between the two calculations. |
| A: acquire | ADD-HOUSING-01 dwellings not occupied by residents | ISTAT Census sections 2023; aggregate builder exists | Verify dictionary, section handling, geography and category reconciliation. Label the measure literally; it does not establish vacant homes or second homes. |
| B: acquire conditionally | H05 valid residential APE F/G | Piemonte SICEE/SIPEE or ENEA SIAPE; normalized builder exists | Require residential scope, validity date, unique certificate handling and complete class totals. Display the certificate denominator and coverage bias; do not infer whole-stock performance from certificates. |
| B: pilot | H27 population beyond walking access to an active transit stop | Regional bus/rail GTFS plus inhabited origins/population | Use service calendars and walking-network distance, with a documented threshold such as the inventory's 1 km. A stop point or municipal centroid alone is insufficient. Prove feed licence, coverage and service validity first. |
| B: pilot | H28 useful public-transport service frequency | Same GTFS acquisition | Define weekday, school holiday, weekend, time windows, directions and useful destinations. Deduplicate trips; distinguish no service from missing feed. |
| C: later | H26 essential services within one hour without a car | GTFS, walking network, service destinations | Route complete journeys including waits and transfers. Consider after H27/H28, because assumptions and timetable validation are substantially more demanding. |
| C: local evidence | Warmth, utility arrears, cooling difficulty, heating self-restriction | Existing aggregate survey prototype | Redesign the collection contract and disclosure controls first. Describe results as shares of respondents unless sampling supports population estimates; do not infer municipal prevalence from a convenience sample. |
| Context only | Direct hardship, energy poverty and tariff benchmarks | Eurostat EU-SILC, OIPE, ARERA | Separate national/regional comparison panel with geography, period and definition. Do not paint regional rates onto municipalities or treat a tariff as actual household expenditure. |

Defer municipal gas-consumption ratios, health-condition rates, social-housing energy performance and assistance effectiveness until suitable primary data, denominators and coverage exist. Do not impute missing municipal evidence from national rates. CIT remains quarantined. Heat/cold-wave indicators also need an agreed threshold, duration and climatological baseline; a single warm day or annual CDD is not a heatwave frequency.

## Better outputs: concrete requirements

1. **One observation contract for every product.** Store municipality code/geography version, indicator/version, period, value/unit, numerator/denominator and universe, missingness reason, source/mapping hashes, QA/audit/review states and caveats. Separate arithmetic QA from methodological and publication approval. Retain technical precision; round only for display.
2. **Atlas for all supported candidates.** Discover metrics from the candidate catalog. Add family filters, a municipality detail view, accessible table export, value/period/source details and links to the evidence receipt. Retain sequential map scales, categorical SNAI and explicit units; never turn context into a red/green risk grade. Add stable scale choices for genuine comparisons across years.
3. **Consistent PDF and municipal sheets.** Generate tables and charts from the same observation objects used by HTML. Include candidate sections, denominators, freshness and missingness notes. Add map locators/labels, readable legends and print layouts; avoid dense charts whose text becomes illegible at mobile size. Show neutral “not acquired”, “missing”, “suppressed” and “not comparable” states distinctly.
4. **Useful comparison without a score.** Offer side-by-side municipalities and pairwise scatterplots with exact period/universe labels. Weighted territorial percentages require sums of compatible numerators and denominators, not averages of municipal percentages. Clearly separate those from unweighted municipal medians. Avoid automatic causal interpretations.
5. **One auditable build command.** A proposed interface is `epah atlas v0.4 --run-config ... --out-dir ...`, with explicit inputs and fresh output directory. Produce HTML, PDF/sheets, tidy observation CSV, definitions, QA summary and a manifest from the same run. Validate every exported artifact against the observations, and preserve source/version information. This interface is a proposal, not implemented yet.

## Implementation sequence and release gates

| Step | Deliverable | Exit condition |
| --- | --- | --- |
| 1. Hardening | Close R1–R4; retain the fixes in this review | Stale receipts, wrong/incomplete calendars, unreviewed promotion and suppression reconstruction have failing regression tests and are blocked. |
| 2. Shared model | Candidate catalog, adapters and evidence receipts | H47/H50/H46 synthetic and real fixtures round-trip without losing denominators or evidence state; canonical data stays unchanged. |
| 3. Source completion | Shared H03/H04 input, housing and conditional H05 acquisition | Original files, licences and mappings are archived; independent checks reproduce values and coverage. An unavailable source stays explicitly unavailable. |
| 4. Output integration | Atlas plus matched technical PDF/sheets and machine-readable exports | All supported adapters render; absent and suppressed results remain distinct; browser, mobile, print and semantic artifact checks pass. |
| 5. Optional mobility | H27/H28 pilot with documented service dates | Reviewed GTFS calendars and populated origins reproduce sample journeys; extend to H26 only after this works. |
| 6. v0.4 software release | Versioned schemas, migration notes and release metadata | Tests and new adversarial cases pass; real-input replay is recorded; publication remains a separate documented decision. |

The minimum useful v0.4 can integrate the three existing demographic/socioeconomic candidates with better outputs, while accurately showing the other four candidates as pending. A larger v0.4 can add those four after source acquisition and QA. Avoid making the software release depend on speculative mobility or survey data. Do not promise a fixed delivery date until access to the missing originals and the scope of their QA are established.

## Recheck commands

From the repository with the configured Python 3.11 environment:

```bash
uv run --locked pytest -q
uv run --locked epah data validate
uv run --locked python scripts/check_v0_3_evidence.py
uv run --locked python scripts/check_v0_3_release.py
uv run --locked python scripts/check_documentation.py
uv run --locked python scripts/audit_repository_hygiene.py --check --json-out /tmp/epah-hygiene-review.json
```

For an explicit registry-aware low-level matrix check:

```bash
uv run --locked python -m epah_diagnosis.cli validate-matrix data/verification_matrix.csv \
  --catalog config/indicators.json --municipalities data/municipalities.csv
```

The outstanding findings above are a development backlog, not completed fixes. Passing synthetic tests does not certify the unavailable local originals or authorize territorial publication.
