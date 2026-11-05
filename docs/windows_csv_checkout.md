# Windows checkout: reviewed CSV SHA-256 integrity

Reviewed CSV evidence for the 2011 building stock and 2020/2021
territorial indicators has immutable byte-level SHA-256 digests.
Git on Windows may convert LF to CRLF during checkout, changing SHA-256
without changing CSV values. This was confirmed for the Windows errors
in test_building_2011_promotion.py, test_priority_81_promotion.py and
test_priority_source_archive.py on 2026-11-05.

The new .gitattributes restricts LF checkout to the ten already-reviewed
CSV paths. No historical data or evidence hash is changed.

## Read-only diagnosis

From the repository root in PowerShell:

~~~powershell
uv run --locked python scripts/check_source_csv_checkout.py
~~~

Every file is reported with one of the following statuses:

- ok: bytes match the original SHA-256.
- crlf_checkout: the exact original bytes are recoverable by CRLF -> LF only.
- unexpected_bytes: other changes detected, no automatic repair allowed.
- missing or unreadable: cannot verify local input.

## Safe repair of an older Windows working tree

After merging the PR and running git pull, a previous Windows checkout
may still contain CRLF. Repair only when the normalized bytes match
the pre-existing, immutable evidence hashes:

~~~powershell
uv run --locked python scripts/check_source_csv_checkout.py --repair-crlf
uv run --locked pytest -q
git status --short
~~~

The repair flag intentionally rewrites affected *local* CSV files.
It is not a promotion, source download, or QA approval. It refuses
to edit any file that differs beyond line endings. An atomic local
replacement is used only after matching the expected SHA-256.

Do not update recorded evidence SHA-256 values to match CRLF,
and avoid broad git restore, git reset --hard, git clean, or
git add --renormalize commands: these can discard local work
or introduce unrelated data changes.

If any status is unexpected_bytes, preserve the file and investigate
the discrepancy against Git history and the source evidence.

The canonical v0.1 release is still blocked until its separate
data and methodology review gates are satisfied.
