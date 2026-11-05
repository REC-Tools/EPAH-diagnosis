"""Read-only post-build v0.2 review ZIP integrity check, not approval."""
from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

from epah_diagnosis.review_package_v0_2 import verify_review_package

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / "outputs/v0.2-review-candidate"


def main() -> int:
    p = argparse.ArgumentParser(
        description="Check v0.2 review folder, hashes and ZIP; never authorize publication"
    )
    p.add_argument("--dir", type=Path, default=DEFAULT)
    args = p.parse_args()
    try:
        result = verify_review_package(args.dir)
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile) as exc:
        print(f"BLOCKED: {exc}")
        return 1
    print(json.dumps(result, indent=2))
    print("INTEGRITY ONLY. Human approvals and PDF visual QA remain pending.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
