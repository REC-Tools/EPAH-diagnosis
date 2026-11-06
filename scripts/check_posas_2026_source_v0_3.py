"""Offline original-archive preflight for ISTAT POSAS 2026 (not data approval).

This checker observes source file bytes, ZIP layout, CSV header and reference year.
It never changes the canonical data matrix or performs network requests.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

EXPECTED_YEAR = "2026"
EXPECTED_URL = "https://demo.istat.it/data/posas/POSAS_2026_it_Comuni.zip"
MAX_ZIP_BYTES = 100 * 1024 * 1024
MAX_MEMBER_BYTES = 600 * 1024 * 1024
STATUS = "technical_draft_do_not_publish"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def check_source(path: Path, *, member: str | None = None) -> dict[str, object]:
    if not path.is_file() or not path.stat().st_size:
        raise ValueError("Source ZIP missing or empty")
    if path.stat().st_size > MAX_ZIP_BYTES:
        raise ValueError("Source ZIP exceeds safety size limit")
    if not zipfile.is_zipfile(path):
        raise ValueError("Official source is not a ZIP archive")

    with zipfile.ZipFile(path) as archive:
        members = sorted(i.filename for i in archive.infolist()
                         if i.filename.lower().endswith(".csv") and not i.is_dir())
        if not members:
            raise ValueError("No CSV member in POSAS source archive")
        if member is None:
            if len(members) != 1:
                raise ValueError("Multiple CSV members: use --member to select source explicitly")
            member = members[0]
        if member not in members:
            raise ValueError(f"Selected CSV member not found: {member!r}")
        info = archive.getinfo(member)
        if info.file_size == 0 or info.file_size > MAX_MEMBER_BYTES:
            raise ValueError("CSV member has an invalid declared size")
        original = archive.read(member)
    try:
        text = original.decode("utf-8-sig")
        encoding = "utf-8-sig"
    except UnicodeDecodeError:
        text = original.decode("latin-1")
        encoding = "latin-1"

    lines = text.splitlines(keepends=True)
    header_position = None
    columns: list[str] = []
    for index, line in enumerate(lines[:50]):
        for delimiter in (";", ",", "\t"):
            candidate = next(csv.reader([line], delimiter=delimiter), [])
            names = [cell.strip().casefold() for cell in candidate]
            if (len(names) >= 4 and any("comune" in x for x in names)
                    and any(x in {"eta", "età"} for x in names)
                    and any(x in {"totale", "tot", "tot_p"} for x in names)):
                header_position = index
                columns = candidate
                break
        if header_position is not None:
            break
    if header_position is None:
        raise ValueError("Could not verify POSAS CSV header (Comune, Età, Totale)")
    title_lines = [line.strip() for line in lines[:header_position] if line.strip()]
    if not title_lines or not any(re.search(r"(?<!\d)2026(?!\d)", line) for line in title_lines):
        raise ValueError("The POSAS preamble does not explicitly confirm reference year 2026")

    return {
        "status": STATUS,
        "source_url_expected": EXPECTED_URL,
        "file_origin_independently_authenticated": False,
        "header_2026_observed": True,
        "reference_date_proposed": "2026-01-01",
        "original_zip_filename": path.name,
        "original_zip_bytes": path.stat().st_size,
        "original_zip_sha256": sha256_file(path),
        "csv_member": member,
        "csv_member_bytes": len(original),
        "csv_member_sha256": hashlib.sha256(original).hexdigest(),
        "csv_encoding": encoding,
        "csv_columns": columns,
        "preamble": title_lines[:5],
        "checked_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "scientific_approval": False,
        "publication_allowed": False,
        "note": "Source bytes and title inspected; manual license, year and source review required.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-zip", required=True, type=Path)
    parser.add_argument("--out-file", required=True, type=Path, help="New QA JSON; cannot overwrite")
    parser.add_argument("--member", help="CSV member if ZIP contains more than one")
    args = parser.parse_args(argv)
    try:
        if args.out_file.exists():
            raise FileExistsError(f"Preserve previous QA evidence: {args.out_file}")
        report = check_source(args.source_zip, member=args.member)
        # Keep script non-destructive; file and its parent must be supplied.
        if not args.out_file.parent.is_dir():
            raise FileNotFoundError("QA output parent must exist")
        args.out_file.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 1
    print(f"Source preflight passed for {report['csv_member']}; no scientific approval.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
