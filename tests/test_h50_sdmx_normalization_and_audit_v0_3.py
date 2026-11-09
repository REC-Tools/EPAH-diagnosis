"""H50 SDMX normalization and independent audit: synthetic fixtures, no ISTAT data in git."""
from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


norm = load("normalize_h50_istat_sdmx_v0_3")
audit = load("audit_h50_istat_independent_v0_3")
prep = load("prepare_low_education_25_64_v0_3")

CODES = [f"001{k:03d}" for k in range(1, 28)]
FIELDS = ["DATAFLOW", "FREQ", "REF_AREA", "INDICATOR", "GENDER", "AGE_NOCLASS", "CITIZENSHIP",
          "EDU_ATTAIN", "CUR_ACT_STAT", "LOC_DEST", "REAS_COMMUTING", "TIME_PERIOD",
          "OBS_VALUE", "OBS_STATUS"]
# Per sex and age band. PSE omitted for Y50-64 (ISTAT drops zero cells); ALL for
# Y25-49 carries float representation noise like the real export.
MALE = {"Y25-49": {"NED": 1, "PSE": 2, "LSE": 10, "USE_IF": 20, "BL": 3, "ML_RDD": 4},
        "Y50-64": {"NED": 0, "LSE": 12, "USE_IF": 15, "BL": 1, "ML_RDD": 2},
        "Y9-24": {"NED": 5, "LSE": 6}}
FEMALE = {"Y25-49": {"NED": 0, "PSE": 3, "LSE": 9, "USE_IF": 22, "BL": 5, "ML_RDD": 6},
          "Y50-64": {"NED": 1, "LSE": 11, "USE_IF": 14, "BL": 2, "ML_RDD": 3},
          "Y9-24": {"NED": 4, "LSE": 7}}
LABELS = {"NED": "nessun titolo di studio", "PSE": "licenza di scuola elementare",
          "LSE": "licenza di scuola media inferiore o di avviamento professionale",
          "USE_IF": "diploma di istruzione secondaria di II grado o di qualifica professionale (corso di 3-4 anni) compresi IFTS",
          "BL": "diploma di tecnico superiore ITS o titolo di studio terziario di primo livello",
          "ML_RDD": "titolo di studio terziario di secondo livello e dottorato di ricerca",
          "NRP": "non indicato", "ALL": "totale", "IL": "analfabeti"}


def write_csv(path: Path, fields, rows) -> Path:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    return path


def metadata(path: Path, labels=LABELS, flow="DF_DCSS_ISTR_LAV_PEN_2_TV_1") -> Path:
    edu = "".join(
        f'<s:Code id="{c}"><c:Name xml:lang="it">{t}</c:Name>'
        + ('<s:Parent><Ref id="NED"/></s:Parent>' if c == "IL" else "") + "</s:Code>"
        for c, t in labels.items())
    ages = "".join(f'<s:Code id="{c}"><c:Name xml:lang="it">{t}</c:Name></s:Code>'
                   for c, t in {"Y25-49": "25-49 anni", "Y50-64": "50-64 anni", "Y9-24": "9-24 anni"}.items())
    path.write_text(
        '<m:Structure xmlns:m="http://www.sdmx.org/resources/sdmxml/schemas/v2_1/message" '
        'xmlns:s="http://www.sdmx.org/resources/sdmxml/schemas/v2_1/structure" '
        'xmlns:c="http://www.sdmx.org/resources/sdmxml/schemas/v2_1/common">'
        f'<s:Dataflow id="{flow}" version="1.0"/>'
        f'<s:Codelist id="CL_TITOLO_STUDIO">{edu}</s:Codelist>'
        f'<s:Codelist id="CL_ETA1">{ages}</s:Codelist></m:Structure>', encoding="utf-8")
    return path


def source_rows(overrides: dict | None = None, extra: list | None = None) -> list[dict]:
    overrides = overrides or {}
    rows = []
    for code in [*CODES, "002001"]:  # 002001 is outside the 27
        for age in ("Y25-49", "Y50-64", "Y9-24"):
            per_sex = {"M": MALE[age], "F": FEMALE[age]}
            per_sex["T"] = {e: MALE[age].get(e, 0) + FEMALE[age].get(e, 0)
                            for e in set(MALE[age]) | set(FEMALE[age])}
            for sex, values in per_sex.items():
                cells = {e: str(v) for e, v in values.items()}
                total = sum(values.values())
                cells["ALL"] = "84.99999999999999" if (sex, age, total) == ("T", "Y25-49", 85) else str(total)
                for edu, value in cells.items():
                    value = overrides.get((code, sex, age, edu), value)
                    if value is None:
                        continue
                    rows.append({"DATAFLOW": "IT1:DF_DCSS_ISTR_LAV_PEN_2_TV_1(1.0)", "FREQ": "A",
                                 "REF_AREA": code, "INDICATOR": "RESPOP_AV", "GENDER": sex,
                                 "AGE_NOCLASS": age, "CITIZENSHIP": "TOTAL", "EDU_ATTAIN": edu,
                                 "CUR_ACT_STAT": "99", "LOC_DEST": "ALL", "REAS_COMMUTING": "ALL",
                                 "TIME_PERIOD": "2024", "OBS_VALUE": value, "OBS_STATUS": ""})
    return rows + (extra or [])


def corpus(tmp_path: Path, **kwargs):
    registry = write_csv(tmp_path / "registry.csv", ["municipality", "istat_code"],
                         [{"municipality": f"Town {i}", "istat_code": c} for i, c in enumerate(CODES)])
    meta = metadata(tmp_path / "meta.xml")
    source = write_csv(tmp_path / "original.csv", FIELDS, source_rows(**kwargs))
    return registry, meta, source


def normalize(tmp_path: Path, registry, meta, source, out="norm"):
    return norm.main(["--original-export", str(source), "--metadata-xml", str(meta),
                      "--registry", str(registry), "--out-dir", str(tmp_path / out)])


def test_round_trip_normalize_prepare_and_independent_audit(tmp_path):
    registry, meta, source = corpus(tmp_path)
    assert normalize(tmp_path, registry, meta, source) == 0
    out = tmp_path / "norm"
    rows = list(csv.DictReader((out / "education_2024_normalized.csv").open(encoding="utf-8")))
    assert len(rows) == 162
    first = {r["education_group"]: r["persons"] for r in rows if r["municipality_code"] == "001001"}
    # 25-49 (T) + 50-64 (T); USE_IF + BL + ML_RDD -> upper_or_tertiary; PSE omitted in 50-64.
    assert first == {"none": "2", "primary": "5", "lower_secondary": "42",
                     "upper_or_tertiary": "97", "unknown": "0", "total": "146"}
    qa = json.loads((out / "normalization_qa.json").read_text(encoding="utf-8"))
    assert qa["qa"]["omitted_education_cells_reconciled_to_zero"] == 27
    assert qa["qa"]["totals_with_float_representation_noise"] == 27
    assert qa["scientific_approval"] is False
    values, prep_qa = prep.aggregate(out / "education_2024_normalized.csv", prep.read_registry(registry))
    assert values[0]["share_below_lower_secondary_25_64_pct"] == "4.79"
    preview = write_csv(tmp_path / "preview.csv", prep.COLUMNS_OUT, values)
    report = audit.audit(source, meta, out / "education_2024_normalized.csv",
                         out / "normalization_manifest.json", registry, preview)
    assert report["independent_source_audit_passed"] is True
    assert report["weighted_share_pct"] == "4.79"
    assert report["sex_reconciliations"] > 27 * 6


def test_real_fractional_count_blocks(tmp_path, capsys):
    registry, meta, source = corpus(tmp_path, overrides={
        ("001002", "T", "Y25-49", "NED"): "1.5", ("001002", "T", "Y25-49", "ALL"): "85.5"})
    with pytest.raises(SystemExit) as stop:
        normalize(tmp_path, registry, meta, source)
    assert stop.value.code == 1
    assert "non-integer" in capsys.readouterr().err
    assert not (tmp_path / "norm").exists()


def test_omitted_cell_that_breaks_total_blocks(tmp_path, capsys):
    registry, meta, source = corpus(tmp_path, overrides={("001003", "T", "Y25-49", "LSE"): None})
    with pytest.raises(SystemExit):
        normalize(tmp_path, registry, meta, source)
    assert "do not add up" in capsys.readouterr().err


def test_undocumented_child_code_blocks_to_avoid_double_counting(tmp_path, capsys):
    template = next(r for r in source_rows() if r["GENDER"] == "T" and r["AGE_NOCLASS"] == "Y25-49")
    extra = [dict(template, EDU_ATTAIN="IL", OBS_VALUE="1")]
    registry, meta, source = corpus(tmp_path, extra=extra)
    with pytest.raises(SystemExit):
        normalize(tmp_path, registry, meta, source)
    assert "Undocumented education code 'IL'" in capsys.readouterr().err


def test_changed_metadata_label_blocks(tmp_path, capsys):
    registry, _, source = corpus(tmp_path)
    meta = metadata(tmp_path / "other.xml", labels=dict(LABELS, PSE="licenza media"))
    with pytest.raises(SystemExit):
        normalize(tmp_path, registry, meta, source)
    assert "Unexpected metadata label for education PSE" in capsys.readouterr().err


def test_wrong_dataflow_metadata_blocks(tmp_path, capsys):
    registry, _, source = corpus(tmp_path)
    meta = metadata(tmp_path / "h46.xml", flow="DF_DCSS_ISTR_LAV_PEN_2_TV_3")
    with pytest.raises(SystemExit):
        normalize(tmp_path, registry, meta, source)
    assert "TV_1" in capsys.readouterr().err


def test_existing_out_dir_is_preserved(tmp_path):
    registry, meta, source = corpus(tmp_path)
    (tmp_path / "norm").mkdir()
    with pytest.raises(SystemExit):
        normalize(tmp_path, registry, meta, source)
    assert list((tmp_path / "norm").iterdir()) == []


def test_audit_detects_tampered_normalized_csv(tmp_path):
    registry, meta, source = corpus(tmp_path)
    normalize(tmp_path, registry, meta, source)
    normalized = tmp_path / "norm" / "education_2024_normalized.csv"
    text = normalized.read_text(encoding="utf-8").replace("001001,Town 0,2024,25-64,total,primary,5",
                                                         "001001,Town 0,2024,25-64,total,primary,6")
    normalized.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match="differs from independent reconstruction"):
        audit.audit(source, meta, normalized, tmp_path / "norm" / "normalization_manifest.json", registry, None)


def test_audit_detects_inconsistent_sex_split(tmp_path):
    registry, meta, source = corpus(tmp_path, overrides={("001004", "M", "Y9-24", "LSE"): "7"})
    with pytest.raises(ValueError, match="Sex split"):
        audit.audit(source, meta, tmp_path / "missing.csv", tmp_path / "missing.json", registry, None)


def test_audit_detects_preview_mismatch(tmp_path):
    registry, meta, source = corpus(tmp_path)
    normalize(tmp_path, registry, meta, source)
    out = tmp_path / "norm"
    values, _ = prep.aggregate(out / "education_2024_normalized.csv", prep.read_registry(registry))
    values[3]["share_below_lower_secondary_25_64_pct"] = "9.99"
    preview = write_csv(tmp_path / "preview.csv", prep.COLUMNS_OUT, values)
    with pytest.raises(ValueError, match="Preview vs raw source mismatch"):
        audit.audit(source, meta, out / "education_2024_normalized.csv",
                    out / "normalization_manifest.json", registry, preview)
