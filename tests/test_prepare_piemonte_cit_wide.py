"""Regression tests for real wide CIT headers with synthetic numeric values."""
import csv
import importlib.util
import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location("cit_wide_v02", ROOT/"scripts/prepare_piemonte_cit_wide.py")
assert SPEC and SPEC.loader
WIDE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(WIDE)
REGISTRY = ROOT/"data/municipalities.csv"


def towns():
    with REGISTRY.open(encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))


def fixture(tmp_path, mode, *, missing=False, names=False):
    path=tmp_path/("cit_"+mode+".csv")
    fields=WIDE.FUEL_HEADERS if mode=="fuel" else WIDE.AGE_HEADERS
    with path.open("w",encoding="utf-8-sig",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=fields,delimiter=";",lineterminator="\n")
        writer.writeheader()
        for i,town in enumerate(towns()):
            if missing and i==0:
                continue
            if mode=="fuel":
                row={c:"0" for c in WIDE.FUEL_COLUMNS}
                row.update({"key_classe":town["municipality"] if names else town["istat_code"],
                            "gas_naturale":"70", "gasolio":"10", "gpl":"20"})
            else:
                row={c:"0" for c in WIDE.AGE_COLUMNS}
                row.update({"denominazione_provincia":"TORINO",
                            "istat_comune":town["istat_code"],
                            "denominazione_comune":town["municipality"],
                            "numero_2001_2005":"20", "numero_2006_2010":"30",
                            "numero_2011_2015":"50"})
            writer.writerow(row)
    return path


def test_wide_fuel_groups_and_selected_towns(tmp_path):
    rows, qa=WIDE.extract_wide(fixture(tmp_path,"fuel"),REGISTRY,"fuel",date(2026,10,30))
    assert len(rows)==27
    assert all(r["generator_groups_total"]==100 for r in rows)
    assert all(r["diesel_lpg_share_pct"]=="30.00" for r in rows)
    assert qa["municipalities_with_generator_data"]==27
    assert qa["source_matches_user_inspection_hash"] is False
    assert qa["validated_for_release"] is False


def test_wide_fuel_accepts_exact_unique_names(tmp_path):
    rows,qa=WIDE.extract_wide(fixture(tmp_path,"fuel",names=True),REGISTRY,"fuel",date(2026,10,30))
    assert len(rows)==27 and not qa["missing"]


def test_installation_bins_20_years_lower_upper_bound(tmp_path):
    rows,qa=WIDE.extract_wide(fixture(tmp_path,"age"),REGISTRY,"age",date(2026,10,30))
    assert all(r["generator_groups_total"]==100 for r in rows)
    assert all(r["groups_aged_20_or_more"]==20 for r in rows)
    assert all(r["groups_ambiguous_age"]==30 for r in rows)
    assert all(r["older_generator_share_pct"]=="20.00" for r in rows)
    assert all(r["older_upper_bound_share_pct"]=="50.00" for r in rows)
    assert qa["age_interval_uncertainty_groups"]==810


def test_missing_town_is_unavailable_not_zero(tmp_path):
    rows,qa=WIDE.extract_wide(fixture(tmp_path,"age",missing=True),REGISTRY,"age",date(2026,10,30))
    assert qa["municipalities_with_generator_data"]==26
    assert qa["qa_status"]=="technical_incomplete_do_not_publish"
    assert any(r["older_generator_share_pct"]=="" for r in rows)


def test_unrecognized_composite_key_does_not_fuzzy_match(tmp_path):
    path=fixture(tmp_path,"fuel")
    text=path.read_text(encoding="utf-8-sig").replace(towns()[0]["istat_code"],"UNRECOGNIZED_KEY",1)
    path.write_text(text,encoding="utf-8-sig")
    rows,qa=WIDE.extract_wide(path,REGISTRY,"fuel",date(2026,10,30))
    assert qa["municipalities_with_generator_data"]==26
    assert "UNRECOGNIZED_KEY" in qa["source_schema"]["unmatched_key_samples"]


def test_duplicate_and_bad_counts_fail_closed(tmp_path):
    file=fixture(tmp_path,"fuel")
    with file.open(encoding="utf-8-sig",newline="") as f:
        original=list(csv.DictReader(f,delimiter=";"))
    with file.open("w",encoding="utf-8-sig",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=WIDE.FUEL_HEADERS,delimiter=";")
        writer.writeheader()
        writer.writerows([*original,original[0]])
    rows,qa=WIDE.extract_wide(file,REGISTRY,"fuel",date(2026,10,30))
    assert len(rows)==27
    assert rows[0]["generator_groups_total"]==100
    assert qa["source_schema"]["identical_source_rows_skipped"]==1
    assert qa["source_schema"]["duplicate_selected_rows"][0]["status"]=="identical_counts"
    age=fixture(tmp_path,"age")
    with age.open(encoding="utf-8-sig",newline="") as f:
        original=list(csv.DictReader(f,delimiter=";"))
    original[0]["numero_2006_2010"]=""
    with age.open("w",encoding="utf-8-sig",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=WIDE.AGE_HEADERS,delimiter=";")
        writer.writeheader()
        writer.writerows(original)
    with pytest.raises(ValueError,match="invalid/blank"):
        WIDE.extract_wide(age,REGISTRY,"age",date(2026,10,30))


def test_inspector_now_recognizes_both_wide_schemas(tmp_path):
    import inspect_piemonte_cit as inspector
    for mode in ("fuel","age"):
        result=inspector.inspect(fixture(tmp_path,mode),REGISTRY,mode)
        assert result["layout"]=="wide"
        assert result["selected_27_matched"]==27
        assert result["requires_schema_mapping"] is False
        assert result["key_examples"]


def test_wrong_header_is_not_guessed(tmp_path):
    file=fixture(tmp_path,"fuel")
    text=file.read_text(encoding="utf-8-sig").replace("key_classe;","bad_key;",1)
    file.write_text(text,encoding="utf-8-sig")
    with pytest.raises(ValueError,match="Unexpected CIT wide schema"):
        WIDE.extract_wide(file,REGISTRY,"fuel",date(2026,10,30))



def test_conflicting_fuel_duplicate_rejected_with_code_lines_and_diff(tmp_path):
    file=fixture(tmp_path,"fuel")
    with file.open(encoding="utf-8-sig",newline="") as handle:
        rows=list(csv.DictReader(handle,delimiter=";"))
    conflicting=dict(rows[0])
    conflicting["gasolio"]="99"
    with file.open("w",encoding="utf-8-sig",newline="") as handle:
        writer=csv.DictWriter(handle,fieldnames=WIDE.FUEL_HEADERS,delimiter=";")
        writer.writeheader()
        writer.writerows([*rows,conflicting])
    raw=WIDE.load_csv(file,WIDE.FUEL_HEADERS)
    report=WIDE.inspect_selected_duplicates(raw,WIDE.read_registry(REGISTRY),"fuel")
    assert len(report)==1
    assert report[0]["status"]=="conflicting_counts"
    assert report[0]["differing_count_fields"]==["gasolio"]
    assert report[0]["source_lines"]==[2,29]
    with pytest.raises(ValueError,match="Conflicting CIT rows.*001007.*gasolio"):
        WIDE.extract_wide(file,REGISTRY,"fuel",date(2026,10,30))
    import inspect_piemonte_cit as inspector
    detailed=inspector.inspect(file,REGISTRY,"fuel")
    assert detailed["selected_duplicate_conflicts"][0]["istat_code"]=="001007"
    assert detailed["selected_duplicate_rows"][0]["row_totals"]==[100,189]


def test_duplicate_age_identical_counts_never_double_counted(tmp_path):
    path=fixture(tmp_path,"age")
    with path.open(encoding="utf-8-sig",newline="") as handle:
        rows=list(csv.DictReader(handle,delimiter=";"))
    duplicate=dict(rows[0])
    with path.open("w",encoding="utf-8-sig",newline="") as handle:
        writer=csv.DictWriter(handle,fieldnames=WIDE.AGE_HEADERS,delimiter=";")
        writer.writeheader()
        writer.writerows([*rows,duplicate])
    result,qa=WIDE.extract_wide(path,REGISTRY,"age",date(2026,10,30))
    assert len(result)==27
    assert result[0]["generator_groups_total"]==100
    assert qa["source_schema"]["identical_source_rows_skipped"]==1
    assert qa["source_schema"]["duplicate_selected_rows"][0]["status"]=="identical_counts"


def test_duplicate_age_changed_name_is_not_silently_merged(tmp_path):
    path=fixture(tmp_path,"age")
    with path.open(encoding="utf-8-sig",newline="") as handle:
        rows=list(csv.DictReader(handle,delimiter=";"))
    bad=dict(rows[0])
    bad["denominazione_comune"]="Un altro Comune"
    with path.open("w",encoding="utf-8-sig",newline="") as handle:
        writer=csv.DictWriter(handle,fieldnames=WIDE.AGE_HEADERS,delimiter=";")
        writer.writeheader()
        writer.writerows([*rows,bad])
    diagnostics=WIDE.inspect_selected_duplicates(
        WIDE.load_csv(path,WIDE.AGE_HEADERS), WIDE.read_registry(REGISTRY),"age")
    assert diagnostics[0]["status"]=="conflicting_identity"
    with pytest.raises(ValueError,match="conflicting|Conflicting"):
        WIDE.extract_wide(path,REGISTRY,"age",date(2026,10,30))



@pytest.mark.parametrize("mode", ["fuel", "age"])
def test_conflicted_pont_canavese_quarantined_without_fabricated_zero(tmp_path,mode):
    original = fixture(tmp_path, mode, names=(mode == "fuel"))
    with original.open(encoding="utf-8-sig", newline="") as f:
        records = list(csv.DictReader(f, delimiter=";"))
    # Pont Canavese belongs to the 27-town fixture, and the extra row
    # shares its ISTAT identity but differs in one original count.
    if mode == "fuel":
        selected = next(r for r in records
                        if WIDE.normalize(r["key_classe"]) == WIDE.normalize("Pont Canavese"))
        extra = dict(selected)
        extra["key_classe"] = "PONT-CANAVESE"
        extra["gas_naturale"] = "7"
        field = "diesel_lpg_share_pct"
    else:
        selected = next(r for r in records if r["istat_comune"] == "001199")
        extra = dict(selected)
        extra["numero_2006_2010"] = "7"
        field = "older_generator_share_pct"
    with original.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=WIDE.FUEL_HEADERS if mode == "fuel" else WIDE.AGE_HEADERS,
            delimiter=";", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows([*records, extra])
    with pytest.raises(ValueError, match="Conflicting CIT"):
        WIDE.extract_wide(original, REGISTRY, mode, date(2026, 10, 30))
    rows, qa = WIDE.extract_wide(
        original, REGISTRY, mode, date(2026, 10, 30),
        quarantine_conflicts=True
    )
    assert len(rows) == 27
    assert qa["qa_status"] == "technical_incomplete_do_not_publish"
    assert qa["validated_for_release"] is False
    assert qa["municipalities_with_generator_data"] == 26
    assert qa["quarantined_municipalities"] == ["001199"]
    assert len(qa["missing"]) == 1
    assert qa["missing"][0]["reason"] == "conflicting_source_rows_quarantined"
    pont = next(row for row in rows if row["istat_code"] == "001199")
    assert pont[field] == ""
    assert pont["generator_groups_total"] == ""
    assert pont["observation_status"] == "source_conflict_quarantined"
    assert sum(r["observation_status"] == "technical_observation" for r in rows) == 26
    assert qa["source_schema"]["quarantined_duplicate_conflicts"][0]["status"] == "conflicting_counts"
    evidence = qa["source_schema"]["quarantined_duplicate_conflicts"][0]["source_records"]
    assert len(evidence) == 2
    assert evidence[0]["counts"] != evidence[1]["counts"]


def test_quarantine_option_keeps_nonconflicted_27_town_source_complete(tmp_path):
    original = fixture(tmp_path, "fuel")
    rows, qa = WIDE.extract_wide(
        original, REGISTRY, "fuel", date(2026, 10, 30),
        quarantine_conflicts=True
    )
    assert qa["qa_status"] == "technical_extraction_only"
    assert qa["quarantined_municipalities"] == []
    assert len(rows) == 27


def test_conflict_review_evidence_contains_exact_source_columns_and_lines(tmp_path):
    original = fixture(tmp_path, "fuel", names=True)
    with original.open(encoding="utf-8-sig", newline="") as f:
        records = list(csv.DictReader(f, delimiter=";"))
    selected = next(r for r in records if WIDE.normalize(r["key_classe"]) ==
                    WIDE.normalize("Pont Canavese"))
    extra = dict(selected)
    extra["key_classe"] = "PONT-CANAVESE"
    extra["gpl"] = "43"
    with original.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=WIDE.FUEL_HEADERS, delimiter=";")
        writer.writeheader()
        writer.writerows([*records, extra])
    source = WIDE.load_csv(original, WIDE.FUEL_HEADERS)
    changes = WIDE.inspect_selected_duplicates(source, WIDE.read_registry(REGISTRY), "fuel")
    assert changes[0]["istat_code"] == "001199"
    assert changes[0]["differing_count_fields"] == ["gpl"]
    assert changes[0]["source_records"][0]["counts"]["gpl"] == 20
    assert changes[0]["source_records"][1]["counts"]["gpl"] == 43
    assert changes[0]["source_records"][0]["line"] != changes[0]["source_records"][1]["line"]
