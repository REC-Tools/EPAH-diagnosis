"""Compatibility entry point: preview-only survey output, never canonical promotion.

Requires a fresh --out-dir and explicit --period-start / --period-end.
"""
from epah_diagnosis.experimental_previews import affordability_main as main

if __name__ == "__main__":
    raise SystemExit(main())
