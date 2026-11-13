"""Deterministic evidence view of the existing checked observation contract.

Digests declared by input receipts are not proof of original-source inspection.
The enclosing manifests bind this ledger to the exact atlas/review artifacts.
"""
from __future__ import annotations

from collections import Counter
from html import escape
import json

from epah_diagnosis.editorial_catalog_v0_4 import CANONICAL, CANDIDATES, snapshot

FILES = ("evidence_ledger.json", "evidence_ledger.html")
STATUS = "technical_draft_do_not_publish"


def derive(payload: dict, rows: list[dict], atlas_sha256: str,
           input_evidence: dict, candidate_receipts: dict) -> dict:
    metrics = payload["indicators"]
    snapshot(metrics)  # Validate any editorial labels rather than inferring them.
    if payload.get("schema_version") == "0.4-technical-atlas":
        if [m["id"] for m in metrics] != list(CANONICAL) + list(CANDIDATES):
            raise ValueError("Full v0.4 ledger requires exactly 16 indicator slots")
    expected = {(t["code"], m["id"]) for t in payload["municipalities"] for m in metrics}
    if (len(payload["municipalities"]) != 27 or len(expected) != 27 * len(metrics)
            or len(rows) != len(expected)
            or {(r["municipality_code"], r["indicator_id"]) for r in rows} != expected):
        raise ValueError("Evidence ledger observation coverage mismatch")
    indicators = []
    for metric in metrics:
        selected = [r for r in rows if r["indicator_id"] == metric["id"]]
        periods = sorted({r["reference_period"] for r in selected if r["reference_period"]})
        if periods != metric["years"]:
            raise ValueError("Evidence ledger reference period differs from atlas")
        editorial = metric.get("editorial") or {}
        observations = []
        for row in sorted(selected, key=lambda r: r["municipality_code"]):
            if (any(row[k] != metric.get(v, "") for k, v in (
                    ("source", "source"), ("indicator_name", "name"), ("unit", "unit"),
                    ("evidence_status", "evidence")))
                    or row["publication_allowed"] != "false"
                    or row["human_review_status"] != "not_approved"
                    or row.get("scientific_approval", "false") != "false"):
                raise ValueError("Evidence ledger source or technical status differs from atlas")
            missing = row["missing_reason"]
            if (missing not in ("", "not_acquired")
                    or bool(missing) != (not metric["available"])
                    or bool(row["value"] != "") == bool(missing)):
                raise ValueError("Evidence ledger missingness contradicts observation")
            observations.append({
                "municipality_code": row["municipality_code"],
                "reference_period": row["reference_period"] or None,
                "presence": "absent" if missing else "observed",
                "missing_reason": missing or None,
                "numerator": row["numerator"] or None,
                "denominator": row["denominator"] or None,
                "universe": row["universe"] or None,
                "counts_absence_reason": None if row["denominator"] else "not_preserved_in_verified_input",
            })
        indicators.append({
            "indicator_id": metric["id"], "title": metric["name"], "unit": metric["unit"],
            "role": editorial.get("role"),
            "population_reference": editorial.get("population_reference"),
            "editorial_absence_reason": None if editorial else "not_present_in_legacy_snapshot",
            "source": metric["source"], "reference_periods": periods,
            "evidence_status": metric["evidence"],
            "present_count": sum(o["presence"] == "observed" for o in observations),
            "missing_count": sum(o["presence"] == "absent" for o in observations),
            "missing_reasons": dict(sorted(Counter(
                o["missing_reason"] for o in observations if o["missing_reason"]).items())),
            "declared_input_evidence": input_evidence.get(metric["id"]) or None,
            "locally_verified_candidate_receipt": candidate_receipts.get(metric["id"]) or None,
            "original_artifact": None,
            "original_artifact_absence_reason": "not_inspected_by_ledger; consult declared input evidence",
            "observations": observations,
        })
    return {
        "schema_version": "0.4-evidence-ledger-1", "status": STATUS,
        "scientific_approval": False, "publication_allowed": False,
        "atlas_data_sha256": atlas_sha256, "municipalities": 27,
        "indicator_slots": len(metrics), "indicators": indicators,
        "declared_input_evidence": input_evidence,
        "limitations": [
            "Hash consistency is not source authenticity or scientific approval.",
            "Declared input digests are not locally verified original-source digests.",
            "not_acquired means absent from this snapshot, not unavailable at the source or not applicable.",
            "Editorial population descriptions never supply missing numeric denominators.",
            "Enclosing manifests bind the atlas manifest and any candidate integrity receipts; no circular hashes.",
        ],
    }


def html(ledger: dict) -> str:
    sections = []
    for item in ledger["indicators"]:
        lines = [
            ("Fonte dichiarata", item["source"]),
            ("Periodo", ", ".join(item["reference_periods"]) or "Non acquisito nello snapshot"),
            ("Universo editoriale", item["population_reference"] or "Non presente nello snapshot"),
            ("Ruolo", item["role"] or "Non presente nello snapshot"),
            ("Stato di evidenza tecnica", item["evidence_status"]),
            ("Copertura", f'{item["present_count"]}/27 presenti; {item["missing_count"]}/27 assenti'),
            ("Motivo di assenza", "Non acquisito nello snapshot (not_acquired)" if item["missing_count"] else "Nessuna assenza nello snapshot"),
        ]
        sections.append('<section><h2>' + escape(item["indicator_id"] + " | " + item["title"]) +
                        '</h2><dl>' + ''.join('<dt>' + escape(k) + '</dt><dd>' + escape(v) + '</dd>'
                                               for k, v in lines) + '</dl></section>')
    return ('<!doctype html><html lang="it"><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>Registro delle evidenze v0.4</title><style>'
            'body{font:1rem/1.5 system-ui;max-width:70rem;margin:auto;padding:1.5rem;color:#17354a}'
            'section{border-top:1px solid #ccd;padding:1rem 0}dt{font-weight:bold}dd{margin:0 0 .6rem;overflow-wrap:anywhere}'
            '</style><h1>Registro delle evidenze v0.4</h1>'
            '<p><strong>BOZZA TECNICA - NON PUBBLICARE.</strong> Nessuna approvazione scientifica.</p>'
            '<p>Non acquisito non significa zero, non disponibile alla fonte o non applicabile. '
            'I checksum dichiarati non certificano gli originali.</p>'
            '<p><a href="evidence_ledger.json">Registro completo JSON: ricevute e denominatori documentati per Comune</a></p>'
            + ''.join(sections) + '</html>')


def write(folder, ledger: dict) -> None:
    (folder / FILES[0]).write_text(json.dumps(ledger, ensure_ascii=False, indent=2,
                                            allow_nan=False) + "\n", encoding="utf-8")
    (folder / FILES[1]).write_text(html(ledger), encoding="utf-8")


def verify_artifacts(folder, hashes: dict) -> None:
    """Check declared local artifacts without following paths outside the snapshot."""
    import hashlib
    from pathlib import PurePosixPath

    if folder.is_symlink() or not isinstance(hashes, dict) or not hashes:
        raise ValueError("Invalid atlas integrity manifest")
    for name, digest in hashes.items():
        if (not isinstance(name, str) or not name or "\\" in name
                or PurePosixPath(name).is_absolute()
                or any(p in (".", "..") for p in name.split("/"))):
            raise ValueError("Unsafe path in atlas checksum manifest")
        path = folder / name
        if (not path.resolve().is_relative_to(folder.resolve())
                or any(p.is_symlink() for p in (path, *path.parents))
                or not path.is_file()
                or hashlib.sha256(path.read_bytes()).hexdigest() != digest):
            raise ValueError(f"Atlas output integrity mismatch (checksum): {name}")
