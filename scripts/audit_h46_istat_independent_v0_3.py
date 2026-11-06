"""Independent byte-source H46 audit: does not import the normalizer or H46 builder.

Read all source records again; reconstruct 27 x 6 normalized observations,
validate published census sex/age totals and optionally validate H46 preview.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

FLOW = "IT1:DF_DCSS_ISTR_LAV_PEN_2_TV_3(1.0)"
REQUIRED = {"1", "12", "22", "23", "24", "4", "5", "7", "99"}
MAP = {"employed": "1", "unemployed": "12", "inactive": "23",
       "labour_force": "22", "population_total": "99"}
AGES = ("Y15-24", "Y25-49", "Y50-64", "Y_GE65")
DIM = {"DATAFLOW": FLOW, "FREQ": "A", "INDICATOR": "RESPOP_AV",
       "CITIZENSHIP": "TOTAL", "EDU_ATTAIN": "ALL", "LOC_DEST": "ALL",
       "REAS_COMMUTING": "ALL", "TIME_PERIOD": "2024"}
TOL = Decimal("0.000001")
NUM = re.compile(r"\d+(?:\.\d+)?\Z")
STATUS = "technical_draft_do_not_publish"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def load_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        d = csv.DictReader(f)
        if not d.fieldnames or len(set(d.fieldnames)) != len(d.fieldnames):
            raise ValueError(f"Duplicate or missing header: {path}")
        rows = list(d)
    if any(None in row for row in rows):
        raise ValueError(f"Malformed CSV: {path}")
    return rows


def census_rows(path: Path, municipality_codes: set[str]) -> dict:
    records = {}
    for row in load_csv(path):
        if row.get("REF_AREA") not in municipality_codes or row.get("TIME_PERIOD") != "2024":
            continue
        if row.get("GENDER") not in ("F", "M", "T") or row.get("AGE_NOCLASS") not in (*AGES, "Y_GE15"):
            continue
        if any(row.get(k) != v for k, v in DIM.items()):
            raise ValueError("Incompatible source dimensions for selected census records")
        key = (row["REF_AREA"], row["GENDER"], row["AGE_NOCLASS"], row["CUR_ACT_STAT"])
        raw = row.get("OBS_VALUE", "").strip()
        if (key in records or key[-1] not in REQUIRED or row.get("OBS_STATUS", "").strip()
                or not NUM.fullmatch(raw)):
            raise ValueError(f"Duplicated, flagged or invalid ISTAT record: {key}")
        records[key] = Decimal(raw)
    return records


def meta_check(path: Path) -> None:
    root = ET.parse(path).getroot()
    s = "{http://www.sdmx.org/resources/sdmxml/schemas/v2_1/structure}"
    c = "{http://www.sdmx.org/resources/sdmxml/schemas/v2_1/common}"
    if len([x for x in root.iter(s + "Dataflow") if x.get("id") == "DF_DCSS_ISTR_LAV_PEN_2_TV_3"]) != 1:
        raise ValueError("Wrong ISTAT dataflow in metadata")
    lists = [x for x in root.iter(s + "Codelist") if x.get("id") == "CL_FORZE_LAV"]
    if len(lists) != 1:
        raise ValueError("Missing ISTAT codebook")
    codes = {}
    for element in lists[0].findall(s + "Code"):
        parent = element.find("./" + s + "Parent/Ref")
        names = [v.text for v in element.findall(c + "Name") if v.get("{http://www.w3.org/XML/1998/namespace}lang") == "it"]
        codes[element.get("id")] = (names[0] if names else "", parent.get("id") if parent is not None else None)
    for code, name, parent in [("1", "occupato", "22"), ("12", "in cerca di occupazione", "22"),
                                ("22", "forze di lavoro", None), ("23", "non forze di lavoro", None),
                                ("99", "totale", None)]:
        if codes.get(code) != (name, parent):
            raise ValueError(f"Changed ISTAT metadata for {code}")
    if any(codes.get(c, (None, None))[1] != "23" for c in ("24", "4", "5", "7")):
        raise ValueError("Inconsistent inactive subgroup metadata")


def audit(source: Path, metadata: Path, normalized: Path, manifest: Path,
          registry: Path, preview: Path | None = None) -> dict:
    meta_check(metadata)
    registry_rows = load_csv(registry)
    municipalities = {r["istat_code"]: r["municipality"] for r in registry_rows}
    if len(municipalities) != 27 or len(registry_rows) != 27:
        raise ValueError("Municipality register not 27 unique codes")
    source_values = census_rows(source, set(municipalities))
    required = {(code, "T", "Y_GE15", status) for code in municipalities for status in REQUIRED}
    if not required <= set(source_values):
        raise ValueError(f"Source missing {len(required - set(source_values))} required 15+ total cells")
    ref = {"employed": "1", "unemployed": "12", "labour_force": "22",
           "inactive": "23", "population_total": "99"}
    norm_rows = load_csv(normalized)
    record_index = {}
    for row in norm_rows:
        code = row.get("municipality_code")
        status = row.get("labour_status")
        key = (code, status)
        if (code not in municipalities or status not in (*ref, "unknown") or key in record_index
                or row.get("municipality") != municipalities[code] or row.get("reference_year") != "2024"
                or row.get("age_universe") != "15_plus" or row.get("sex") != "total"):
            raise ValueError(f"Malformed normalized row: {key}")
        if not NUM.fullmatch(row.get("persons", "")):
            raise ValueError(f"Nondecimal normalized count: {key}")
        record_index[key] = Decimal(row["persons"])
    if len(norm_rows) != 162 or len(record_index) != 162:
        raise ValueError("Expected exact 27 x 6 normalized matrix")
    maximum_sex = maximum_age = maximum_force = maximum_population = maximum_subtotal = Decimal(0)
    omitted_zero_age_cells = 0
    expected = {}
    weighted_unemployed = weighted_force = Decimal(0)
    for code in sorted(municipalities):
        raw = {s: source_values[code, "T", "Y_GE15", s] for s in REQUIRED}
        f = abs(raw["1"] + raw["12"] - raw["22"])
        p = abs(raw["22"] + raw["23"] - raw["99"])
        i = abs(raw["24"] + raw["4"] + raw["5"] + raw["7"] - raw["23"])
        if max(f, p, i) > TOL or raw["22"] <= 0:
            raise ValueError(f"Source status hierarchy not reconciled: {code}")
        maximum_force, maximum_population, maximum_subtotal = max(maximum_force, f), max(maximum_population, p), max(maximum_subtotal, i)
        for category, code_sdmx in ref.items():
            if record_index[code, category] != raw[code_sdmx]:
                raise ValueError(f"Original vs normalized mismatch: {code}/{category}")
        if record_index[code, "unknown"] != 0:
            raise ValueError(f"Unknown not supported by ISTAT hierarchy: {code}")
        # Every published 15+ total must reconcile with males/females and four
        # mutually exclusive age groups. Omitted age cells may only denote zero
        # after the *total* reconciles; never impute missing source total cells.
        for status in REQUIRED:
            sex_values = [(code, x, "Y_GE15", status) for x in ("F", "M")]
            if not all(k in source_values for k in sex_values):
                raise ValueError(f"Missing published gender total: {code}/{status}")
            s_err = abs(sum((source_values[k] for k in sex_values), Decimal(0)) - raw[status])
            age_keys = [(code, "T", age, status) for age in AGES]
            omitted_zero_age_cells += sum(k not in source_values for k in age_keys)
            a_err = abs(sum((source_values[k] for k in age_keys if k in source_values), Decimal(0)) - raw[status])
            if max(s_err, a_err) > TOL:
                raise ValueError(f"Age/sex source census not reconciled: {code}/{status}")
            maximum_sex, maximum_age = max(maximum_sex, s_err), max(maximum_age, a_err)
        weighted_unemployed += raw["12"]
        weighted_force += raw["22"]
        expected[code] = {"unemployed_15_plus": raw["12"], "employed_15_plus": raw["1"],
                          "labour_force_15_plus": raw["22"], "inactive_15_plus": raw["23"],
                          "population_15_plus": raw["99"], "unknown_labour_status_15_plus": Decimal(0),
                          "rate": (Decimal(100) * raw["12"] / raw["22"]).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)}
    manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
    for key, file in [("original_export_sha256", source), ("metadata_xml_sha256", metadata),
                      ("normalized_csv_sha256", normalized), ("municipality_registry_sha256", registry)]:
        if manifest_data.get(key) != sha(file):
            raise ValueError(f"Manifest SHA-256 mismatch: {key}")
    if manifest_data.get("scientific_approval") is not False or manifest_data.get("canonical_data_modified") is not False:
        raise ValueError("Invalid evidence status in manifest")
    if preview is not None:
        preview_rows = load_csv(preview)
        observed = set()
        for row in preview_rows:
            code = row["municipality_code"]
            if code not in expected or code in observed or row.get("status") != STATUS:
                raise ValueError("Invalid H46 preview coverage or status")
            observed.add(code)
            for key in ("unemployed_15_plus", "employed_15_plus", "labour_force_15_plus",
                        "inactive_15_plus", "population_15_plus", "unknown_labour_status_15_plus"):
                if Decimal(row[key]) != expected[code][key]:
                    raise ValueError(f"Preview vs raw source count mismatch: {code}/{key}")
            if Decimal(row["unemployment_rate_15_plus_pct"]) != expected[code]["rate"]:
                raise ValueError(f"Preview vs raw source rate mismatch: {code}")
        if len(observed) != 27:
            raise ValueError("Expected exactly 27 preview rows")
    return {"status": STATUS, "indicator_id": "H46", "independent_source_audit_passed": True,
            "scientific_approval": False, "canonical_data_modified": False,
            "reference_year": "2024", "coverage": "27/27", "normalized_rows": 162,
            "source_sha256": sha(source), "metadata_sha256": sha(metadata),
            "normalized_sha256": sha(normalized), "manifest_sha256": sha(manifest),
            "preview_checked": preview is not None,
            "sex_reconciliations": 243, "age_reconciliations": 243,
            "omitted_age_cells_reconciled_as_zero": omitted_zero_age_cells,
            "max_sex_residual": format(maximum_sex, "f"),
            "max_age_residual": format(maximum_age, "f"),
            "max_labour_force_residual": format(maximum_force, "f"),
            "max_population_residual": format(maximum_population, "f"),
            "max_inactive_subgroup_residual": format(maximum_subtotal, "f"),
            "weighted_unemployment_rate_pct": format((Decimal(100) * weighted_unemployed / weighted_force).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), "f")}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--original-export", type=Path, required=True)
    p.add_argument("--metadata-xml", type=Path, required=True)
    p.add_argument("--normalized-csv", type=Path, required=True)
    p.add_argument("--normalization-manifest", type=Path, required=True)
    p.add_argument("--registry", type=Path, required=True)
    p.add_argument("--preview-csv", type=Path)
    p.add_argument("--out-file", type=Path, required=True)
    a = p.parse_args(argv)
    if a.out_file.exists():
        p.error("Audit file exists: preserve previous reviews")
    for f in (a.original_export, a.metadata_xml, a.normalized_csv, a.normalization_manifest, a.registry):
        if not f.is_file():
            p.error(f"Missing evidence: {f}")
    if a.preview_csv is not None and not a.preview_csv.is_file():
        p.error("Preview CSV missing")
    report = audit(a.original_export, a.metadata_xml, a.normalized_csv,
                   a.normalization_manifest, a.registry, a.preview_csv)
    a.out_file.parent.mkdir(parents=True, exist_ok=True)
    a.out_file.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("H46: independent source/sex/age/metadata audit PASS; scientific approval pending")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
