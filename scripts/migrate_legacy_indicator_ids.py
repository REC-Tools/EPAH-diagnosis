from __future__ import annotations

import csv
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MATRIX_FILE = ROOT / "data" / "verification_matrix.csv"
BACKUP_FILE = ROOT / "data" / "verification_matrix.pre_indicator_id_migration.csv"

ALIASES = {
    "dea_access_minutes": "dea_accessibility",
    "upper_secondary_access_minutes": "upper_secondary_accessibility",
    "rail_access_minutes": "rail_accessibility",
    "snai_isolation_class": "snai_classification",
}


def main() -> None:
    with MATRIX_FILE.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
        if not rows:
            raise ValueError("Verification matrix is empty.")
        fieldnames = list(rows[0].keys())

    migrated = 0
    counts: dict[tuple[str, str], int] = {}

    for row in rows:
        old_id = row["indicator_id"].strip()
        new_id = ALIASES.get(old_id)
        if new_id is None:
            continue
        row["indicator_id"] = new_id
        migrated += 1
        key = (old_id, new_id)
        counts[key] = counts.get(key, 0) + 1

    if migrated == 0:
        print("No legacy indicator IDs found. Nothing to migrate.")
        return

    # Guard against duplicate municipality/indicator pairs after migration.
    seen: set[tuple[str, str]] = set()
    duplicates: list[tuple[str, str]] = []
    for row in rows:
        key = (row["municipality"].strip(), row["indicator_id"].strip())
        if key in seen:
            duplicates.append(key)
        seen.add(key)

    if duplicates:
        preview = ", ".join(
            f"{municipality}/{indicator_id}"
            for municipality, indicator_id in duplicates[:10]
        )
        raise ValueError(
            "Migration would create duplicate municipality/indicator rows: "
            + preview
        )

    if not BACKUP_FILE.exists():
        shutil.copy2(MATRIX_FILE, BACKUP_FILE)
        print(f"Backup created: {BACKUP_FILE}")
    else:
        print(f"Backup already exists: {BACKUP_FILE}")

    with MATRIX_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Migrated {migrated} verification-matrix rows.")
    for (old_id, new_id), count in sorted(counts.items()):
        print(f"- {old_id} -> {new_id}: {count} rows")


if __name__ == "__main__":
    main()
