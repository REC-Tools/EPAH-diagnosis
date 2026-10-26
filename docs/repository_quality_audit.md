# Repository-wide quality audit — 26 October 2026

This is a source-tree audit. A passing unit-test workflow is not evidence of successful fresh remote data acquisition or scientific validation.

## P0 — Correctness
- The integrated readiness check previously iterated only over municipalities present in the matrix: an empty matrix could wrongly report READY. Fixed by validating against the canonical 27-municipality registry; unexpected names and duplicate keys also fail.
- Verify all producer scripts use the catalog IDs and do not overwrite unrelated matrix fields.
- Preserve the baseline snapshot and validated observations when generating or updating indicators.

## P1 — Data completeness and provenance
- The matrix has 9 cataloged dimensions; two additional documented experimental directions (heating facilities gap and SIPEE/APE) are **not cataloged yet**. Do not silently include them in the canonical 9 × 27 matrix.
- Require source URI, retrieval date, dataset vintage, checksum/license check, method version, QA decision, and limitations before publishing verified results.
- Distinguish `Dato acquisito`, `Dato validato`, methodological maturity, and missing data. The climate snapshot is acquired, not independently validated against the primary normative text.
- Financial and demographic values marked validated are historical states; their current reproducibility should be rechecked separately.

## P1 — Automation and integration
- `model.py` maintains a 3-indicator legacy registry, while `config/indicators.json` has 9. Prefer the catalog for new validation/output paths and explicitly label legacy CLI operations.
- Upsert of `verification_matrix.csv` is atomic, but output CSVs are written earlier: there is no multi-artifact transaction, provenance manifest, or rollback for partial failures.
- Remote downloaders (ISTAT, MEF, MIM and matrices) need isolated end-to-end tests, timeout/retry and response validation; do not add such network checks to deterministic offline CI.
- Ensure readiness checks the expected municipality universe (implemented here) and distinguish partial reports from nine-dimensional complete profiles.

## P2 — Maintainability and delivery
- The README had an outdated historical roadmap and inaccurate references to an eight-indicator registry. Replace with current commands and evidence-based status.
- Duplicate building-stock finalizers write the same outputs; only one should be designated canonical, with the other explicitly legacy.
- Add reproducible one-command snapshot build + QA summary only after input contract stabilization.
- Prioritize an Excel export and maps that show individual indicators and missingness; avoid an unsupported composite energy poverty score.

## Proposed sequence
1. **Now:** repository integrity and documentation (this PR).
2. **Next:** automated completeness report with CSV/JSON outputs for 27 × 9 dimensions, without changing statuses.
3. **Then:** verified acquisitions and provenance for building stock, altimetry, SNAI and service accessibility.
4. **Finally:** partial/complete profiles, thematic maps, Excel and EPAH narrative report.
