"""Normalize official ISTAT 2024 SDMX education data into H50's 162-row contract.

Source: census flow ``IT1,DF_DCSS_ISTR_LAV_PEN_2_TV_1,1.0`` (residents by
educational attainment). H50 needs residents aged 25-64 by attainment; ISTAT
publishes the bands ``Y25-49`` and ``Y50-64``, which are summed here into the
single ``25-64`` band accepted by ``prepare_low_education_25_64_v0_3.py``.

Fail-closed rules (no imputation):

* the metadata XML must describe the TV_1 dataflow and give the expected Italian
  labels for every education and age code used;
* every selected row must have the fixed dimensions below and no OBS_STATUS;
* any education code outside the documented exclusive set blocks the run (a
  hierarchical child such as ``IL`` or ``RDD`` would double count);
* an omitted education cell is written as 0 **only** when the published
  categories still add up to the published ``ALL`` total for that municipality
  and age band;
* ISTAT totals carry floating-point representation noise (e.g.
  ``63.99999999999999``). A value is accepted as a whole number of persons only
  within 0.000001; anything else blocks, because H50's contract is integer.

Output is a technical input, not a scientific approval. Canonical data untouched.
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
FLOW_ID = "DF_DCSS_ISTR_LAV_PEN_2_TV_1"
FLOW = f"IT1:{FLOW_ID}(1.0)"
YEAR = "2024"
STATUS = "technical_draft_do_not_publish"
AGES = ("Y25-49", "Y50-64")
AGE_LABELS = {"Y25-49": "25-49 anni", "Y50-64": "50-64 anni"}
# Exclusive ISTAT attainment codes -> H50 normalized education group.
EDU_MAP = {
    "NED": "none",
    "PSE": "primary",
    "LSE": "lower_secondary",
    "USE_IF": "upper_or_tertiary",
    "BL": "upper_or_tertiary",
    "ML_RDD": "upper_or_tertiary",
    "NRP": "unknown",
}
EDU_LABELS = {
    "NED": "nessun titolo di studio",
    "PSE": "licenza di scuola elementare",
    "LSE": "licenza di scuola media inferiore o di avviamento professionale",
    "USE_IF": "diploma di istruzione secondaria di II grado o di qualifica professionale (corso di 3-4 anni) compresi IFTS",
    "BL": "diploma di tecnico superiore ITS o titolo di studio terziario di primo livello",
    "ML_RDD": "titolo di studio terziario di secondo livello e dottorato di ricerca",
    "NRP": "non indicato",
    "ALL": "totale",
}
GROUPS = ("none", "primary", "lower_secondary", "upper_or_tertiary", "unknown")
DIMENSIONS = {"DATAFLOW": FLOW, "FREQ": "A", "INDICATOR": "RESPOP_AV", "GENDER": "T",
              "CITIZENSHIP": "TOTAL", "CUR_ACT_STAT": "99", "LOC_DEST": "ALL",
              "REAS_COMMUTING": "ALL", "TIME_PERIOD": YEAR}
FIELDS = ("municipality_code", "municipality", "reference_year", "age_band",
          "sex", "education_group", "persons")
TOLERANCE = Decimal("0.000001")
NUMBER = re.compile(r"\d+(?:\.\d+)?\Z")
NS_S = "{http://www.sdmx.org/resources/sdmxml/schemas/v2_1/structure}"
NS_C = "{http://www.sdmx.org/resources/sdmxml/schemas/v2_1/common}"
XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def clean_name(value: str) -> str:
    s = unicodedata.normalize("NFKD", value.casefold())
    return "".join(ch for ch in s if ch.isalnum() and not unicodedata.combining(ch))


def fold_label(value: str) -> str:
    return " ".join(value.casefold().split())


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


def _codelist(root: ET.Element, list_id: str) -> dict[str, tuple[str, str | None]]:
    lists = [x for x in root.iter(NS_S + "Codelist") if x.get("id") == list_id]
    if len(lists) != 1:
        raise ValueError(f"Metadata missing codelist {list_id}")
    codes = {}
    for code in lists[0].findall(NS_S + "Code"):
        names = [n.text or "" for n in code.findall(NS_C + "Name") if n.get(XML_LANG) == "it"]
        parent = code.find("./" + NS_S + "Parent/Ref")
        codes[code.get("id")] = (names[0] if names else "", parent.get("id") if parent is not None else None)
    return codes


def verify_metadata(path: Path) -> dict[str, str]:
    root = ET.parse(path).getroot()
    flows = [x for x in root.iter(NS_S + "Dataflow")
             if x.get("id") == FLOW_ID and x.get("version") == "1.0"]
    if len(flows) != 1:
        raise ValueError(f"Metadata does not describe the official {FLOW_ID} dataflow")
    education = _codelist(root, "CL_TITOLO_STUDIO")
    for code, label in EDU_LABELS.items():
        actual = education.get(code)
        if actual is None or fold_label(actual[0]) != fold_label(label):
            raise ValueError(f"Unexpected metadata label for education {code}: {actual!r}")
        if actual[1] is not None:
            raise ValueError(f"Education {code} is not a top-level category (parent {actual[1]})")
    ages = _codelist(root, "CL_ETA1")
    for code, label in AGE_LABELS.items():
        if fold_label(ages.get(code, ("", None))[0]) != fold_label(label):
            raise ValueError(f"Unexpected metadata label for age {code}: {ages.get(code)!r}")
    return {code: education[code][0] for code in EDU_LABELS} | {code: ages[code][0] for code in AGES}


def whole_persons(value: Decimal, where: str) -> int:
    nearest = value.to_integral_value()
    if abs(value - nearest) > TOLERANCE:
        raise ValueError(f"{where}: non-integer persons {value}; H50 contract is integer")
    return int(nearest)


def extract(path: Path, registry: dict[str, str]) -> tuple[list[dict[str, str]], dict]:
    cells: dict[tuple[str, str], dict[str, Decimal]] = defaultdict(dict)
    observed = 0
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames or []
        needed = set(DIMENSIONS) | {"REF_AREA", "AGE_NOCLASS", "EDU_ATTAIN", "OBS_VALUE", "OBS_STATUS"}
        if len(fields) != len(set(fields)) or not needed <= set(fields):
            raise ValueError("Original SDMX CSV schema missing/duplicated required fields")
        for i, row in enumerate(reader, 2):
            if None in row:
                raise ValueError(f"Malformed source line {i}")
            area = row["REF_AREA"].strip()
            if (area not in registry or row["TIME_PERIOD"] != YEAR or row["GENDER"] != "T"
                    or row["AGE_NOCLASS"] not in AGES):
                continue
            if any(row[k].strip() != v for k, v in DIMENSIONS.items()):
                raise ValueError(f"Unexpected SDMX dimensions on selected row {i}")
            edu = row["EDU_ATTAIN"].strip()
            if edu not in EDU_LABELS:
                raise ValueError(f"Undocumented education code {edu!r} on row {i}; mapping must be explicit")
            key = (area, row["AGE_NOCLASS"])
            if edu in cells[key]:
                raise ValueError(f"Duplicate source cell on row {i}: {key}/{edu}")
            text = row["OBS_VALUE"].strip()
            if row["OBS_STATUS"].strip() or not NUMBER.fullmatch(text):
                raise ValueError(f"Missing/flagged/non-numeric ISTAT observation on row {i}")
            cells[key][edu] = Decimal(text)
            observed += 1
    output: list[dict[str, str]] = []
    omitted: list[str] = []
    noisy_totals = 0
    max_residual = Decimal(0)
    for code, name in sorted(registry.items()):
        groups = dict.fromkeys(GROUPS, 0)
        for age in AGES:
            item = cells.get((code, age))
            if not item or "ALL" not in item:
                raise ValueError(f"Missing published total for {code}/{age}")
            details = {e: item.get(e, Decimal(0)) for e in EDU_MAP}
            residual = abs(sum(details.values(), Decimal(0)) - item["ALL"])
            if residual > TOLERANCE:
                raise ValueError(f"Education categories do not add up to ISTAT total at {code}/{age}")
            max_residual = max(max_residual, residual)
            total = whole_persons(item["ALL"], f"{code}/{age}/ALL")
            if Decimal(total) != item["ALL"]:
                noisy_totals += 1
            omitted += [f"{code}/{age}/{e}" for e in EDU_MAP if e not in item and e != "NRP"]
            band = 0
            for edu, group in EDU_MAP.items():
                persons = whole_persons(details[edu], f"{code}/{age}/{edu}")
                groups[group] += persons
                band += persons
            if band != total:
                raise ValueError(f"Integer categories do not add up to total at {code}/{age}")
        if sum(groups.values()) <= 0:
            raise ValueError(f"Zero 25-64 residents at {code}; do not impute")
        for group in GROUPS:
            output.append(dict(municipality_code=code, municipality=name, reference_year=YEAR,
                               age_band="25-64", sex="total", education_group=group,
                               persons=str(groups[group])))
        output.append(dict(municipality_code=code, municipality=name, reference_year=YEAR,
                           age_band="25-64", sex="total", education_group="total",
                           persons=str(sum(groups.values()))))
    return output, {
        "source_observations_2024_total_25_64": observed,
        "municipality_count": 27,
        "normalized_rows": len(output),
        "age_bands_summed": list(AGES),
        "omitted_education_cells_reconciled_to_zero": len(omitted),
        "omitted_education_cells": omitted,
        "totals_with_float_representation_noise": noisy_totals,
        "max_category_total_residual": format(max_residual, "f"),
        "unknown_zero_justification": "NRP (non indicato) is not published for these cells; published categories add up to ALL, so unknown=0 is an exhaustiveness inference",
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
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
    try:
        labels = verify_metadata(a.metadata_xml)
        rows, qa = extract(a.original_export, registry_names(a.registry))
    except (ValueError, ET.ParseError, csv.Error) as exc:
        p.exit(1, f"BLOCKED: {exc}\n")
    a.out_dir.mkdir(parents=True)
    normalized = a.out_dir / "education_2024_normalized.csv"
    with normalized.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    report = {"status": STATUS, "indicator_id": "H50", "year": YEAR, "dataflow": FLOW,
              "metadata_code_labels": labels,
              "category_mapping": {code: group for code, group in EDU_MAP.items()},
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
    print(f"H50: {len(rows)} rows, 27/27, {qa['omitted_education_cells_reconciled_to_zero']} omitted cells "
          f"reconciled to zero; NOT APPROVED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
