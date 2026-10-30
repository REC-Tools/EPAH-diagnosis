"""Synthetic Regione Piemonte CIT tests. NOT real municipal observations."""
import csv
import importlib.util
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/prepare_piemonte_cit.py"
SPEC = importlib.util.spec_from_file_location("cit_v02", SCRIPT)
assert SPEC and SPEC.loader
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


def source(tmp_path, mode, *, empty=False):
    registry = list(csv.DictReader((ROOT / "data/municipalities.csv").open(encoding="utf-8")))
    filename = tmp_path / (mode + ".csv")
    with filename.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, delimiter=";", lineterminator="\n",
                                fieldnames=["Key_istat_comune", "Desc_combustibile" if mode=="fuel" else "Anno_installazione", "Numero"])
        writer.writeheader()
        for i, entry in enumerate(registry):
            if empty and i==0:
                continue
            for label, value in ([("Gas naturale", 70), ("GPL", 20), ("Gasolio",10)]
                                 if mode=="fuel" else [("1999",25),("2018",75)]):
                writer.writerow({"Key_istat_comune":entry["istat_code"],
                                 ("Desc_combustibile" if mode=="fuel" else "Anno_installazione"): label,
                                 "Numero":value})
    return filename


def test_fuel_share_is_based_on_generator_groups_not_households(tmp_path):
    path=source(tmp_path,"fuel")
    rows, qa = MOD.prepare(path,ROOT/"data/municipalities.csv","fuel","2026-10-30")
    assert len(rows)==27
    assert rows[0]["generator_groups_total"]==100
    assert rows[0]["diesel_lpg_share_pct"]=="30.00"
    assert rows[0]["denominator"]=="classified_generator_groups"
    assert qa["qa_status"]=="technical_extraction_only"
    assert qa["validated_for_release"] is False


def test_generator_age_uses_dated_groups_and_snapshot_year(tmp_path):
    path=source(tmp_path,"age")
    rows, qa=MOD.prepare(path,ROOT/"data/municipalities.csv","age","2026-10-30")
    assert rows[0]["groups_aged_20_or_more"]==25
    assert rows[0]["older_generator_share_pct"]=="25.00"
    assert qa["older_years_threshold"]==20


def test_missing_municipality_is_not_published_as_zero(tmp_path):
    path=source(tmp_path,"fuel",empty=True)
    rows,qa=MOD.prepare(path,ROOT/"data/municipalities.csv","fuel","2026-10-30")
    assert qa["municipalities_with_generator_data"]==26
    assert qa["qa_status"]=="technical_incomplete_do_not_publish"
    assert any(r["diesel_lpg_share_pct"]=="" for r in rows)


def test_unknown_fuel_not_silently_assigned(tmp_path):
    assert MOD.fuel_category("Gas naturale")=="natural_gas"
    assert MOD.fuel_category("Gpl")=="lpg"
    assert MOD.fuel_category("Hydrogen imaginary type")=="unclassified"


def test_year_bin_and_future_dates_fail_closed():
    with pytest.raises(ValueError, match="Ambiguous"):
        MOD.installation_year("1990-2000")
    with pytest.raises(ValueError, match="Invalid"):
        MOD.installation_year("1880")


def test_invalid_negative_count_and_ambiguous_header_fail(tmp_path):
    path=source(tmp_path,"fuel")
    text=path.read_text(encoding="utf-8").replace(";70\n",";-70\n",1)
    path.write_text(text,encoding="utf-8")
    with pytest.raises(ValueError,match="count"):
        MOD.read_long_csv(path,"fuel")


def test_explicit_schema_column_mapping(tmp_path):
    f=tmp_path/"other.csv"
    f.write_text("COM_ID;VETTORE;TOTAL_N\n001007;GPL;10\n",encoding="utf-8")
    data,meta=MOD.read_long_csv(f,"fuel",code_col="COM_ID",category_col="VETTORE",count_col="TOTAL_N")
    assert data[0]["count"]==10
    assert meta["fields"]["category"]=="VETTORE"
