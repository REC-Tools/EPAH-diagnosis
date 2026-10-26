"""Safe atomic upserts for verification-matrix indicator rows."""
from __future__ import annotations

import csv
import os
import tempfile
from pathlib import Path


def upsert_indicator_rows(path: Path, indicator_id: str, updates: list[dict[str, str]]) -> None:
    """Replace precisely the supplied indicator keys, preserving all other rows."""
    with path.open(encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        fields = reader.fieldnames
        if not fields or "municipality" not in fields or "indicator_id" not in fields:
            raise ValueError("Invalid verification matrix header")
        rows = list(reader)

    def key(row: dict[str, str]) -> tuple[str, str]:
        return row["municipality"].strip().casefold(), row["indicator_id"].strip()

    originals = [key(row) for row in rows]
    if len(originals) != len(set(originals)):
        raise ValueError("Duplicate keys in verification matrix; refusing to write")

    if not updates:
        raise ValueError("No new results; refusing to write")
    update_map: dict[tuple[str, str], dict[str, str]] = {}
    for row in updates:
        identifier = key(row)
        if not identifier[0] or identifier[1] != indicator_id:
            raise ValueError(f"Invalid update key: {identifier}")
        if identifier in update_map:
            raise ValueError(f"Duplicate update key: {identifier}")
        if set(row) != set(fields):
            raise ValueError(f"Update columns differ from matrix schema: {identifier}")
        update_map[identifier] = row

    merged = [update_map.pop(key(row), row) for row in rows]
    merged.extend(update_map.values())

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="", dir=path.parent,
            prefix=f".{path.name}.", suffix=".tmp", delete=False
        ) as handle:
            tmp_path = Path(handle.name)
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(merged)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    finally:
        if tmp_path is not None and tmp_path.exists():
            tmp_path.unlink()
