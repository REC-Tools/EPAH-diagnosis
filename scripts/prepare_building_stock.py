"""Create a reviewable CPA-2011 draft from a locally downloaded official ZIP.

This never modifies the verification matrix and does not certify provenance.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path

from epah_diagnosis.building_stock_qa import (
    BENCHMARK_COLUMNS, BUILDING_COLUMNS, prepare,
)

ROOT = Path(__file__).resolve().parents[1]


def _csv_bytes(fields: list[str], records: list[dict]) -> bytes:
    handle = io.StringIO(newline="")
    writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(records)
    return handle.getvalue().encode("utf-8")


def prepare_files(source_zip: Path, registry: Path, out_dir: Path, *,
                  min_italy: int = 7000, min_piemonte: int = 900) -> dict:
    source_zip, registry, out_dir = (
        source_zip.resolve(), registry.resolve(), out_dir.resolve()
    )
    dest = [
        out_dir / "building_stock_2011.csv",
        out_dir / "building_stock_benchmarks_2011.csv",
        out_dir / "building_stock_qa.json",
    ]
    if any(path.exists() for path in dest):
        raise FileExistsError("Draft exists; use a fresh output directory")
    if any(path in (source_zip, registry) for path in dest):
        raise ValueError("Refusing to overwrite an input file")
    rows, benchmarks, qa = prepare(
        source_zip.read_bytes(), registry, min_italy=min_italy,
        min_piemonte=min_piemonte,
    )
    stock = _csv_bytes(BUILDING_COLUMNS, rows)
    summary = _csv_bytes(BENCHMARK_COLUMNS, benchmarks)
    qa = {
        **qa,
        "building_csv_sha256": hashlib.sha256(stock).hexdigest(),
        "benchmark_csv_sha256": hashlib.sha256(summary).hexdigest(),
    }
    contents = (stock, summary, (json.dumps(qa, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    out_dir.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    try:
        for path, data in zip(dest, contents):
            with path.open("xb") as output:
                output.write(data)
            created.append(path)
    except Exception:
        for path in created:
            path.unlink(missing_ok=True)
        raise
    return qa


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare draft building stock from official CPA ZIP")
    parser.add_argument("--source-zip", type=Path, required=True)
    parser.add_argument("--registry", type=Path, default=ROOT / "data/municipalities.csv")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "outputs/quality/building_stock_2011")
    args = parser.parse_args()
    report = prepare_files(args.source_zip, args.registry, args.out_dir)
    print(
        f"Technical QA: {report['coverage']}/27; "
        f"Italy {report['national_count']}; Piemonte {report['piemonte_count']}. "
        "NOT independently validated; matrix unchanged."
    )


if __name__ == "__main__":
    main()
