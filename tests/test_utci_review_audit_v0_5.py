"""Check transferred/tampered packs with an auditor independent of rendering."""
import json

import pytest

from epah_diagnosis import utci_review_audit_v0_5 as audit
from epah_diagnosis import utci_review_portal_v0_5 as portal
from epah_diagnosis.methodology_v0_5 import main as methodology_main
from epah_diagnosis.provenance import sha256_file
from epah_diagnosis.utci_export_review_v0_5 import create_example


@pytest.fixture
def pack(tmp_path):
    source = create_example(tmp_path / "input") / "synthetic.nc"
    return portal.build_portal(source, tmp_path / "pack", reference_year=2025, field="example_days", synthetic=True)


def snapshot(pack):
    return {p.relative_to(pack): p.read_bytes() for p in pack.rglob("*") if p.is_file()}


def rehash(pack, name):
    path = pack / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest["files_sha256"][name] = sha256_file(pack / name)
    path.write_text(json.dumps(manifest), encoding="utf-8")


def test_valid_pack_replays_without_rendering_or_changing_any_bytes(pack, monkeypatch):
    before = snapshot(pack)
    monkeypatch.setattr(portal, "render", lambda *a, **k: pytest.fail("auditor must not invoke renderer"))
    result = audit.audit_pack(pack)
    assert result["software_integrity_passed"] is True
    assert result["source_review_issues"] == ["selected_values_masked"]
    assert len(result["pack_files_sha256"]) == 4
    assert result["scientific_approval"] is result["publication_allowed"] is False
    assert result["visual_layout_verified"] is result["municipal_coverage_verified"] is False
    assert before == snapshot(pack)
    assert str(pack) not in json.dumps(result)


@pytest.mark.parametrize("problem", ["report_value", "report_boolean", "html_minimum", "html_missing", "html_year",
                                   "html_warning", "html_synthetic", "html_issues", "html_script"])
def test_rehashed_tampering_is_detected_by_replay_or_semantics(pack, problem):
    if problem.startswith("report"):
        path = pack / "review.json"
        report = json.loads(path.read_text())
        if problem == "report_value":
            report["selected_values"]["minimum"] = 999
        else:
            report["scientific_approval"] = 0  # Python equality alone treats this as False.
        path.write_text(json.dumps(report), encoding="utf-8")
        rehash(pack, "review.json")
    else:
        path = pack / "index.html"
        html = path.read_text(encoding="utf-8")
        old, new = {
            "html_minimum": ("Minimo numerico</th><td>0.0", "Minimo numerico</th><td>999"),
            "html_missing": ("Valori mascherati</th><td>1", "Valori mascherati</th><td>0"),
            "html_year": ("Anno richiesto al controllo</th><td>2025", "Anno richiesto al controllo</th><td>2030"),
            "html_warning": ("BOZZA TECNICA", "APPROVATO"),
            "html_synthetic": ("DATI SINTETICI · NON SONO DATI TERRITORIALI", "Fonte reale"),
            "html_issues": ("Questioni da revisionare (1)", "Questioni da revisionare (0)"),
            "html_script": ("</body>", "<script>alert(1)</script></body>"),
        }[problem]
        assert old in html
        path.write_text(html.replace(old, new), encoding="utf-8")
        rehash(pack, "index.html")
    before = snapshot(pack)
    with pytest.raises(ValueError):
        audit.audit_pack(pack)
    assert before == snapshot(pack)


@pytest.mark.parametrize("problem", ["duplicate_key", "nan", "approval", "extra_approval", "unknown_kind", "boolean_year", "path_traversal"])
def test_untrusted_manifest_contract_is_blocked_before_replay(pack, monkeypatch, problem):
    path = pack / "manifest.json"
    manifest = json.loads(path.read_text())
    if problem == "approval":
        manifest["publication_allowed"] = True
    elif problem == "extra_approval":
        manifest["approved_by"] = "invented authority"
    elif problem == "unknown_kind":
        manifest["input_kind"] = "certified_cds"
    elif problem == "boolean_year":
        manifest["reference_year"] = True
    elif problem == "path_traversal":
        manifest["files_sha256"]["../../outside.nc"] = manifest["files_sha256"].pop("source/original.nc")
    raw = json.dumps(manifest)
    if problem == "duplicate_key":
        raw = raw.replace('"reference_year": 2025', '"reference_year": 2025, "reference_year": 2026')
    elif problem == "nan":
        raw = raw.replace('"reference_year": 2025', '"reference_year": NaN')
    path.write_text(raw, encoding="utf-8")
    monkeypatch.setattr(audit, "inspect_export", lambda *a, **k: pytest.fail("invalid manifest must block before source replay"))
    with pytest.raises(ValueError):
        audit.audit_pack(pack)


@pytest.mark.parametrize("problem", ["missing", "extra", "checksum"])
def test_incomplete_or_changed_files_are_not_accepted(pack, problem):
    if problem == "missing":
        (pack / "review.json").unlink()
    elif problem == "extra":
        (pack / "reviewer-notes.txt").write_text("Keep review notes outside the baseline")
    else:
        (pack / "index.html").write_text("changed")
    with pytest.raises(ValueError):
        audit.audit_pack(pack)


def test_matching_hash_does_not_allow_symlink_member(pack, tmp_path, symlink_support):
    outside = tmp_path / "outside.html"
    outside.write_bytes((pack / "index.html").read_bytes())
    (pack / "index.html").unlink()
    (pack / "index.html").symlink_to(outside)
    with pytest.raises(ValueError, match="symbolic"):
        audit.audit_pack(pack)


def test_change_during_replay_is_rejected_even_if_html_remains_semantically_equal(pack, monkeypatch):
    real_inspect = audit.inspect_export
    def changing(*args, **kwargs):
        result = real_inspect(*args, **kwargs)
        with (pack / "index.html").open("a", encoding="utf-8") as f:
            f.write("\n")
        return result
    monkeypatch.setattr(audit, "inspect_export", changing)
    with pytest.raises(ValueError, match="changed during"):
        audit.audit_pack(pack)


def test_cli_receipts_are_fresh_external_and_keep_source_issues_open(pack, tmp_path, capsys):
    out = tmp_path / "receipts" / "audit.json"
    args = ["utci-audit", "--pack", str(pack), "--json-out", str(out)]
    before = snapshot(pack)
    assert methodology_main(args) == 0
    result = json.loads(out.read_text())
    assert result["software_integrity_passed"] and result["source_review_issues"]
    assert "COERENTE" in capsys.readouterr().out
    saved = out.read_bytes()
    with pytest.raises(SystemExit) as exc:
        methodology_main(args)
    assert exc.value.code == 2 and out.read_bytes() == saved
    with pytest.raises(SystemExit):
        audit.main(["--pack", str(pack), "--json-out", str(pack / "audit.json")])
    assert before == snapshot(pack)
    (pack / "index.html").write_bytes(b"changed")
    blocked = tmp_path / "blocked.json"
    assert audit.main(["--pack", str(pack), "--json-out", str(blocked)]) == 2
    assert json.loads(blocked.read_text())["software_integrity_passed"] is False
    assert not (pack / "audit.json").exists()
