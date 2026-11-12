"""Audit a v0.4 technical review pack: hashes, HTML/CSV agreement and PDF structure."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from epah_diagnosis.output_quality_v0_4 import audit


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", required=True, type=Path)
    parser.add_argument("--atlas", type=Path, help="Optional original atlas to verify provenance")
    parser.add_argument("--json-out", type=Path, help="Optional new quality report path")
    args = parser.parse_args(argv)
    try:
        if args.json_out and args.json_out.exists():
            raise FileExistsError("Quality report already exists; no overwrite")
        result = audit(args.pack, atlas=args.atlas)
        if args.json_out:
            args.json_out.parent.mkdir(parents=True, exist_ok=True)
            with args.json_out.open("x", encoding="utf-8") as handle:
                json.dump(result, handle, indent=2, ensure_ascii=False)
                handle.write("\n")
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        parser.exit(2, f"BLOCKED: {exc}\n")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
