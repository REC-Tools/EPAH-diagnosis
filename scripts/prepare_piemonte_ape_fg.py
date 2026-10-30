"""Prepare the Piemonte APE F+G certificate share for 27 Green Community towns.

This is the share among ALL energy certificates (all building uses), NOT
the residential housing stock and NOT the share of energy-poor households.
No canonical data, approval flags, or v0.1 files are changed.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data/downloads/regpie-Ape_comune_c_3985-all.csv"
DEFAULT_REGISTRY = ROOT / "data/municipalities.csv"
DEFAULT_OUTPUT = ROOT / "outputs/quality/piemonte_ape_fg_v02"
SOURCE_URL = ("https://www.dati.gov.it/node/view-dataset/dataset"
              "?id=63401619-1a9f-4382-8399-84c20c59dad0")
CLASSES = ("Classe_a4", "Classe_a3", "Classe_a2", "Classe_a1",
           "Classe_b", "Classe_c", "Classe_d", "Classe_e",
           "Classe_f", "Classe_g")
FIELDS = ("municipality", "istat_code", "ape_a4", "ape_a3", "ape_a2",
          "ape_a1", "ape_b", "ape_c", "ape_d", "ape_e", "ape_f",
          "ape_g", "ape_fg", "ape_total", "ape_fg_share_pct",
          "snapshot_date", "denominator", "scope")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def read_registry(path: Path) -> dict[str, str]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        entries = list(csv.DictReader(f))
    result = {}
    for r in entries:
        name, code = r["municipality"].strip(), r["istat_code"].strip()
        if not name or not re.fullmatch(r"[0-9]{6}", code) or code in result:
            raise ValueError("Invalid or duplicate registry municipality/code")
        result[code] = name
    if len(result) != 27 or len(set(result.values())) != 27:
        raise ValueError("Exactly 27 distinct Green Community municipalities required")
    return result


def prepare(input_csv: Path, registry_csv: Path) -> tuple[list[dict], dict]:
    registry = read_registry(registry_csv)
    source_hash = sha256(input_csv)
    grouped = defaultdict(list)
    total_source_rows = 0
    update_dates = set()
    with input_csv.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        required = {"Key_istat_comune", "Desc_comune",
                    "Data_aggiornamento_record", *CLASSES}
        if not reader.fieldnames or set(reader.fieldnames) != required:
            raise ValueError("Unexpected Piemonte APE CSV columns; check schema before updating")
        for line, r in enumerate(reader, 2):
            total_source_rows += 1
            key = r["Key_istat_comune"].strip()
            if not re.fullmatch(r"[0-9]{6}", key):
                raise ValueError(f"Invalid ISTAT code at source line {line}")
            if not r["Desc_comune"].strip():
                raise ValueError(f"Missing municipality name at source line {line}")
            try:
                values = [int(r[c]) for c in CLASSES]
            except (ValueError, TypeError) as exc:
                raise ValueError(f"Non-integer APE count at source line {line}") from exc
            if any(v < 0 or str(v) != str(r[c]).strip() for c, v in zip(CLASSES, values)):
                raise ValueError(f"Negative or noncanonical APE count at line {line}")
            timestamp = r["Data_aggiornamento_record"].strip()
            try:
                date = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).date().isoformat()
            except ValueError as exc:
                raise ValueError(f"Bad snapshot timestamp at source line {line}") from exc
            update_dates.add(date)
            grouped[key].append((line, r["Desc_comune"].strip(), tuple(values), date))
    if not total_source_rows:
        raise ValueError("Empty source file")
    missing = set(registry) - set(grouped)
    if missing:
        raise ValueError("Missing Green Community codes: " + ", ".join(sorted(missing)))
    if len(update_dates) != 1:
        raise ValueError("Mixed snapshot dates in source: " + str(sorted(update_dates)))
    dup_extras = []
    for key, entries in grouped.items():
        if len(entries) > 1:
            if key in registry:
                raise ValueError(f"Duplicate selected municipality code: {key}")
            if len({e[2:] for e in entries}) != 1:
                raise ValueError(f"Inconsistent duplicate records outside study: {key}")
            dup_extras.append({"istat_code": key, "names": sorted({e[1] for e in entries}),
                               "source_rows": [e[0] for e in entries]})
    result = []
    for code, name in sorted(registry.items(), key=lambda item: item[1]):
        _, source_name, values, snapshot = grouped[code][0]
        total = sum(values)
        if total <= 0:
            raise ValueError(f"No APE in selected municipality {name}: {code}")
        fg = values[8] + values[9]
        result.append({
            "municipality": name, "istat_code": code,
            **{c.lower().replace("classe_", "ape_"): n for c, n in zip(CLASSES, values)},
            "ape_fg": fg, "ape_total": total,
            "ape_fg_share_pct": f"{100 * fg / total:.2f}",
            "snapshot_date": snapshot, "denominator": "all_ape",
            "scope": "all_building_uses_not_residential_only",
        })
    count = sum(r["ape_total"] for r in result)
    fg_count = sum(r["ape_fg"] for r in result)
    report = {
        "indicator_id": "ape_fg_share_all_uses",
        "qa_status": "technical_extraction_only",
        "validated_as_residential_share": False,
        "source_url": SOURCE_URL,
        "source_license": "CC BY 4.0",
        "source_csv_sha256": source_hash,
        "municipality_registry_sha256": sha256(registry_csv),
        "snapshot_date": next(iter(update_dates)),
        "source_rows": total_source_rows,
        "source_unique_codes": len(grouped),
        "duplicate_codes_outside_study": dup_extras,
        "municipalities_expected": 27, "municipalities_matched": len(result),
        "ape_count_27": count, "ape_fg_count_27": fg_count,
        "pooled_fg_share_pct": round(100 * fg_count / count, 2),
        "meaning": "APE certificates class F+G / all APE certificates recorded in each municipality",
        "limitations": [
            "Source does not distinguish residential vs non-residential properties.",
            "APE counts are neither all housing units nor unique buildings/households.",
            "The update date of the aggregate is not the issuance date of each APE.",
            "Small municipality certificate denominators may yield unstable shares.",
            "The aggregated percent pools certificates; not a mean of 27 percentages.",
        ],
    }
    return result, report


def main() -> None:
    p = argparse.ArgumentParser(description="Prepare Regione Piemonte APE F/G share, 27 municipality pilot")
    p.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    p.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUTPUT)
    a = p.parse_args()
    if a.out_dir.exists():
        raise FileExistsError("Use a fresh --out-dir; do not overwrite prior source evidence")
    rows, report = prepare(a.input, a.registry)
    a.out_dir.mkdir(parents=True, exist_ok=False)
    csv_path = a.out_dir / "ape_fg_27_municipalities.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    report["result_csv_sha256"] = sha256(csv_path)
    (a.out_dir / "ape_fg_qa.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Piemonte APE {report['snapshot_date']}: "
          f"{report['municipalities_matched']}/27 municipalities")
    print(f"Certificates: {report['ape_count_27']}; F+G: "
          f"{report['ape_fg_count_27']} ({report['pooled_fg_share_pct']:.2f}%)")
    print(f"Duplicate codes outside study: {len(report['duplicate_codes_outside_study'])}")
    print("STATUS: technical extraction. All-use certificates, NOT residential housing share.")
    print(f"Output: {a.out_dir}")


if __name__ == "__main__":
    main()
