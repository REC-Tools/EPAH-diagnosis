"""Technical intake of Piemonte CIT GROUP-THERMIC aggregated source CSVs.

No data are included here: the two original regional CSVs must be obtained
and checked locally. One generator group is NOT one house/household.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data/municipalities.csv"
SOURCE_FUEL = "https://www.dati.gov.it/node/view-dataset/dataset?id=80540d5b-72af-4c45-901b-eb4a4f7ae9cf"
SOURCE_AGE = "https://www.dati.gov.it/node/view-dataset/dataset?id=d34fb6c0-6ae3-4ff6-9915-387d21606807"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for buf in iter(lambda: f.read(1024 * 1024), b""):
            h.update(buf)
    return h.hexdigest()


def norm(value: object) -> str:
    val = unicodedata.normalize("NFKD", str(value or "")).casefold()
    return re.sub(r"[^a-z0-9]", "", "".join(c for c in val if not unicodedata.combining(c)))


def read_registry(path: Path) -> dict[str, str]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    result = {}
    for r in rows:
        code, name = r["istat_code"].strip(), r["municipality"].strip()
        if not re.fullmatch(r"\d{6}", code) or not name or code in result:
            raise ValueError("Invalid/duplicate municipality registry")
        result[code] = name
    if len(result) != 27 or len(set(result.values())) != 27:
        raise ValueError("Registry requires exactly 27 municipalities")
    return result


ALIASES = {
    "code": ("Key_istat_comune", "Codice_istat_comune", "Codice_comune", "Cod_istat_comune",
             "Cod_comune", "Pro_com_t", "Procom", "Codice ISTAT", "Codice comune ISTAT"),
    "category_fuel": ("Combustibile", "Desc_combustibile", "Tipo_combustibile",
                      "Descrizione_combustibile", "Tipo combustibile", "Fuel"),
    "category_age": ("Data_installazione", "Anno_installazione", "Anno installazione",
                     "Data installazione", "Installation year", "Anno_inst"),
    "count": ("Numero", "Conteggio", "Num_gt", "Num_gruppi_termici", "N_gruppi_termici",
              "Numero_gruppi", "Numero gruppi termici", "Totale", "Count"),
}


def read_long_csv(path: Path, mode: str, *, code_col: str | None = None,
                  category_col: str | None = None, count_col: str | None = None
                  ) -> tuple[list[dict], dict]:
    # Accept common source exports but never reinterpret unknown schemas.
    if mode not in {"fuel", "age"}:
        raise ValueError("mode must be fuel or age")
    with path.open(encoding="utf-8-sig", newline="") as stream:
        sample = stream.read(8096)
        stream.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=";,\t")
        except csv.Error as exc:
            raise ValueError("Unable to detect CIT CSV delimiter") from exc
        reader = csv.DictReader(stream, dialect=dialect)
        names = reader.fieldnames or []
        if not names or len(names) != len(set(names)):
            raise ValueError("Invalid/duplicate CIT CSV column headers")
        def resolve(override, aliases):
            if override:
                if override not in names:
                    raise ValueError(f"CIT column not found: {override}; columns: {names}")
                return override
            lookup = {norm(name): name for name in names}
            found = [lookup[norm(a)] for a in aliases if norm(a) in lookup]
            if len(set(found)) != 1:
                raise ValueError(f"Cannot identify CIT column unambiguously: {aliases}. "
                                 f"Found: {names}. Use explicit --*-col options.")
            return found[0]
        field_code = resolve(code_col, ALIASES["code"])
        field_category = resolve(category_col, ALIASES["category_"+mode])
        field_count = resolve(count_col, ALIASES["count"])
        if len({field_code, field_category, field_count}) != 3:
            raise ValueError("Code/category/count cannot share columns")
        parsed = []
        for line, row in enumerate(reader, 2):
            raw = str(row.get(field_code) or "").strip()
            if not raw:
                continue
            if not raw.isdigit() or len(raw) > 6:
                raise ValueError(f"Invalid municipality code at CIT row {line}")
            code = raw.zfill(6)
            label = str(row.get(field_category) or "").strip()
            if not label:
                label = "Non dichiarato"
            count_str = str(row.get(field_count) or "").strip()
            if not re.fullmatch(r"\d+", count_str):
                raise ValueError(f"Invalid/negative/ambiguous CIT count row {line}: {count_str!r}")
            parsed.append({"istat_code": code, "category": label,
                           "count": int(count_str), "source_line": line})
    if not parsed:
        raise ValueError("CIT source has no numeric rows")
    return parsed, {"fields": {"code": field_code, "category": field_category,
                              "count": field_count},
                    "source_rows_parsed": len(parsed)}


def fuel_category(label: str) -> str:
    key = norm(label)
    if key in {"gasnaturale", "metano", "gasmetano"}:
        return "natural_gas"
    if key in {"gasolio", "diesel"}:
        return "diesel"
    if key in {"gpl", "gaspetrolioliquefatto", "gasliquefatto"}:
        return "lpg"
    if key in {"legna", "pellet", "biomassa", "cippato", "carbone", "combustibilesolido"}:
        return "solid_fuels"
    if key in {"energiaelettrica", "elettricita", "elettrico"}:
        return "electricity"
    if key in {"oliocombustibile", "olio"}:
        return "fuel_oil"
    if key in {"altro", "altri", "altricombustibili"}:
        return "other"
    return "unclassified"


def installation_year(label: str) -> int | None:
    text = label.strip()
    if norm(text) in {"nondichiarato", "nonspecificato", "sconosciuto", "nd", "nan"}:
        return None
    if re.fullmatch(r"\d{4}", text):
        year = int(text)
    elif re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        year = date.fromisoformat(text).year
    elif re.fullmatch(r"\d{2}/\d{2}/\d{4}", text):
        year = datetime.strptime(text, "%d/%m/%Y").year
    else:
        # 1990-2000 and "before 2010" are bins, not precise installation years:
        # refusing to infer an unknown amount of old generators from the bin.
        raise ValueError(f"Ambiguous installation date/category: {text!r}")
    if not 1900 <= year <= 2100:
        raise ValueError("Invalid installation year")
    return year


def prepare(input_file: Path, registry_file: Path, mode: str, snapshot: str,
            *, code_col: str | None = None,
            category_col: str | None = None,
            count_col: str | None = None, older_years: int = 20
            ) -> tuple[list[dict], dict]:
    # Snapshot is supplied/documented by the operator, not invented from
    # outdated catalogue metadata or treated as the per-group install year.
    try:
        as_of = date.fromisoformat(snapshot)
    except ValueError as exc:
        raise ValueError("Supply a real --snapshot-date YYYY-MM-DD") from exc
    if not 1 <= older_years <= 100:
        raise ValueError("older_years must be 1..100")
    registry = read_registry(registry_file)
    observations, meta = read_long_csv(input_file, mode, code_col=code_col,
                                        category_col=category_col, count_col=count_col)
    grouped = defaultdict(Counter)
    unknown = defaultdict(Counter)
    for obs in observations:
        code = obs["istat_code"]
        if code not in registry:
            continue
        count = obs["count"]
        if mode == "fuel":
            key = fuel_category(obs["category"])
            if key == "unclassified":
                unknown[code][obs["category"]] += count
            grouped[code][key] += count
        else:
            year = installation_year(obs["category"])
            if year is not None and year > as_of.year:
                raise ValueError(f"Installation year is after snapshot in {registry[code]}")
            bucket = ("unknown_year" if year is None else
                      "aged_20_or_more" if year <= as_of.year - older_years else
                      "younger_than_threshold")
            grouped[code][bucket] += count
    output = []
    missing = []
    for code, name in sorted(registry.items(), key=lambda pair: pair[1]):
        categories = grouped.get(code, Counter())
        total = sum(categories.values())
        if total == 0:
            missing.append({"istat_code": code, "municipality": name})
        if mode == "fuel":
            in_scope = sum(v for k, v in categories.items() if k != "unclassified")
            numerator = categories["diesel"] + categories["lpg"]
            share = (100 * numerator / in_scope) if in_scope else None
            row = {"municipality": name, "istat_code": code,
                   "generator_groups_total": total,
                   "classified_groups": in_scope,
                   "unclassified_groups": categories["unclassified"],
                   "natural_gas_groups": categories["natural_gas"],
                   "diesel_groups": categories["diesel"],
                   "lpg_groups": categories["lpg"],
                   "solid_fuels_groups": categories["solid_fuels"],
                   "electricity_groups": categories["electricity"],
                   "other_groups": categories["other"] + categories["fuel_oil"],
                   "diesel_lpg_share_pct": f"{share:.2f}" if share is not None else "",
                   "denominator": "classified_generator_groups",
                   "snapshot_date": snapshot}
        else:
            in_scope = total - categories["unknown_year"]
            numerator = categories["aged_20_or_more"]
            share = (100 * numerator / in_scope) if in_scope else None
            row = {"municipality": name, "istat_code": code,
                   "generator_groups_total": total, "groups_with_known_year": in_scope,
                   "groups_with_unknown_year": categories["unknown_year"],
                   "groups_aged_20_or_more": numerator,
                   "older_generator_share_pct": f"{share:.2f}" if share is not None else "",
                   "denominator": "generator_groups_with_known_installation_year",
                   "snapshot_date": snapshot}
        output.append(row)
    report = {
        "indicator_id": ("cit_diesel_lpg_generator_share" if mode == "fuel" else "cit_older_generator_share"),
        "qa_status": ("technical_extraction_only" if len(missing) == 0
                      else "technical_incomplete_do_not_publish"),
        "validated_for_release": False,
        "source_csv_sha256": sha256(input_file), "registry_csv_sha256": sha256(registry_file),
        "source_url": SOURCE_FUEL if mode == "fuel" else SOURCE_AGE,
        "licence_catalogue": "CC BY 4.0 (check on downloaded resource)",
        "snapshot_date_operator_reported": snapshot,
        "source_schema": meta, "municipalities_expected": 27,
        "municipalities_with_generator_data": 27 - len(missing),
        "missing": missing,
        "unclassified_fuel_labels": {registry[k]: dict(v) for k, v in unknown.items()},
        "older_years_threshold": older_years if mode == "age" else None,
        "meaning": ("gasolio+GPL groups / groups with recognized fuel, NOT homes"
                    if mode == "fuel" else
                    "groups aged >=20 years / groups with known install year, NOT households"),
        "limitations": [
            "One registered generator group is not one heated dwelling or one household.",
            "Category mapping excludes unclassified fuels from the denominator.",
            "Snapshot date is asserted by the local operator; verify source metadata.",
            "A fuel or age threshold is not direct evidence of energy poverty.",
            "Generator records may have incomplete/outdated registration.",
        ],
    }
    return output, report


def main() -> None:
    p = argparse.ArgumentParser(description="Regione Piemonte CIT grouped-generator indicators")
    p.add_argument("--mode", choices=["fuel","age"], required=True)
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--registry", type=Path, default=REGISTRY)
    p.add_argument("--snapshot-date", required=True, help="Actual source snapshot YYYY-MM-DD")
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--code-col")
    p.add_argument("--category-col")
    p.add_argument("--count-col")
    p.add_argument("--older-years", type=int, default=20)
    p.add_argument("--strict", action="store_true")
    a = p.parse_args()
    if a.out_dir.exists():
        raise FileExistsError("Preserve previous evidence; choose a fresh output folder")
    rows, qa = prepare(a.input, a.registry, a.mode, a.snapshot_date,
                       code_col=a.code_col, category_col=a.category_col,
                       count_col=a.count_col, older_years=a.older_years)
    if a.strict and (qa["missing"] or (a.mode=="fuel" and qa["unclassified_fuel_labels"])):
        raise ValueError("Strict QA blocked: missing municipalities or unclassified fuel labels")
    a.out_dir.mkdir(parents=True)
    filename = "cit_fuel_27.csv" if a.mode == "fuel" else "cit_generator_age_27.csv"
    file = a.out_dir / filename
    with file.open("w", encoding="utf-8", newline="") as handle:
        w = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    qa["output_csv_sha256"] = sha256(file)
    (a.out_dir / "cit_qa.json").write_text(json.dumps(qa, ensure_ascii=False, indent=2)+"\n",
                                           encoding="utf-8")
    print(a.mode.upper(), qa["qa_status"],
          f"{qa['municipalities_with_generator_data']}/27 towns",
          "source snapshot:", a.snapshot_date)
    print("Source/schema:", qa["source_schema"])
    print("No canonical matrix modified; counts measure groups, NOT families.")
    print("Output:", a.out_dir)


if __name__ == "__main__":
    main()
