"""Synthetic source regression tests: no official observations checked into git."""
import csv
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


normalizer = load("normalize_h46_istat_sdmx_v0_3")
independent = load("audit_h46_istat_independent_v0_3")


def writer(path, fields, rows):
    with path.open("w", encoding="utf-8", newline="") as file:
        w = csv.DictWriter(file, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def corpus(tmp_path):
    registry = tmp_path / "registry.csv"
    codes = [f"001{k:03}" for k in range(1, 28)]
    writer(registry, ["municipality", "istat_code"],
           [{"municipality": f"Town {i}", "istat_code": code} for i, code in enumerate(codes)])
    meta = tmp_path / "meta.xml"
    pieces = []
    for code, label, parent in [("1", "occupato", "22"), ("12", "in cerca di occupazione", "22"),
                                 ("22", "forze di lavoro", None), ("23", "non forze di lavoro", None),
                                 ("24", "pensionato", "23"), ("4", "casalinga", "23"),
                                 ("5", "studente", "23"), ("7", "altro", "23"),
                                 ("99", "totale", None)]:
        p = f'<s:Parent><Ref id="{parent}" /></s:Parent>' if parent else ""
        pieces.append(f'<s:Code id="{code}"><c:Name xml:lang="it">{label}</c:Name>{p}</s:Code>')
    meta.write_text('<m:Structure xmlns:m="http://www.sdmx.org/resources/sdmxml/schemas/v2_1/message" '
                    'xmlns:s="http://www.sdmx.org/resources/sdmxml/schemas/v2_1/structure" '
                    'xmlns:c="http://www.sdmx.org/resources/sdmxml/schemas/v2_1/common">'
                    '<s:Dataflow id="DF_DCSS_ISTR_LAV_PEN_2_TV_3" version="1.0"/>'
                    '<s:Codelist id="CL_FORZE_LAV">' + "".join(pieces) + "</s:Codelist></m:Structure>", encoding="utf-8")
    source = tmp_path / "original.csv"
    values = {"1": "80", "12": "1.499", "22": "81.499", "23": "18.501",
              "24": "10", "4": "5", "5": "2", "7": "1.501", "99": "100"}
    fields = ["DATAFLOW", "FREQ", "REF_AREA", "INDICATOR", "GENDER", "AGE_NOCLASS",
              "CITIZENSHIP", "EDU_ATTAIN", "CUR_ACT_STAT", "LOC_DEST",
              "REAS_COMMUTING", "TIME_PERIOD", "OBS_VALUE", "OBS_STATUS"]
    rows = []
    for municipality in codes:
        for stat, v in values.items():
            for gender, age, d in [("T", "Y_GE15", "1"), ("M", "Y_GE15", "2"),
                                   ("F", "Y_GE15", "2"), ("T", "Y15-24", "4"),
                                   ("T", "Y25-49", "4"), ("T", "Y50-64", "4"),
                                   ("T", "Y_GE65", "4")]:
                from decimal import Decimal
                rows.append(dict(DATAFLOW=normalizer.FLOW, FREQ="A", REF_AREA=municipality,
                                 INDICATOR="RESPOP_AV", GENDER=gender, AGE_NOCLASS=age,
                                 CITIZENSHIP="TOTAL", EDU_ATTAIN="ALL", CUR_ACT_STAT=stat,
                                 LOC_DEST="ALL", REAS_COMMUTING="ALL", TIME_PERIOD="2024",
                                 OBS_VALUE=str(Decimal(v) / Decimal(d)), OBS_STATUS=""))
    writer(source, fields, rows)
    return source, meta, registry, rows, fields


def build(tmp_path, source, meta, registry, out_name="review"):
    out = tmp_path / out_name
    r = subprocess.run([sys.executable, str(SCRIPTS / "normalize_h46_istat_sdmx_v0_3.py"),
                        "--original-export", str(source), "--metadata-xml", str(meta),
                        "--registry", str(registry), "--out-dir", str(out)],
                       text=True, capture_output=True)
    return r, out


def test_full_synthetic_source_round_trip_and_unchanged_csv(tmp_path):
    source, meta, registry, _, _ = corpus(tmp_path)
    original_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    result, out = build(tmp_path, source, meta, registry)
    assert result.returncode == 0, result.stderr
    normalized = out / "labour_2024_normalized.csv"
    rows = independent.load_csv(normalized)
    assert len(rows) == 162
    assert rows[1]["labour_status"] == "unemployed" and rows[1]["persons"] == "1.499"
    qa = independent.audit(source, meta, normalized, out / "normalization_manifest.json", registry)
    assert qa["independent_source_audit_passed"] is True
    assert qa["sex_reconciliations"] == qa["age_reconciliations"] == 243
    assert qa["weighted_unemployment_rate_pct"] == "1.84"
    assert qa["scientific_approval"] is False
    assert hashlib.sha256(source.read_bytes()).hexdigest() == original_hash
    again, _ = build(tmp_path, source, meta, registry)
    assert again.returncode != 0 and "exists" in again.stderr


def test_tampering_with_normalized_estimate_fails_independent_check(tmp_path):
    source, meta, registry, _, _ = corpus(tmp_path)
    result, out = build(tmp_path, source, meta, registry)
    assert result.returncode == 0
    norm = out / "labour_2024_normalized.csv"
    norm.write_text(norm.read_text().replace("1.499", "2.499", 1))
    with pytest.raises(ValueError, match="mismatch"):
        independent.audit(source, meta, norm, out / "normalization_manifest.json", registry)


def test_wrong_metadata_fails_closed_before_output(tmp_path):
    source, meta, registry, _, _ = corpus(tmp_path)
    meta.write_text(meta.read_text().replace("in cerca di occupazione", "occupato", 1))
    result, out = build(tmp_path, source, meta, registry)
    assert result.returncode != 0
    assert not out.exists()


def test_missing_source_category_and_bad_decimal_fails_closed(tmp_path):
    source, meta, registry, rows, fields = corpus(tmp_path)
    selected = [r for r in rows if not (r["REF_AREA"] == "001001" and r["GENDER"] == "T"
                                       and r["AGE_NOCLASS"] == "Y_GE15" and r["CUR_ACT_STAT"] == "12")]
    writer(source, fields, selected)
    result, out = build(tmp_path, source, meta, registry)
    assert result.returncode != 0 and not out.exists()
    rows[0]["OBS_VALUE"] = "NaN"
    writer(source, fields, rows)
    result, out = build(tmp_path, source, meta, registry)
    assert result.returncode != 0 and not out.exists()


def test_actual_integrity_checks_do_not_permit_invalid_population_totals(tmp_path):
    source, meta, registry, rows, fields = corpus(tmp_path)
    for r in rows:
        if r["REF_AREA"] == "001001" and r["CUR_ACT_STAT"] == "99" and r["GENDER"] == "T" and r["AGE_NOCLASS"] == "Y_GE15":
            r["OBS_VALUE"] = "100.2"
    writer(source, fields, rows)
    result, out = build(tmp_path, source, meta, registry)
    assert result.returncode != 0 and not out.exists()
