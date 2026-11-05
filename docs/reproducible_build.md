# Reproducible build environment and core replay checks

The Python project dependencies and development/test dependencies are resolved
in the committed `uv.lock` file. Python 3.11 is the supported CI baseline.
The version of the `uv` installer used in CI is pinned separately in the workflow.

## Clean installation (Windows PowerShell)

Install the `uv` package manager (version 0.10.0 for the CI baseline).
From a fresh clone, run:

```powershell
uv sync --python 3.11 --locked --group dev
uv run --locked python scripts/check_pilot_inputs.py
uv run --locked pytest -q
```

A preflight status of `blocked` is expected when the locally stored official
archives and access QA drafts are absent. Do not commit source archives or
approvals to make a test pass. The unit tests use synthetic fixtures.

## Compare the deterministic core of two builds

When two completed pilot bundles have been built from *the same inputs*
with separate output paths:

```powershell
uv run --locked python scripts/check_pilot_replay.py outputs/v0.1.0-pilot outputs/v0.1.0-pilot-replay
```

This compares the parsed contents of `municipality_profile.csv`,
`municipality_comparison.csv`, and `municipality_profile.geojson` (including
coordinates and properties). It does not compare PDFs, maps, XLSX workbooks,
ZIP archives, or manifests, whose metadata and rendering may vary. A match
does **not** certify the original source or methodological approval.

The CI runs the locked environment on a fresh GitHub Actions runner and
performs two separate complete synthetic release builds to verify that the
numerical core agrees.

## Updating dependencies

Edit `pyproject.toml` intentionally, then regenerate with `uv lock`.
Review all transitive changes in `uv.lock`, and rerun the CI. Never
automatically upgrade dependencies on a published release branch. Maintain
existing source QA gates, human sign-off and the no-overwrite release rule.
