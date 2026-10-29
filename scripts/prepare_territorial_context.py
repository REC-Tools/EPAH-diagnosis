"""Build non-validated 27-municipality drafts from an official XLSX, offline."""
from __future__ import annotations

import argparse
from pathlib import Path

from epah_diagnosis.territorial_context_qa import CONFIG, write_draft

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare draft altitude or SNAI observations")
    parser.add_argument("--indicator", required=True, choices=sorted(CONFIG))
    parser.add_argument("--source-xlsx", type=Path, required=True)
    parser.add_argument("--registry", type=Path, default=ROOT / "data/municipalities.csv")
    parser.add_argument("--out-dir", type=Path, help="Fresh destination directory for unvalidated outputs")
    args = parser.parse_args()
    destination = args.out_dir or ROOT / "outputs" / "quality" / args.indicator
    qa = write_draft(args.indicator, args.source_xlsx, args.registry, destination)
    print(
        f"Draft {args.indicator}: {qa['target_municipalities']}/27 municipalities, "
        f"{qa['source_record_count']} source rows. "
        "Technical checks only; no matrix changed and no scientific approval."
    )


if __name__ == "__main__":
    main()
