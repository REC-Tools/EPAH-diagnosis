"""Synthetic source composition, preserved versions and hostile-pack regressions."""
import json
from pathlib import Path
import stat

import pytest

from test_atc_source_review_v0_5 import ROW, html
from test_tenure_intake_v0_5 import inputs, response
from test_tenure_review_portal_v0_5 import source
from epah_diagnosis.methodology_v0_5 import main
from epah_diagnosis.source_review_hub_v0_5 import build_hub, decode, digest, encode, tree
from epah_diagnosis.source_review_hub_audit_v0_5 import audit_hub, Page
from epah_diagnosis.tenure_intake_v0_5 import acquire
from epah_diagnosis.utci_export_review_v0_5 import create_example


@pytest.fixture
def local_sources(source, tmp_path):
    run, notes = source
    root = tmp_path / "atc"
    root.mkdir()
    (root / "table.html").write_bytes(html([ROW, ROW]) + b"<!--><script src='https://example.invalid/x.js'></script>-->")
    index = root / "index.json"
    index.write_bytes(encode({"provider": "Ente sintetico", "entries": [
        {"istat_code": "001001", "source_selector": "COMUNE <img src=x onerror=alert(1)>",
         "file": "table.html", "reference_date": None, "acquired_on": "2026-11-19",
         "source_url": "https://example.invalid/public-table"}]}))
    nc = create_example(tmp_path / "climate") / "synthetic.nc"
    return dict(registry=run / "inputs/registry.csv", tenure_run=run, notes=notes,
                utci_source=nc, utci_field="example_days", atc_index=index, synthetic=True)


def rehash(pack):
    manifest = decode((pack / "manifest.json").read_bytes())
    manifest["files_sha256"] = {n: digest(raw) for n, raw in tree(pack).items() if n != "manifest.json"}
    (pack / "manifest.json").write_bytes(encode(manifest))


def test_portable_real_adapters_preserve_decimals_dates_duplicates_and_offline_links(local_sources, tmp_path):
    options = local_sources
    before = {p: p.read_bytes() for key, p in options.items() if isinstance(p, Path) and p.is_file()}
    before_run = tree(options["tenure_run"])
    out = build_hub(out_dir=tmp_path / "hub", **options)
    snapshot = decode((out / "snapshot.json").read_bytes())
    rows = snapshot["municipalities"]
    assert len(rows) == 27 and rows[0]["tenure"]["values"]["RENT"] == "2.500001"
    assert rows[0]["tenure"]["periods"] == ["2021"]
    assert rows[2]["tenure"]["partition_difference"] == "-0.000001"
    assert rows[0]["atc"]["audit"]["identical_row_groups"] == [[1, 2]]
    assert rows[0]["atc"]["reference_date"] is None and rows[1]["atc"] is None
    assert all(r["utci_municipal_state"] == "not_aggregated" for r in rows)
    assert snapshot["utci"]["selected_values"]["masked"] == 1
    assert not snapshot["indicator_calculated"] and not snapshot["weights_applied"]
    assert snapshot["municipal_series_added"] == 0
    assert audit_hub(out)["scientific_approval"] is False
    raw = (out / "index.html").read_bytes()
    page = Page(raw)
    assert len(page.rows) == 28
    assert "script" not in raw.decode().replace("&lt;script", "")  # Hostile original is text only.
    assert b"&lt;img" in raw and b"2.500001" in raw
    assert all((out / link).is_file() for link in page.links)
    assert all(not link.endswith(".html") for link in page.links)
    assert (out / "sources/atc/001001.html.txt").read_bytes() == (options["atc_index"].parent / "table.html").read_bytes()
    assert all(p.read_bytes() == raw for p, raw in before.items())
    assert tree(options["tenure_run"]) == before_run
    second = build_hub(out_dir=tmp_path / "identical", **options)
    assert tree(out) == tree(second)


def test_comparison_replays_both_versions_and_separates_value_period_and_byte_changes(local_sources, inputs, tmp_path):
    first = build_hub(out_dir=tmp_path / "first", **local_sources)
    frozen = tree(first)
    meta, seed, registry, codes = inputs
    seed.write_bytes(response(codes[0], values={"RENT": "2.700001", "ALL": "10.200000"}, periods={k: "2023" for k in ("ALL", "RENT", "OWN", "OTH_OR")}))
    run = tmp_path / "new-run"
    acquire(meta, seed, registry, codes[0], run,
            fetch=lambda url: (200, response(url.split("/A.")[1].split(".")[0]), None), wait=lambda _: None)
    options = {**local_sources, "tenure_run": run}
    index = options["atc_index"]
    content = decode(index.read_bytes())
    content["entries"][0]["reference_date"] = "2025-12-31"
    index.write_bytes(encode(content))
    # A changed file alone must not be mistaken for a changed stock value.
    table = index.parent / "table.html"
    table.write_bytes(table.read_bytes() + b"\n")
    second = build_hub(out_dir=tmp_path / "second", previous=first, **options)
    assert audit_hub(second)["comparison_replayed"] is True
    comparison = decode((second / "comparison.json").read_bytes())
    fields = {c["field"]: c for c in comparison["municipalities"][0]["changes"]}
    assert fields["tenure.values.RENT"]["before"] == "2.500001"
    assert fields["tenure.values.RENT"]["after"] == "2.700001"
    assert fields["tenure.periods"]["before"] == ["2021"] and fields["tenure.periods"]["after"] == ["2023"]
    assert fields["atc.reference_date"]["before"] is None
    assert fields["atc.reference_date"]["after"] == "2025-12-31"
    assert "atc.audit.table_rows" not in fields
    assert any(c["field"] == "sources/atc/001001.html.txt" for c in comparison["source_file_changes"])
    assert tree(first) == frozen
    assert (second / "baseline/sources/atc/001001.html.txt").read_bytes() == frozen["sources/atc/001001.html.txt"]
    third = build_hub(out_dir=tmp_path / "third", previous=second, **options)
    assert not (third / "baseline/baseline").exists()  # Bounded archives, not recursive history cloning.
    assert audit_hub(third)["comparison_replayed"]


@pytest.mark.parametrize("tamper", ["snapshot", "source", "comparison", "html_value", "html_script", "html_comment", "html_css", "html_charset", "extra", "baseline"])
def test_rehashed_tampering_is_rejected_by_replay_and_independent_html_checks(local_sources, tmp_path, tamper):
    original = build_hub(out_dir=tmp_path / "original", **local_sources)
    pack = build_hub(out_dir=tmp_path / "compared", previous=original, **local_sources)
    if tamper == "snapshot":
        path = pack / "snapshot.json"
        value = decode(path.read_bytes())
        value["municipalities"][0]["tenure"]["values"]["RENT"] = "999"
        path.write_bytes(encode(value))
    elif tamper == "source":
        path = pack / "sources/tenure/raw/001001.xml"
        path.write_bytes(path.read_bytes().replace(b"2.500001", b"2.700001"))
    elif tamper == "comparison":
        (pack / "comparison.json").write_bytes(b"null")
    elif tamper == "baseline":
        path = pack / "baseline/snapshot.json"
        path.write_bytes(path.read_bytes().replace(b'"2021"', b'"2025"'))
    elif tamper == "extra":
        (pack / "unreviewed.txt").write_text("extra")
    else:
        path = pack / "index.html"
        raw = path.read_text(encoding="utf-8")
        if tamper == "html_value":
            raw = raw.replace("RENT: 2.500001", "RENT: 9.500001", 1)
        elif tamper == "html_css":
            raw = raw.replace("<style>", "<style>@import url(https://example.invalid/x.css);")
        elif tamper == "html_comment":
            raw += "<!--><script src='https://example.invalid/x.js'></script>-->"
        elif tamper == "html_charset":
            raw = raw.replace('charset="utf-8"', 'charset="windows-1251"')
        else:
            raw += "<script>alert(1)</script>"
        path.write_text(raw, encoding="utf-8")
    rehash(pack)
    with pytest.raises(ValueError):
        audit_hub(pack)
    destination = tmp_path / "blocked"
    with pytest.raises(ValueError):
        build_hub(out_dir=destination, previous=pack, **local_sources)
    assert not destination.exists()


def test_gap_added_source_and_empty_table_never_become_zero_stock_or_climate_coverage(local_sources, tmp_path):
    options = local_sources
    empty = build_hub(options["registry"], tmp_path / "empty", synthetic=True)
    first = decode((empty / "snapshot.json").read_bytes())
    assert all(r["tenure"] is None and r["atc"] is None and r["utci_municipal_state"] == "source_not_included" for r in first["municipalities"])
    added = build_hub(out_dir=tmp_path / "added", previous=empty, **options)
    c = decode((added / "comparison.json").read_bytes())
    assert c["municipalities"][0]["changes"] and c["utci_changes"]
    assert audit_hub(added)["comparison_replayed"]
    assert main(["source-portal", "--example", "--out-dir", str(tmp_path / "example")]) == 0
    assert main(["source-audit", "--pack", str(tmp_path / "example")]) == 0
    example = decode((tmp_path / "example/snapshot.json").read_bytes())
    assert example["municipalities"][0]["atc"]["audit"]["table_rows"] == 0
    assert example["municipalities"][0]["atc"]["audit"]["stock_totals_calculated"] is False


@pytest.mark.parametrize("change", ["duplicate_code", "traversal", "bad_date", "second_provider", "unknown_code"])
def test_atc_association_contract_refuses_ambiguous_or_unsafe_inputs(local_sources, tmp_path, change):
    index = local_sources["atc_index"]
    content = decode(index.read_bytes())
    entry = content["entries"][0]
    if change == "duplicate_code":
        content["entries"].append(dict(entry))
    elif change == "traversal":
        entry["file"] = "../table.html"
    elif change == "bad_date":
        entry["reference_date"] = "2025"
    elif change == "second_provider":
        entry["provider"] = "Another provider"
    else:
        entry["istat_code"] = "999999"
    index.write_bytes(encode(content))
    with pytest.raises(ValueError):
        build_hub(out_dir=tmp_path / "blocked", **local_sources)
    assert not (tmp_path / "blocked").exists()


def test_fresh_destinations_provider_boundaries_and_failed_publication_preserve_evidence(local_sources, tmp_path, monkeypatch):
    original = build_hub(out_dir=tmp_path / "first", **local_sources)
    frozen = tree(original)
    with pytest.raises(FileExistsError):
        build_hub(out_dir=original, **local_sources)
    with pytest.raises(ValueError):
        build_hub(out_dir=local_sources["tenure_run"] / "nested", **local_sources)
    index = local_sources["atc_index"]
    content = decode(index.read_bytes())
    content["provider"] = "Different entity"
    index.write_bytes(encode(content))
    with pytest.raises(ValueError, match="provider"):
        build_hub(out_dir=tmp_path / "wrong-provider", previous=original, **local_sources)
    import epah_diagnosis.source_review_hub_v0_5 as service
    def fail(*args):
        raise OSError("Synthetic publication failure")
    monkeypatch.setattr(service, "publish_directory", fail)
    with pytest.raises(OSError):
        build_hub(out_dir=tmp_path / "failed", **local_sources)
    assert not (tmp_path / "failed").exists() and not list(tmp_path.glob(".source-hub-*"))
    assert tree(original) == frozen


def test_windows_reparse_directory_is_rejected_before_traversal(tmp_path, monkeypatch):
    root = tmp_path / "linked"
    root.mkdir()
    actual = Path.lstat
    class Reparse:
        st_file_attributes = stat.FILE_ATTRIBUTE_REPARSE_POINT
        st_mode = stat.S_IFDIR
    monkeypatch.setattr(Path, "lstat", lambda path: Reparse() if path == root else actual(path))
    with pytest.raises(ValueError, match="junctions"):
        tree(root)
