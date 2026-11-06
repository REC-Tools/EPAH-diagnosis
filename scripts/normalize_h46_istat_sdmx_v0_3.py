"""Normalize official 2024 ISTAT SDMX municipal work status into H46's 162-row contract.

Strict source/metadata-only intake; never updates canonical releases. No imputation
except explicit unknown=0 after independently published 22+23=99 reconcile.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import unicodedata
import xml.etree.ElementTree as ET
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data/municipalities.csv"
FLOW = "IT1:DF_DCSS_ISTR_LAV_PEN_2_TV_3(1.0)"
YEAR = "2024"
REQUIRED_CODES = {"1", "12", "22", "23", "24", "4", "5", "7", "99"}
CODE_MAP = (("employed", "1"), ("unemployed", "12"), ("inactive", "23"),
            ("unknown", None), ("labour_force", "22"), ("population_total", "99"))
DIMENSIONS = {"DATAFLOW": FLOW, "FREQ": "A", "INDICATOR": "RESPOP_AV",
              "GENDER": "T", "AGE_NOCLASS": "Y_GE15", "CITIZENSHIP": "TOTAL",
              "EDU_ATTAIN": "ALL", "LOC_DEST": "ALL", "REAS_COMMUTING": "ALL",
              "TIME_PERIOD": YEAR}
TOLERANCE = Decimal("0.000001")
FIELDS = ("municipality_code", "municipality", "reference_year", "age_universe",
          "sex", "labour_status", "persons")
STATUS = "technical_draft_do_not_publish"
NUMBER = re.compile(r"\d+(?:\.\d+)?\Z")
NS_S = "{http://www.sdmx.org/resources/sdmxml/schemas/v2_1/structure}"
NS_C = "{http://www.sdmx.org/resources/sdmxml/schemas/v2_1/common}"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def clean_name(value: str) -> str:
    s = unicodedata.normalize("NFKD", value.casefold())
    return "".join(ch for ch in s if ch.isalnum() and not unicodedata.combining(ch))


def registry_names(path: Path) -> dict[str, str]:
    result = {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not {"municipality", "istat_code"} <= set(reader.fieldnames or ()):
            raise ValueError("Invalid municipality registry columns")
        for row in reader:
            code, name = row["istat_code"].strip(), row["municipality"].strip()
            if not re.fullmatch(r"\d{6}", code) or not name or code in result:
                raise ValueError("Invalid/duplicate municipality registry")
            result[code] = name
    if len(result) != 27 or len({clean_name(n) for n in result.values()}) != 27:
        raise ValueError("Registry must contain 27 unique municipalities")
    return result


def verify_metadata(path: Path) -> dict[str, str]:
    root = ET.parse(path).getroot()
    flows = [x for x in root.iter(NS_S + "Dataflow")
             if x.get("id") == "DF_DCSS_ISTR_LAV_PEN_2_TV_3" and x.get("version") == "1.0"]
    if len(flows) != 1:
        raise ValueError("Metadata missing expected official 2024 census dataflow")
    lists = [x for x in root.iter(NS_S + "Codelist") if x.get("id") == "CL_FORZE_LAV"]
    if len(lists) != 1:
        raise ValueError("Metadata missing CL_FORZE_LAV hierarchy")
    codes = {}
    for x in lists[0].findall(NS_S + "Code"):
        names = [n.text or "" for n in x.findall(NS_C + "Name")
                 if n.get("{http://www.w3.org/XML/1998/namespace}lang") == "it"]
        parent = x.find("./" + NS_S + "Parent/Ref")
        codes[x.get("id")] = (names[0] if names else "", parent.get("id") if parent is not None else None)
    expected = {"1": ("occupato", "22"), "12": ("in cerca di occupazione", "22"),
                "22": ("forze di lavoro", None), "23": ("non forze di lavoro", None),
                "99": ("totale", None)}
    for code, value in expected.items():
        if codes.get(code) != value:
            raise ValueError(f"Unexpected metadata classification for status {code}: {codes.get(code)!r}")
    for code in ("24", "4", "5", "7"):
        if code not in codes or codes[code][1] != "23":
            raise ValueError(f"Metadata subgroup {code} must be under non-forces 23")
    return {code: codes[code][0] for code in sorted(REQUIRED_CODES)}


def extract(path: Path, registry: dict[str, str]) -> tuple[list[dict[str, str]], dict]:
    groups: dict[str, dict[str, Decimal]] = defaultdict(dict)
    observed = 0
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames or []
        if len(fields) != len(set(fields)) or not set(DIMENSIONS) | {"REF_AREA", "CUR_ACT_STAT", "OBS_VALUE", "OBS_STATUS"} <= set(fields):
            raise ValueError("Original SDMX CSV schema missing/duplicated required fields")
        for i, row in enumerate(reader, 2):
            if None in row:
                raise ValueError(f"Malformed source line {i}")
            code = row["REF_AREA"].strip()
            if code not in registry or row["TIME_PERIOD"] != YEAR or row["AGE_NOCLASS"] != "Y_GE15" or row["GENDER"] != "T":
                continue
            if any(row[k].strip() != v for k, v in DIMENSIONS.items()):
                raise ValueError(f"Unexpected SDMX dimensions on selected row {i}")
            cat = row["CUR_ACT_STAT"].strip()
            if cat not in REQUIRED_CODES or cat in groups[code]:
                raise ValueError(f"Unknown/duplicate work status on source row {i}: {code}/{cat}")
            if row["OBS_STATUS"].strip() or not NUMBER.fullmatch(row["OBS_VALUE"].strip()):
                raise ValueError(f"Missing/flagged/non-decimal ISTAT observation on row {i}")
            groups[code][cat] = Decimal(row["OBS_VALUE"].strip())
            observed += 1
    if observed != 27 * len(REQUIRED_CODES) or set(groups) != set(registry):
        raise ValueError(f"H46 source coverage not 27 x 9: {observed} source observations")
    output = []
    max_force = max_population = max_inactive_detail = Decimal(0)
    for code, name in sorted(registry.items()):
        item = groups[code]
        if set(item) != REQUIRED_CODES or item["22"] <= 0 or item["99"] <= 0:
            raise ValueError(f"Missing work categories or zero denominator at {code}")
        force = abs(item["1"] + item["12"] - item["22"])
        population = abs(item["22"] + item["23"] - item["99"])
        inactive = abs(sum((item[k] for k in ("24", "4", "5", "7")), Decimal(0)) - item["23"])
        if max(force, population, inactive) > TOLERANCE:
            raise ValueError(f"Unreconciled official work totals at {code}")
        max_force = max(max_force, force)
        max_population = max(max_population, population)
        max_inactive_detail = max(max_inactive_detail, inactive)
        for status, raw_code in CODE_MAP:
            value = "0" if raw_code is None else format(item[raw_code], "f")
            output.append(dict(municipality_code=code, municipality=name,
                               reference_year=YEAR, age_universe="15_plus", sex="total",
                               labour_status=status, persons=value))
    return output, {"source_observations_2024_total_15_plus": observed,
                    "municipality_count": 27, "normalized_rows": len(output),
                    "max_force_residual": format(max_force, "f"),
                    "max_population_residual": format(max_population, "f"),
                    "max_inactive_subgroup_residual": format(max_inactive_detail, "f"),
                    "unknown_zero_justification": "Official 22 + 23 = 99 in every municipality; zero is an exhaustiveness inference, not an observed category"}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--original-export", type=Path, required=True)
    p.add_argument("--metadata-xml", type=Path, required=True)
    p.add_argument("--registry", type=Path, default=REGISTRY)
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--expected-original-sha256")
    a = p.parse_args(argv)
    if a.out_dir.exists():
        p.error("Output directory exists; preserve previous QA evidence")
    for file in (a.original_export, a.metadata_xml, a.registry):
        if not file.is_file():
            p.error(f"Missing input: {file}")
    source_hash = digest(a.original_export)
    if a.expected_original_sha256 and source_hash != a.expected_original_sha256.lower():
        p.error("Original SHA-256 mismatch")
    code_labels = verify_metadata(a.metadata_xml)
    rows, qa = extract(a.original_export, registry_names(a.registry))
    a.out_dir.mkdir(parents=True)
    normalized = a.out_dir / "labour_2024_normalized.csv"
    with normalized.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    report = {"status": STATUS, "indicator_id": "H46", "year": YEAR,
              "dataflow": FLOW, "metadata_code_labels": code_labels,
              "source_category_mapping_documented": True,
              "scientific_approval": False, "independent_reproduction_verified": False,
              "qa": qa}
    qa_path = a.out_dir / "normalization_qa.json"
    qa_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest = {"status": STATUS, "original_export_sha256": source_hash,
                "metadata_xml_sha256": digest(a.metadata_xml),
                "municipality_registry_sha256": digest(a.registry),
                "normalized_csv_sha256": digest(normalized),
                "normalization_qa_sha256": digest(qa_path),
                "scientific_approval": False, "canonical_data_modified": False}
    (a.out_dir / "normalization_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("H46: 162 rows, 27/27, original Decimal estimates preserved; NOT APPROVED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
