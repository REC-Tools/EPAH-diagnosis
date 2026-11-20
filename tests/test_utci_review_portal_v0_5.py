"""Synthetic source-to-HTML regressions, independent of authenticated CDS access."""
from html.parser import HTMLParser
import json

from netCDF4 import Dataset
import pytest

from epah_diagnosis import utci_review_portal_v0_5 as portal
from epah_diagnosis.methodology_v0_5 import main as methodology_main
from epah_diagnosis.provenance import sha256_file
from epah_diagnosis.utci_export_review_v0_5 import create_example, inspect_export


@pytest.fixture
def source(tmp_path):
    folder = create_example(tmp_path / "fixture")
    return folder / "synthetic.nc"


class Page(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.links, self.ids, self.tags, self.attributes = [], [], [], []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        self.attributes.extend(attrs)
        values = dict(attrs)
        if "href" in values:
            self.links.append(values["href"])
        if "id" in values:
            self.ids.append(values["id"])


def build(source, destination, **kwargs):
    return portal.build_portal(source, destination, reference_year=kwargs.pop("reference_year", 2025),
                               field=kwargs.pop("field", "example_days"), **kwargs)


def test_source_report_manifest_and_html_form_one_replayable_pack(source, tmp_path):
    before = source.read_bytes()
    out = build(source, tmp_path / "new-parent" / "portal", synthetic=True)
    assert source.read_bytes() == (out / "source/original.nc").read_bytes() == before
    report = json.loads((out / "review.json").read_text())
    assert report == inspect_export(out / "source/original.nc", reference_year=2025, field="example_days")
    assert report["selected_values"]["masked"] == report["selected_values"]["zero"] == 1
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["input_kind"] == "synthetic_declared"
    assert manifest["source_sha256"] == sha256_file(source)
    assert set(manifest["files_sha256"]) == {"source/original.nc", "review.json", "index.html"}
    for name, digest in manifest["files_sha256"].items():
        assert sha256_file(out / name) == digest
    html = (out / "index.html").read_text(encoding="utf-8")
    page = Page(html)
    assert set(page.links) == {"source/original.nc", "review.json", "manifest.json"}
    assert all((out / link).is_file() for link in page.links)
    assert len(page.ids) == len(set(page.ids))
    assert "script" not in page.tags and "iframe" not in page.tags
    assert not any(name == "src" or name.startswith("on") for name, _ in page.attributes)
    assert "DATI SINTETICI" in html and "NON SONO DATI TERRITORIALI" in html
    assert "technical_draft_do_not_publish" in html
    assert "selected_values_masked" in html and report["source_sha256"] in html
    for name in ("index.html", "review.json", "manifest.json"):
        assert str(source) not in (out / name).read_text(encoding="utf-8")


def test_actual_export_gaps_and_period_are_presented_without_inference(source, tmp_path):
    with Dataset(source, "r+") as ds:
        ds.variables["example_days"].delncattr("units")
        ds.variables["time"].units = "hours since 2025-1-1 00:00:00"
        ds.variables["time"][:] = [4379.5]
        ds.variables["time_bnds"][:] = [[0, 8759]]
    out = build(source, tmp_path / "portal")
    report = json.loads((out / "review.json").read_text())
    html = (out / "index.html").read_text(encoding="utf-8")
    assert "day_units_not_explicit" in html and "time_bounds_require_interpretation" in html
    assert "2025-12-31 23:00:00" in html and "Non dichiarato / non disponibile" in html
    assert "Fonte locale da verificare" in html and "DATI SINTETICI" not in html
    assert "units" not in report["variables"]["example_days"]["attributes"]
    assert report["time"]["decoded_bounds"][1] == "2025-12-31 23:00:00"
    assert json.loads((out / "manifest.json").read_text())["input_kind"] == "unclassified_local_source"


def test_clean_structure_never_becomes_scientific_or_municipal_approval(source, tmp_path):
    with Dataset(source, "r+") as ds:
        ds.variables["example_days"][:] = [[[0, 365], [120, 10]]]
    out = build(source, tmp_path / "portal")
    report = json.loads((out / "review.json").read_text())
    assert report["issues"] == []
    for key in ("scientific_approval", "publication_allowed", "municipal_coverage_verified",
                "daily_completeness_verified", "threshold_semantics_verified", "aggregation_performed"):
        assert report[key] is False
    html = (out / "index.html").read_text(encoding="utf-8")
    assert "Nessuna anomalia nei controlli strutturali" in html
    assert "copertura comunale: da verificare" in html


def test_untrusted_metadata_is_escaped_not_executable(source, tmp_path):
    attack = '<script>alert("source")</script><img src=x onerror=alert(1)>'
    with Dataset(source, "r+") as ds:
        ds.variables["example_days"].long_name = attack
    out = build(source, tmp_path / "portal")
    html = (out / "index.html").read_text(encoding="utf-8")
    assert "&lt;script&gt;" in html and "&lt;img" in html
    assert "script" not in Page(html).tags and "img" not in Page(html).tags
    assert json.loads((out / "review.json").read_text())["variables"]["example_days"]["attributes"]["long_name"] == attack


def test_two_builds_from_same_input_are_identical(source, tmp_path):
    first = build(source, tmp_path / "first", synthetic=True)
    second = build(source, tmp_path / "second", synthetic=True)
    assert {p.relative_to(first): p.read_bytes() for p in first.rglob("*") if p.is_file()} == {
        p.relative_to(second): p.read_bytes() for p in second.rglob("*") if p.is_file()}


@pytest.mark.parametrize("failure", ["render", "copy", "source_changed"])
def test_failed_build_never_publishes_partial_pack_or_changes_neighbour(source, tmp_path, monkeypatch, failure):
    original = source.read_bytes()
    neighbour = tmp_path / "keep.txt"
    neighbour.write_bytes(b"earlier evidence")
    if failure == "render":
        def fail(*args, **kwargs):
            raise RuntimeError("synthetic render failure")
        monkeypatch.setattr(portal, "render", fail)
    elif failure == "copy":
        monkeypatch.setattr(portal.shutil, "copyfile", lambda src, dst: dst.write_bytes(b"incomplete copy"))
    else:
        real_hash = portal.sha256_file
        monkeypatch.setattr(portal, "sha256_file", lambda path: "changed" if path == source else real_hash(path))
    destination = tmp_path / "blocked"
    with pytest.raises((RuntimeError, ValueError)):
        build(source, destination)
    assert not destination.exists()
    assert source.read_bytes() == original and neighbour.read_bytes() == b"earlier evidence"


def test_dispatcher_preserves_existing_output_and_blocks_invalid_field(source, tmp_path, capsys):
    destination = tmp_path / "portal"
    args = ["utci-portal", "--file", str(source), "--reference-year", "2025", "--field", "example_days",
            "--out-dir", str(destination), "--synthetic"]
    assert methodology_main(args) == 0
    before = {p.relative_to(destination): p.read_bytes() for p in destination.rglob("*") if p.is_file()}
    with pytest.raises(SystemExit) as exc:
        methodology_main(args)
    assert exc.value.code == 2 and "BLOCKED:" in capsys.readouterr().err
    assert before == {p.relative_to(destination): p.read_bytes() for p in destination.rglob("*") if p.is_file()}
    with pytest.raises(ValueError, match="numeric field"):
        build(source, tmp_path / "missing-field", field="absent")
    assert not (tmp_path / "missing-field").exists()


def test_requested_year_does_not_relabel_actual_source_time(source, tmp_path):
    out = build(source, tmp_path / "portal", reference_year=2026)
    report = json.loads((out / "review.json").read_text())
    assert report["reference_year"] == 2026
    assert report["time"]["decoded_bounds"][0] == "2025-01-01 00:00:00"
    assert "time_reference_year_mismatch" in report["issues"]
    html = (out / "index.html").read_text(encoding="utf-8")
    assert "time_reference_year_mismatch" in html and "2025-01-01" in html
