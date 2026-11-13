"""Audit a v0.4 technical review pack: hashes, HTML/CSV agreement and PDF structure."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from epah_diagnosis.output_quality_v0_4 import audit
from epah_diagnosis.output_bundle_quality_v0_4 import audit_bundle


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--pack", type=Path)
    target.add_argument("--hub", type=Path, help="Complete integrated output hub (Step 9)")
    parser.add_argument("--atlas", type=Path, help="Optional original atlas to verify provenance")
    parser.add_argument("--json-out", type=Path, help="Optional new quality report path")
    args = parser.parse_args(argv)
    try:
        inputs = [args.hub] if args.hub else [args.pack, args.atlas]
        if args.json_out and any(args.json_out.resolve().is_relative_to(source.resolve())
                                 for source in inputs if source is not None):
            raise ValueError("Quality report must be outside input snapshot directories")
        if args.json_out and args.json_out.exists():
            raise FileExistsError("Quality report already exists; no overwrite")
        if args.hub and args.atlas:
            raise ValueError("--hub uses its own packaged atlas; do not supply --atlas")
        result = audit_bundle(args.hub) if args.hub else audit(args.pack, atlas=args.atlas)
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
