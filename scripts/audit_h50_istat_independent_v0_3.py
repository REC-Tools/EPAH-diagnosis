"""Independent H50 audit: does not import the normalizer or the H50 builder.

Re-reads the original ISTAT export and metadata, reconstructs the 27 x 6
normalized rows from its own parsing, checks the published sex split
(M + F = T for every cell, including the 9-24 band) and the education split
(categories = ALL), verifies the normalization manifest hashes and, when given,
the 27 H50 shares of the preview. Writes a JSON report; any discrepancy blocks.
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

FLOW = "IT1:DF_DCSS_ISTR_LAV_PEN_2_TV_1(1.0)"
STATUS = "technical_draft_do_not_publish"
TOL = Decimal("0.000001")
NUM = re.compile(r"\d+(?:\.\d+)?\Z")
H50_AGES = ("Y25-49", "Y50-64")
# Independent restatement of the documented ISTAT -> H50 mapping.
LOW = ("NED", "PSE")
GROUP_OF = {"NED": "none", "PSE": "primary", "LSE": "lower_secondary",
            "USE_IF": "upper_or_tertiary", "BL": "upper_or_tertiary",
            "ML_RDD": "upper_or_tertiary", "NRP": "unknown"}
FIXED = {"DATAFLOW": FLOW, "FREQ": "A", "INDICATOR": "RESPOP_AV", "CITIZENSHIP": "TOTAL",
         "CUR_ACT_STAT": "99", "LOC_DEST": "ALL", "REAS_COMMUTING": "ALL", "TIME_PERIOD": "2024"}
S = "{http://www.sdmx.org/resources/sdmxml/schemas/v2_1/structure}"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def load_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if any(None in r for r in rows):
        raise ValueError(f"Malformed CSV: {path.name}")
    return rows


def check_metadata(path: Path) -> None:
    root = ET.parse(path).getroot()
    if not any(x.get("id") == "DF_DCSS_ISTR_LAV_PEN_2_TV_1" and x.get("version") == "1.0"
               for x in root.iter(S + "Dataflow")):
        raise ValueError("Metadata is not the TV_1 education dataflow")
    education = next((x for x in root.iter(S + "Codelist") if x.get("id") == "CL_TITOLO_STUDIO"), None)
    if education is None:
        raise ValueError("Metadata lacks CL_TITOLO_STUDIO")
    present = {c.get("id"): c.find("./" + S + "Parent") is None for c in education.findall(S + "Code")}
    for code in [*GROUP_OF, "ALL"]:
        if not present.get(code):
            raise ValueError(f"Education code {code} missing or not top-level in metadata")


def audit(source: Path, metadata: Path, normalized: Path, manifest: Path,
          registry: Path, preview: Path | None) -> dict:
    check_metadata(metadata)
    names = {r["istat_code"].strip(): r["municipality"].strip() for r in load_csv(registry)}
    if len(names) != 27:
        raise ValueError("Registry must contain 27 municipalities")
    cell: dict[tuple[str, str, str, str], Decimal] = {}
    with source.open(encoding="utf-8-sig", newline="") as f:
        for i, row in enumerate(csv.DictReader(f), 2):
            if row.get("REF_AREA", "").strip() not in names or row.get("TIME_PERIOD") != "2024":
                continue
            if any(row.get(k, "").strip() != v for k, v in FIXED.items()):
                raise ValueError(f"Unexpected dimensions on source row {i}")
            value = row["OBS_VALUE"].strip()
            if row.get("OBS_STATUS", "").strip() or not NUM.fullmatch(value):
                raise ValueError(f"Flagged or non-numeric source value on row {i}")
            key = (row["REF_AREA"].strip(), row["GENDER"].strip(), row["AGE_NOCLASS"].strip(),
                   row["EDU_ATTAIN"].strip())
            if key in cell:
                raise ValueError(f"Duplicate source cell {key}")
            cell[key] = Decimal(value)
    get = lambda *k: cell.get(k, Decimal(0))  # noqa: E731 - omitted cell = 0, checked below
    sex_checks = edu_checks = 0
    max_sex = max_edu = Decimal(0)
    combos = {(a, g, e) for (a, _s, g, e) in cell}
    for area, age, edu in combos:
        diff = abs(get(area, "M", age, edu) + get(area, "F", age, edu) - get(area, "T", age, edu))
        if diff > TOL:
            raise ValueError(f"Sex split does not add up: {area}/{age}/{edu}")
        max_sex = max(max_sex, diff)
        sex_checks += 1
    for area in names:
        for sex in ("T", "M", "F"):
            for age in {g for (a, _s, g, _e) in cell if a == area}:
                if (area, sex, age, "ALL") not in cell:
                    continue
                diff = abs(sum((get(area, sex, age, e) for e in GROUP_OF), Decimal(0))
                           - cell[(area, sex, age, "ALL")])
                if diff > TOL:
                    raise ValueError(f"Education split does not add up: {area}/{sex}/{age}")
                max_edu = max(max_edu, diff)
                edu_checks += 1
    expected: dict[tuple[str, str], int] = {}
    shares: dict[str, Decimal] = {}
    total_all = low_all = 0
    for area in names:
        for age in H50_AGES:
            if (area, "T", age, "ALL") not in cell:
                raise ValueError(f"Missing ISTAT total for {area}/{age}")
        groups: dict[str, int] = defaultdict(int)
        for edu, group in GROUP_OF.items():
            value = sum((get(area, "T", age, edu) for age in H50_AGES), Decimal(0))
            if abs(value - value.to_integral_value()) > TOL:
                raise ValueError(f"Non-integer persons for {area}/{edu}")
            groups[group] += int(value.to_integral_value())
        total = sum(groups.values())
        published = sum((cell[(area, "T", age, "ALL")] for age in H50_AGES), Decimal(0))
        if abs(Decimal(total) - published) > TOL or total <= 0:
            raise ValueError(f"25-64 total mismatch at {area}")
        low = sum(int(sum((get(area, "T", age, e) for age in H50_AGES), Decimal(0)).to_integral_value()) for e in LOW)
        for group in ("none", "primary", "lower_secondary", "upper_or_tertiary", "unknown"):
            expected[(area, group)] = groups[group]
        expected[(area, "total")] = total
        shares[area] = (Decimal(100) * low / total).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        total_all += total
        low_all += low
    rows = load_csv(normalized)
    seen = {}
    for row in rows:
        key = (row["municipality_code"], row["education_group"])
        if (key in seen or row["age_band"] != "25-64" or row["sex"] != "total"
                or row["reference_year"] != "2024" or row["municipality"] != names.get(key[0])):
            raise ValueError(f"Unexpected normalized row {key}")
        seen[key] = int(row["persons"])
    if seen != expected:
        diff = sorted(k for k in set(seen) | set(expected) if seen.get(k) != expected.get(k))
        raise ValueError(f"Normalized CSV differs from independent reconstruction: {diff[:5]}")
    manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
    for key, file in [("original_export_sha256", source), ("metadata_xml_sha256", metadata),
                      ("normalized_csv_sha256", normalized), ("municipality_registry_sha256", registry)]:
        if manifest_data.get(key) != sha(file):
            raise ValueError(f"Manifest SHA-256 mismatch: {key}")
    if manifest_data.get("scientific_approval") is not False or manifest_data.get("canonical_data_modified") is not False:
        raise ValueError("Invalid evidence status in manifest")
    if preview is not None:
        observed = set()
        for row in load_csv(preview):
            code = row["municipality_code"]
            if code not in names or code in observed or row.get("status") != STATUS:
                raise ValueError("Invalid H50 preview coverage or status")
            observed.add(code)
            if (int(row["residents_25_64_total"]) != expected[(code, "total")]
                    or Decimal(row["share_below_lower_secondary_25_64_pct"]) != shares[code]):
                raise ValueError(f"Preview vs raw source mismatch: {code}")
        if len(observed) != 27:
            raise ValueError("Expected exactly 27 preview rows")
    return {"status": STATUS, "indicator_id": "H50", "independent_source_audit_passed": True,
            "scientific_approval": False, "canonical_data_modified": False,
            "reference_year": "2024", "coverage": "27/27", "normalized_rows": len(rows),
            "source_sha256": sha(source), "metadata_sha256": sha(metadata),
            "normalized_sha256": sha(normalized), "manifest_sha256": sha(manifest),
            "preview_checked": preview is not None,
            "sex_reconciliations": sex_checks, "education_reconciliations": edu_checks,
            "max_sex_residual": format(max_sex, "f"), "max_education_residual": format(max_edu, "f"),
            "residents_25_64_total": total_all, "residents_below_lower_secondary_25_64": low_all,
            "weighted_share_pct": format((Decimal(100) * low_all / total_all).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP), "f")}


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
    try:
        report = audit(a.original_export, a.metadata_xml, a.normalized_csv,
                       a.normalization_manifest, a.registry, a.preview_csv)
    except (ValueError, KeyError, ET.ParseError) as exc:
        p.exit(1, f"H50 AUDIT FAILED: {exc}\n")
    a.out_file.parent.mkdir(parents=True, exist_ok=True)
    a.out_file.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"H50: independent source/sex/education/metadata audit PASS "
          f"({report['sex_reconciliations']} sex, {report['education_reconciliations']} education checks); "
          "scientific approval pending")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
