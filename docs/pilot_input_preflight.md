# Offline input preflight — technical v0.1.0 pilot

Before building the owner-accepted technical pilot, run from the repository root:

```powershell
python scripts/check_pilot_inputs.py
```

To save a machine-readable inventory to a **new** file only:

```powershell
python scripts/check_pilot_inputs.py --json-out outputs/quality/pilot_inputs_20261105.json
```

The command checks that the 12 expected files are present and readable, and
prints their relative paths, byte sizes, and actual SHA-256 hashes. It uses
only the Python standard library, does not download sources, does not touch
canonical data, and does not build or release anything. Exit code **0**
means all files are readable; exit code **1** means at least one is missing
or unreadable. Existing JSON reports are never overwritten.

**Important:** presence and digest checks are not source verification,
methodological approval, consistency checks, or an institutional release.
The actual pilot builder still enforces the detailed QA and review gates.
A file with unexpected contents can pass this preflight and fail the build.
The report is a local inventory, not a reproducibility guarantee.

Required local inputs include the three accessibility draft CSV/QA pairs,
the nine-route ISTAT sample evidence and the official boundary ZIP. Paths
are the *default paths* for `build_v0_1_owner_accepted.py`; if its command-line
arguments override locations, use a matching input layout for this check
or rely on the builder's own validation.

When all default inputs are ready:

```powershell
python scripts/build_v0_1_owner_accepted.py
```

Do not overwrite a previous pilot bundle or promote draft data to the
canonical matrix without the documented review process.
