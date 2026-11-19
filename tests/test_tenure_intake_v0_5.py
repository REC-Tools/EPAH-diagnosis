import csv
import json
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from epah_diagnosis.tenure_source_review_v0_5 import main as review_main
from epah_diagnosis.methodology_v0_5 import main as methodology_main
from epah_diagnosis.tenure_source_review_v0_5 import (
    CATEGORIES, DENOMINATOR_NOTE, DIMENSIONS, FLOW, NS, SELECTION, inspect_response, metadata_profile)
from epah_diagnosis.tenure_intake_v0_5 import acquire, main, source_url


def node(parent, scope, tag, **attributes):
    return ET.SubElement(parent, "{" + NS[scope] + "}" + tag, attributes)


def metadata(codes):
    root = ET.Element("{" + NS["m"] + "}Structure")
    flow = node(root, "s", "Dataflow", id=FLOW, agencyID="IT1", version="1.0")
    ET.SubElement(node(flow, "s", "Structure"), "Ref", id="DCSS_HUDW_TV", agencyID="IT1", version="1.0")
    ds = node(root, "s", "DataStructure", id="DCSS_HUDW_TV", agencyID="IT1", version="1.0")
    dims = node(node(ds, "s", "DataStructureComponents"), "s", "DimensionList")
    for i, name in enumerate(DIMENSIONS, 1):
        dim = node(dims, "s", "Dimension", id=name, position=str(i))
        ET.SubElement(node(node(dim, "s", "LocalRepresentation"), "s", "Enumeration"), "Ref", id="CL_" + name)
        scheme = node(root, "s", "Codelist", id="CL_" + name)
        values = codes if name == "REF_AREA" else sorted(CATEGORIES) if name == "TENURE_STATUS_HOU" else [SELECTION[name]]
        for value in values:
            node(scheme, "s", "Code", id=value)
    node(dims, "s", "TimeDimension", id="TIME_PERIOD", position="11")
    note = node(node(root, "s", "Codelist", id="CL_NOTES"), "s", "Code", id=DENOMINATOR_NOTE)
    label = node(note, "c", "Name")
    label.set("{http://www.w3.org/XML/1998/namespace}lang", "it")
    label.text = "Totale sintetico: famiglie senza tetto escluse"
    return ET.tostring(root)


def response(code, *, missing=None, periods=None, values=None, flag=None, note=True):
    root = ET.Element("{" + NS["m"] + "}GenericData")
    header = node(root, "m", "Header")
    usage = node(node(header, "m", "Structure"), "c", "StructureUsage")
    ET.SubElement(usage, "Ref", id=FLOW, agencyID="IT1", version="1.0")
    dataset = node(root, "m", "DataSet")
    raw_values = {"ALL": "10.000000", "OWN": "6.123456", "RENT": "2.500001", "OTH_OR": "1.376543"}
    raw_values.update(values or {})
    for category in sorted(CATEGORIES - set(missing or [])):
        series = node(dataset, "g", "Series")
        key = node(series, "g", "SeriesKey")
        for name, value in {**SELECTION, "REF_AREA": code, "TENURE_STATUS_HOU": category}.items():
            node(key, "g", "Value", id=name, value=value)
        if category == "ALL" and note:
            node(node(series, "g", "Attributes"), "g", "Value", id="NOTE_TENURE_STATUS_HOU", value=DENOMINATOR_NOTE)
        obs = node(series, "g", "Obs")
        node(obs, "g", "ObsDimension", id="TIME_PERIOD", value=(periods or {}).get(category, "2021"))
        if raw_values[category] is not None:
            node(obs, "g", "ObsValue", value=raw_values[category])
        if flag:
            node(node(obs, "g", "Attributes"), "g", "Value", id="OBS_STATUS", value=flag)
    return ET.tostring(root)


@pytest.fixture
def inputs(tmp_path):
    codes = [f"001{i:03}" for i in range(1, 28)]
    meta, seed, registry = [tmp_path / name for name in ["metadata.xml", "seed.xml", "registry.csv"]]
    meta.write_bytes(metadata(codes))
    seed.write_bytes(response(codes[0]))
    with registry.open("w", encoding="utf-8", newline="") as stream:
        csv.writer(stream).writerows([["municipality", "istat_code"],
                                     *[[f"Comune sintetico {i}", code] for i, code in enumerate(codes)]])
    return meta, seed, registry, codes


def test_source_values_and_notes_preserved_without_float_ratios_or_year_relabelling(inputs):
    meta, seed, _, codes = inputs
    profile = metadata_profile(meta.read_bytes())
    report = inspect_response(seed.read_bytes(), codes[0], profile)
    assert report["source_periods"] == ["2021"] and report["target_analysis_year"] == 2025
    assert next(o["value_as_received"] for o in report["observations"] if o["source_key"]["TENURE_STATUS_HOU"] == "RENT") == "2.500001"
    assert report["denominator_note_present"] and "escluse" in report["denominator_universe"]["source_text"]["it"]
    assert report["partition_difference_as_received"] == "0.000000" and report["review_issues"] == []
    assert report["indicator_calculated"] is report["scientific_approval"] is report["publication_allowed"] is False


@pytest.mark.parametrize("changes,issue", [
    ({"missing": ["RENT"]}, "missing_tenure_categories"),
    ({"periods": {"RENT": "2023"}}, "source_periods_missing_or_different"),
    ({"values": {"RENT": None}}, "missing_or_invalid_value:RENT"),
    ({"values": {"RENT": "NaN"}}, "missing_or_invalid_value:RENT"),
    ({"values": {"RENT": "-1"}}, "missing_or_invalid_value:RENT"),
    ({"values": {"ALL": "0"}}, "denominator_not_positive"),
    ({"values": {"RENT": "2.500002"}}, "partition_not_exact_no_tolerance_applied"),
    ({"note": False}, "denominator_universe_note_absent"),
])
def test_incomplete_or_incompatible_sources_are_exposed_not_imputed(inputs, changes, issue):
    profile = metadata_profile(inputs[0].read_bytes())
    report = inspect_response(response(inputs[3][0], **changes), inputs[3][0], profile)
    assert issue in report["review_issues"]
    assert report["municipal_series_added"] == 0


def test_flags_wrong_code_duplicates_and_changed_metadata_require_review(inputs):
    profile = metadata_profile(inputs[0].read_bytes())
    code = inputs[3][0]
    assert any("source_flag" in issue for issue in inspect_response(response(code, flag="p"), code, profile)["review_issues"])
    for raw in [response(inputs[3][1]), b"<html>error</html>", b"<!DOCTYPE a><a/>"]:
        with pytest.raises(ValueError):
            inspect_response(raw, code, profile)
    root = ET.fromstring(response(code))
    dataset = root.find("m:DataSet", NS)
    dataset.append(dataset[0])
    with pytest.raises(ValueError, match="Repeated"):
        inspect_response(ET.tostring(root), code, profile)
    with pytest.raises(ValueError):
        metadata_profile(inputs[0].read_bytes().replace(b'position="1"', b'position="2"'))


def test_sequential_intake_reuses_seed_keeps_receipts_and_preserves_inputs(inputs, tmp_path):
    meta, seed, registry, codes = inputs
    originals = [path.read_bytes() for path in [meta, seed, registry]]
    events = []
    def fetch(url):
        code = url.split("/A.")[1].split(".")[0]
        events.append(("fetch", code))
        return 200, response(code), None
    def wait(seconds):
        events.append(("wait", seconds))
    out = tmp_path / "run"
    result = acquire(meta, seed, registry, codes[0], out, fetch=fetch, wait=wait)
    assert result["source_snapshots_reviewed"] == 27 and result["requests_made"] == 26
    assert [v for kind, v in events if kind == "fetch"] == codes[1:]
    assert events[1::2] == [("wait", 16)] * 25
    assert len(list((out / "receipts").iterdir())) == 26
    assert (out / "raw" / (codes[0] + ".xml")).read_bytes() == originals[1]
    assert json.loads((out / "run.json").read_text())["phase"] == "requests_completed"
    assert all(path.read_bytes() == raw for path, raw in zip([meta, seed, registry], originals))
    with pytest.raises(FileExistsError):
        acquire(meta, seed, registry, codes[0], out, fetch=lambda _: pytest.fail("must not fetch"))


@pytest.mark.parametrize("failure", ["timeout", "quota", "wrong_identity"])
def test_failures_are_recorded_and_remaining_codes_are_not_zero(inputs, tmp_path, failure):
    meta, seed, registry, codes = inputs
    def fetch(url):
        if failure == "timeout":
            return None, None, "TimeoutError"
        if failure == "quota":
            return 429, b"rate limit", "HTTP 429"
        return 200, response(codes[0]), None
    out = tmp_path / "failed"
    result = acquire(meta, seed, registry, codes[0], out, fetch=fetch, wait=lambda _: None)
    assert result["requests_made"] == (3 if failure == "timeout" else 1)
    assert result["source_snapshots_reviewed"] == 1
    assert result["not_requested"] and result["failed_codes"]
    run = json.loads((out / "run.json").read_text())
    assert run["phase"] == "stopped_source_requires_review" and run["automatic_retries"] == 0
    assert all(r["response_sha256"] is None for r in run["records"] if r["state"] == "not_requested")


def test_interruption_and_read_only_plan_are_explicit(inputs, tmp_path, capsys):
    meta, seed, registry, codes = inputs
    out = tmp_path / "planned"
    argv = ["--metadata", str(meta), "--seed", str(seed), "--seed-code", codes[0],
            "--registry", str(registry), "--out-dir", str(out)]
    assert main(argv + ["--plan-only"]) == 0 and not out.exists()
    assert json.loads(capsys.readouterr().out)["requests_planned"] == 26
    def interrupt(url):
        raise KeyboardInterrupt
    with pytest.raises(KeyboardInterrupt):
        acquire(meta, seed, registry, codes[0], out, fetch=interrupt)
    assert json.loads((out / "run.json").read_text())["phase"] == "interrupted"


def test_query_keeps_real_dimensions_and_latest_period_semantics():
    assert source_url("001007").endswith("A.001007.NPHH_AV..ALL.ALL.ALL.TOT.ALL.ALL?dimensionAtObservation=TIME_PERIOD&lastNObservations=1")


def test_decimal_precision_and_duplicate_observation_fields(inputs):
    from decimal import Decimal
    profile = metadata_profile(inputs[0].read_bytes())
    code = inputs[3][0]
    exact = "0.123456789012345678901234567890123456789"
    report = inspect_response(response(code, values={"ALL": exact, "OWN": exact, "RENT": "0", "OTH_OR": "0"}), code, profile)
    assert Decimal(report["partition_difference_as_received"]) == 0
    root = ET.fromstring(response(code))
    obs = root.find(".//g:Obs", NS)
    obs.append(obs.find("g:ObsValue", NS))
    with pytest.raises(ValueError, match="Repeated observation"):
        inspect_response(ET.tostring(root), code, profile)


def test_audit_cli_and_methodology_dispatch_preserve_prior_report(inputs, tmp_path, capsys):
    meta, seed, registry, codes = inputs
    report = tmp_path / "review.json"
    argv = ["--xml", str(seed), "--metadata", str(meta), "--istat-code", codes[0], "--json-out", str(report)]
    assert methodology_main(["tenure-review", *argv]) == 0
    before = report.read_bytes()
    with pytest.raises(SystemExit) as error:
        review_main(argv)
    assert error.value.code == 2 and report.read_bytes() == before
    assert methodology_main(["tenure-acquire", "--metadata", str(meta), "--seed", str(seed),
                             "--seed-code", codes[0], "--registry", str(registry),
                             "--out-dir", str(tmp_path / "unused"), "--plan-only"]) == 0


def test_selective_followup_fetches_only_failed_code_and_keeps_previous_evidence(inputs, tmp_path):
    meta, seed, registry, codes = inputs
    failed = codes[14]
    def initial_fetch(url):
        code = url.split("/A.")[1].split(".")[0]
        if code == failed:
            return None, None, "TimeoutError"
        return 200, response(code, values={"RENT": "2.500002"} if code == codes[5] else None), None
    first = tmp_path / "partial"
    assert acquire(meta, seed, registry, codes[0], first, fetch=initial_fetch, wait=lambda _: None)["source_snapshots_reviewed"] == 26
    before = {p.relative_to(first): p.read_bytes() for p in first.rglob("*") if p.is_file()}
    requests = []
    def followup(url):
        requests.append(url)
        assert url == source_url(failed)
        return 200, response(failed), None
    result = acquire(meta, seed, registry, codes[0], tmp_path / "complete", reuse_run=first,
                     fetch=followup, wait=lambda _: pytest.fail("one query needs no intra-run wait"))
    assert len(requests) == result["requests_made"] == 1
    assert result["reused_snapshots"] == 26 and result["source_snapshots_reviewed"] == 27
    assert result["review_issue_codes"] == [codes[5]]
    assert all((first / relative).read_bytes() == raw for relative, raw in before.items())


@pytest.mark.parametrize("problem", ["active", "tampered", "registry_changed"])
def test_reuse_refuses_unstable_or_changed_provenance_before_network(inputs, tmp_path, problem):
    meta, seed, registry, codes = inputs
    first = tmp_path / "original"
    acquire(meta, seed, registry, codes[0], first,
            fetch=lambda url: (200, response(url.split("/A.")[1].split(".")[0]), None), wait=lambda _: None)
    if problem == "active":
        receipt = json.loads((first / "run.json").read_text())
        receipt["phase"] = "running"
        (first / "run.json").write_text(json.dumps(receipt))
    elif problem == "tampered":
        (first / "raw" / (codes[1] + ".xml")).write_bytes(b"changed evidence")
    else:
        registry.write_bytes(registry.read_bytes() + b"\n")
    out = tmp_path / "must-not-exist"
    with pytest.raises(ValueError):
        acquire(meta, seed, registry, codes[0], out, reuse_run=first, fetch=lambda _: pytest.fail("no network"))
    assert not out.exists()


def test_reusing_complete_run_requires_no_new_queries(inputs, tmp_path):
    meta, seed, registry, codes = inputs
    first = tmp_path / "original"
    acquire(meta, seed, registry, codes[0], first,
            fetch=lambda url: (200, response(url.split("/A.")[1].split(".")[0]), None), wait=lambda _: None)
    result = acquire(meta, seed, registry, codes[0], tmp_path / "copy", reuse_run=first,
                     fetch=lambda _: pytest.fail("no queries needed"), wait=lambda _: pytest.fail("no waiting needed"))
    assert result["requests_made"] == 0 and result["reused_snapshots"] == 27
