import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path

import pytest

from test_tenure_intake_v0_5 import inputs, response
from epah_diagnosis.methodology_v0_5 import main
from epah_diagnosis.tenure_intake_v0_5 import acquire
from epah_diagnosis.tenure_review_portal_v0_5 import build_portal


class Elements(HTMLParser):
    def __init__(self):
        super().__init__()
        self.elements = []
    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))


@pytest.fixture
def source(inputs, tmp_path):
    meta, seed, registry, codes = inputs
    run = tmp_path / "source-run"
    def fetch(url):
        code = url.split("/A.")[1].split(".")[0]
        return 200, response(code, values={"RENT": "2.500002"} if code == codes[2] else None), None
    acquire(meta, seed, registry, codes[0], run, fetch=fetch, wait=lambda _: None)
    notes = tmp_path / "notes.md"
    notes.write_bytes(b"# Note del revisore\r\n\r\nFonte storica 2021, obiettivo 2025.\r\n\r\n<img src=x onerror=alert(1)>\r\n")
    return run, notes


def test_portable_portal_has_traceable_values_safe_notes_local_links_and_unchanged_inputs(source, tmp_path):
    run, notes = source
    before = {p.relative_to(run): p.read_bytes() for p in run.rglob("*") if p.is_file()}
    notes_before = notes.read_bytes()
    out = build_portal(run, notes, tmp_path / "portal")
    snapshot = json.loads((out / "snapshot.json").read_text(encoding="utf-8"))
    assert len(snapshot["municipalities"]) == 27
    assert snapshot["municipalities"][0]["values"]["RENT"] == "2.500001"
    assert snapshot["municipalities"][0]["periods"] == ["2021"]
    assert snapshot["target_analysis_year"] == 2025
    assert snapshot["indicator_calculated"] is snapshot["weights_applied"] is False
    assert snapshot["scientific_approval"] is snapshot["publication_allowed"] is False
    html = (out / "index.html").read_text(encoding="utf-8")
    assert "27/27" in html and "4 anni" in html and "2.500001" in html
    assert "&lt;img" in html and "senza tetto" in html
    assert "Totale e categorie differiscono" in html
    parser = Elements()
    parser.feed(html)
    assert not any(tag in {"img", "iframe"} for tag, _ in parser.elements)
    assert len([attrs for tag, attrs in parser.elements if tag == "tr" and "data-search" in attrs]) == 27
    for tag, attrs in parser.elements:
        assert not attrs.get("src")  # No remote scripts, fonts, images or runtime fetches.
        if "href" in attrs:
            path = attrs["href"]
            assert ":" not in path and not path.startswith("/")
            assert (out / path).is_file(), path
    manifest = json.loads((out / "manifest.json").read_text())
    for path, expected in manifest["files_sha256"].items():
        assert hashlib.sha256((out / path).read_bytes()).hexdigest() == expected
    assert manifest["review_notes_sha256"] == hashlib.sha256(notes_before).hexdigest()
    assert all((run / path).read_bytes() == raw for path, raw in before.items())
    assert notes.read_bytes() == notes_before
    other = build_portal(run, notes, tmp_path / "second")
    assert all((other / p.relative_to(out)).read_bytes() == p.read_bytes() for p in out.rglob("*") if p.is_file())


@pytest.mark.parametrize("tamper", ["raw", "review", "request_receipt", "metadata", "registry", "run"])
def test_portal_refuses_inconsistent_source_evidence_without_output(source, tmp_path, tamper):
    run, notes = source
    if tamper == "raw":
        target = run / "raw/001002.xml"
        target.write_bytes(target.read_bytes() + b" ")
    elif tamper == "review":
        target = run / "reviews/001002.json"
        data = json.loads(target.read_text())
        data["scientific_approval"] = True
        target.write_text(json.dumps(data))
    elif tamper == "request_receipt":
        target = run / "receipts/001002.json"
        target.write_text("{}")
    elif tamper in {"metadata", "registry"}:
        target = run / ("inputs/metadata.xml" if tamper == "metadata" else "inputs/registry.csv")
        target.write_bytes(target.read_bytes() + b"\n")
    else:
        target = run / "run.json"
        data = json.loads(target.read_text())
        data["records"][1]["state"] = "invented_state"
        target.write_text(json.dumps(data))
    out = tmp_path / "must-not-exist"
    with pytest.raises(ValueError):
        build_portal(run, notes, out)
    assert not out.exists()


@pytest.mark.parametrize("kind", ["file", "empty_directory", "nested"])
def test_portal_preserves_existing_destinations_and_original_run(source, tmp_path, kind):
    run, notes = source
    out = run / "nested" if kind == "nested" else tmp_path / "existing"
    if kind == "file":
        out.write_bytes(b"earlier evidence")
    elif kind == "empty_directory":
        out.mkdir()
    with pytest.raises((ValueError, FileExistsError)):
        build_portal(run, notes, out)
    if kind == "file":
        assert out.read_bytes() == b"earlier evidence"
    elif kind == "empty_directory":
        assert list(out.iterdir()) == []
    else:
        assert not out.exists()


def test_incomplete_run_shows_missingness_and_next_steps_without_zeros(inputs, tmp_path):
    meta, seed, registry, codes = inputs
    run = tmp_path / "partial"
    acquire(meta, seed, registry, codes[0], run, fetch=lambda _: (None, None, "TimeoutError"), wait=lambda _: None)
    notes = tmp_path / "notes.md"
    notes.write_text("Fonte storica da revisionare", encoding="utf-8")
    out = build_portal(run, notes, tmp_path / "portal")
    snapshot = json.loads((out / "snapshot.json").read_text())
    missing = snapshot["municipalities"][1:]
    assert all(row["values"] == {} and row["periods"] == [] for row in missing)
    html = (out / "index.html").read_text(encoding="utf-8")
    assert "1/27" in html and "Richiesta non riuscita" in html and "Codice non richiesto" in html
    assert "Non disponibile" in html and "Prossimo passo" in html and "UTCI" in html


def test_portal_command_and_failed_publication(source, tmp_path, monkeypatch):
    run, notes = source
    assert main(["tenure-portal", "--run-dir", str(run), "--notes", str(notes),
                 "--out-dir", str(tmp_path / "command")]) == 0
    import epah_diagnosis.tenure_review_portal_v0_5 as module
    def fail(stage, target):
        assert (stage / "index.html").is_file() and (stage / "manifest.json").is_file()
        raise OSError("synthetic publication failure")
    monkeypatch.setattr(module, "publish_directory", fail)
    with pytest.raises(OSError):
        build_portal(run, notes, tmp_path / "failed")
    assert not (tmp_path / "failed").exists()
    assert not list(tmp_path.glob(".tenure-portal-*"))
