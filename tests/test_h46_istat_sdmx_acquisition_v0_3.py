"""H46 raw ISTAT SDMX acquisition: synthetic, offline fixtures only, no network."""
from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


acq = load("acquire_h46_istat_sdmx_v0_3")

COLUMNS = ["DATAFLOW", "FREQ", "REF_AREA", "INDICATOR", "GENDER", "AGE_NOCLASS", "CITIZENSHIP",
           "EDU_ATTAIN", "CUR_ACT_STAT", "LOC_DEST", "REAS_COMMUTING", "TIME_PERIOD",
           "OBS_VALUE", "OBS_STATUS"]
# Non-integer register estimates, as in the real ISTAT 2024 flow.
VALUES = {"1": "93", "12": "7.970101160766249", "22": "100.97010116076625",
          "23": "130.02989883923374", "99": "231", "4": "16.25"}
DSD = """<?xml version="1.0"?>
<m:Structure xmlns:m="urn:m" xmlns:s="urn:s" xmlns:c="urn:c">
<s:DataStructure id="DSD">
 <s:Dimension id="FREQ" position="1"/>
 <s:Dimension id="REF_AREA" position="2"/>
 <s:Dimension id="CUR_ACT_STAT" position="3"><s:LocalRepresentation><s:Enumeration><Ref id="CL_STAT" class="Codelist"/></s:Enumeration></s:LocalRepresentation></s:Dimension>
</s:DataStructure>
<s:Codelist id="CL_STAT">
 <s:Code id="1"><c:Name xml:lang="it">occupato</c:Name><c:Name xml:lang="en">employed</c:Name></s:Code>
 <s:Code id="12"><c:Name xml:lang="en">jobseeker</c:Name><c:Name xml:lang="it">in cerca di occupazione</c:Name></s:Code>
</s:Codelist>
</m:Structure>"""


def registry(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    path = tmp_path / "municipalities.csv"
    reg = {f"001{i:03d}": f"Comune {i}" for i in range(1, 28)}
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["municipality", "istat_code"])
        writer.writerows((name, code) for code, name in reg.items())
    return path, reg


def raw_export(path: Path, reg: dict[str, str], *, drop: str | None = None,
               override: dict[tuple[str, str], str] | None = None) -> Path:
    override = override or {}
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        for code in [*reg, "001999"]:  # 001999 is outside the 27 and must be filtered
            if code == drop:
                continue
            for stat, value in VALUES.items():
                for age in ("Y_GE15", "Y15-24"):
                    for gender in ("T", "M"):
                        writer.writerow({
                            "DATAFLOW": "IT1:X", "FREQ": "A", "REF_AREA": code,
                            "INDICATOR": "RESPOP_AV", "GENDER": gender, "AGE_NOCLASS": age,
                            "CITIZENSHIP": "TOTAL", "EDU_ATTAIN": "ALL", "CUR_ACT_STAT": stat,
                            "LOC_DEST": "ALL", "REAS_COMMUTING": "ALL", "TIME_PERIOD": "2024",
                            "OBS_VALUE": override.get((code, stat), value), "OBS_STATUS": ""})
    return path


def make_intake(tmp_path: Path, **kwargs) -> tuple[Path, Path, int]:
    reg_path, reg = registry(tmp_path)
    export = raw_export(tmp_path / "export.csv", reg, **kwargs)
    out = tmp_path / "intake"
    code = acq.main(["--registry", str(reg_path), "--out-dir", str(out),
                     "--original-export", str(export)])
    return out, reg_path, code


# --- acquisition -----------------------------------------------------------

def test_offline_intake_filters_27_and_total_sex(tmp_path: Path) -> None:
    out, _, code = make_intake(tmp_path)
    assert code == 0
    audit = json.loads((out / "H46_codebook_and_coverage.json").read_text(encoding="utf-8"))
    assert audit["municipality_coverage"] == "27/27"
    assert audit["rows_2024_for_27_municipalities_total_sex"] == 27 * len(VALUES) * 2
    assert audit["scientific_approval"] is False
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    for name, digest in manifest["files_sha256"].items():
        assert acq.sha256(out / name) == digest
    assert manifest["dimension_order_provenance"].startswith("manual_export")


def test_incomplete_coverage_returns_2(tmp_path: Path) -> None:
    out, _, code = make_intake(tmp_path, drop="001005")
    assert code == 2
    audit = json.loads((out / "H46_codebook_and_coverage.json").read_text(encoding="utf-8"))
    assert audit["missing_municipalities"] == [{"code": "001005", "name": "Comune 5"}]


def test_existing_out_dir_never_overwritten(tmp_path: Path) -> None:
    reg_path, reg = registry(tmp_path)
    export = raw_export(tmp_path / "export.csv", reg)
    out = tmp_path / "intake"
    out.mkdir()
    with pytest.raises(SystemExit):
        acq.main(["--registry", str(reg_path), "--out-dir", str(out), "--original-export", str(export)])
    assert list(out.iterdir()) == []


def test_malformed_export_leaves_no_partial_folder(tmp_path: Path) -> None:
    reg_path, _ = registry(tmp_path)
    bad = tmp_path / "bad.csv"
    bad.write_text("REF_AREA,TIME_PERIOD\n001001,2024\n", encoding="utf-8")
    out = tmp_path / "intake"
    with pytest.raises(ValueError, match="not expected SDMX CSV"):
        acq.main(["--registry", str(reg_path), "--out-dir", str(out), "--original-export", str(bad)])
    assert not out.exists()
    assert not any(p.name.startswith(".epah-h46-intake-") for p in tmp_path.iterdir())


def test_network_failure_leaves_no_partial_folder(tmp_path: Path, monkeypatch) -> None:
    reg_path, _ = registry(tmp_path)

    def offline(*_args, **_kwargs):
        raise RuntimeError("offline test")

    monkeypatch.setattr(acq, "fetch_one", offline)
    out = tmp_path / "intake"
    with pytest.raises(RuntimeError, match="offline test"):
        acq.main(["--registry", str(reg_path), "--out-dir", str(out)])
    assert not out.exists()


def test_parse_metadata_reads_dimensions_and_italian_labels() -> None:
    dims, labels = acq.parse_metadata(DSD.encode())
    assert dims == ["FREQ", "REF_AREA", "CUR_ACT_STAT"]
    assert labels["CUR_ACT_STAT"] == {"1": "occupato", "12": "in cerca di occupazione"}


def test_build_key_selects_only_freq_and_area() -> None:
    assert acq.build_key(["FREQ", "REF_AREA", "GENDER"], ["001001", "001002"]) == "A.001001+001002."
    with pytest.raises(ValueError):
        acq.build_key(["GENDER"], ["001001"])
