"""Check immutable reviewed CSV bytes; repair exact Windows CRLF conversions.

Checksums reflect existing approved source-byte evidence, not new approvals.
--repair-crlf writes only if CRLF->LF exactly reproduces the recorded hash.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEWED_CSV_SHA256 = {
    "data/indicators/building_stock_2011.csv":
        "3e57f8ee85458d82ff8d3c9b031bb063bf9e73b86fa3d621875ba8e1765ac9d1",
    "data/indicators/building_stock_benchmarks_2011.csv":
        "5aca08da60931876c70800c8079b1ec5180f51f0225959697378b0614ac20021",
    "data/indicators/mean_altitude_2021.csv":
        "bf102e4a1828773120d4cc01e5d9f9cf07c16c2728a4cbf3aaa1144f9b3bc187",
    "data/indicators/mean_altitude_summary_2021.csv":
        "f8a5b7e59bbeda2d0a70557f6efcd333aacf16844d1ecef63da479449fc476d6",
    "data/indicators/snai_classification_2020.csv":
        "78ee6821543381a32e6ed891a90dca11e75869b6f223c887f3be932a8fdf6cd4",
    "data/indicators/snai_classification_summary_2020.csv":
        "41a3fac979ad68e74e02513683eba994519c049d7de5cab246a85a8b6f347c9f",
    "data/reference/priority_source_archive_20261029/mean_altitude_2021.csv":
        "bf102e4a1828773120d4cc01e5d9f9cf07c16c2728a4cbf3aaa1144f9b3bc187",
    "data/reference/priority_source_archive_20261029/mean_altitude_summary_2021.csv":
        "f8a5b7e59bbeda2d0a70557f6efcd333aacf16844d1ecef63da479449fc476d6",
    "data/reference/priority_source_archive_20261029/snai_classification_2020.csv":
        "78ee6821543381a32e6ed891a90dca11e75869b6f223c887f3be932a8fdf6cd4",
    "data/reference/priority_source_archive_20261029/snai_classification_summary_2020.csv":
        "41a3fac979ad68e74e02513683eba994519c049d7de5cab246a85a8b6f347c9f",
}


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _atomic_replace(path: Path, content: bytes) -> None:
    """Write in same directory and atomically replace after digest verification."""
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=".epah-csv-line-endings-", suffix=".tmp",
            dir=path.parent, delete=False,
        ) as out:
            temporary = Path(out.name)
            out.write(content)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def check_one(path: Path, expected_sha256: str, *, repair_crlf: bool = False) -> str:
    if not path.is_file():
        return "missing"
    try:
        actual = path.read_bytes()
    except OSError:
        return "unreadable"
    if digest(actual) == expected_sha256:
        return "ok"
    normalized = actual.replace(b"\r\n", b"\n")
    if normalized == actual or digest(normalized) != expected_sha256:
        return "unexpected_bytes"
    if not repair_crlf:
        return "crlf_checkout"
    try:
        _atomic_replace(path, normalized)
        return "repaired" if digest(path.read_bytes()) == expected_sha256 else "repair_failed"
    except OSError:
        return "repair_failed"


def run(root: Path, *, repair_crlf: bool = False) -> dict[str, str]:
    return {
        relative: check_one(root / relative, expected, repair_crlf=repair_crlf)
        for relative, expected in REVIEWED_CSV_SHA256.items()
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify 10 reviewed CSVs match original LF byte checksums"
    )
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument(
        "--repair-crlf", action="store_true",
        help="Restore LF only when the exact evidence SHA-256 would be recovered",
    )
    args = parser.parse_args()
    results = run(args.root, repair_crlf=args.repair_crlf)
    for path, status in results.items():
        print(f"{status}: {path}")
    if any(status not in {"ok", "repaired"} for status in results.values()):
        print("BLOCKED: source bytes differ. Do not change original QA SHA-256.")
        return 1
    print("OK: reviewed CSV byte hashes match recorded evidence.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
