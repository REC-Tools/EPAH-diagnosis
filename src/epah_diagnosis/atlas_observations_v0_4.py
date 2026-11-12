"""Validated technical-only long-format export from a v0.3 atlas snapshot.

Only displayed values and periods exist in the atlas; original numerators,
denominators and source precision cannot be reconstructed.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import tempfile
from pathlib import Path

from epah_diagnosis.candidate_observations_v0_4 import enrich

STATUS = "technical_draft_do_not_publish"
COLUMNS = (
    "municipality_code", "municipality", "indicator_id", "indicator_name",
    "family", "reference_period", "value", "unit", "source",
    "evidence_status", "source_preview_sha256", "numerator", "denominator",
    "universe", "geography_version", "missing_reason",
    "human_review_status", "publication_allowed",
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _registry(path: Path) -> dict[str, str]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or not {"municipality", "istat_code"} <= set(reader.fieldnames):
            raise ValueError("Invalid municipality registry headers")
        rows = list(reader)
    result = {r["istat_code"]: r["municipality"] for r in rows}
    if (len(rows) != 27 or len(result) != 27
            or any(len(k) != 6 or not k.isascii() or not k.isdigit() or not v.strip()
                   for k, v in result.items())):
        raise ValueError("Registry must contain 27 unique municipality codes")
    return result


def build(atlas_dir: Path, registry: Path, out_dir: Path, *,
          candidate_previews: dict[str, Path] | None = None) -> Path:
    if out_dir.exists():
        raise FileExistsError("Choose a fresh output directory; no overwrite is permitted")
    if out_dir.resolve().is_relative_to(atlas_dir.resolve()):
        raise ValueError("Outputs may not be written inside the atlas input")
    atlas_file, manifest_file = atlas_dir / "atlas_data.json", atlas_dir / "atlas_manifest.json"
    data = json.loads(atlas_file.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    names = _registry(registry)
    if (data.get("status") != STATUS or manifest.get("status") != STATUS
            or data.get("publication_allowed") is not False
            or manifest.get("publication_allowed") is not False
            or data.get("no_composite_score") is not True
            or manifest.get("registry_sha256") != _sha(registry)
            or manifest.get("output_sha256", {}).get("atlas_data.json") != _sha(atlas_file)):
        raise ValueError("Atlas status, municipality registry, or source checksum mismatch")
    municipalities = data.get("municipalities")
    metrics = data.get("indicators")
    if not isinstance(municipalities, list) or not isinstance(metrics, list):
        raise ValueError("Atlas schema is incomplete")
    towns = {r["code"]: r for r in municipalities}
    if (len(municipalities) != 27 or set(towns) != set(names)
            or any(r.get("name") != names.get(r.get("code")) or not isinstance(r.get("values"), dict)
                   for r in municipalities)):
        raise ValueError("Atlas municipality names or codes differ from registry")
    ids = [m["id"] for m in metrics]
    if (len(ids) != len(set(ids)) or not ids
            or data.get("municipality_count") != 27
            or manifest.get("municipalities") != 27
            or manifest.get("indicator_slots") != len(ids)):
        raise ValueError("Atlas indicator inventory or coverage mismatch")
    if any(set(r["values"]) - set(ids) for r in municipalities):
        raise ValueError("Unexpected observation outside atlas indicator inventory")
    available = [m["id"] for m in metrics if m.get("available") is True]
    pending = [m["id"] for m in metrics if m.get("available") is False]
    if (len(available) + len(pending) != len(ids)
            or manifest.get("indicators_available") != available
            or manifest.get("indicators_pending") != pending):
        raise ValueError("Atlas available/pending inventory mismatch")

    candidate_previews = candidate_previews or {}
    enriched, candidate_receipts = {}, {}
    if any(key not in {"H46", "H47", "H50"} or key not in available
           for key in candidate_previews):
        raise ValueError("Candidate previews must match available H46/H47/H50 atlas slots")
    for key, location in sorted(candidate_previews.items()):
        enriched[key], candidate_receipts[key] = enrich(
            key, location, names, _sha(registry),
            manifest.get("input_evidence", {}).get(key), towns)

    rows, summary = [], []
    for metric in metrics:
        mid = metric["id"]
        is_available = metric["available"]
        found = [towns[code]["values"].get(mid) for code in sorted(names)]
        if (sum(x is not None for x in found) != (27 if is_available else 0)
                or metric.get("count") != (27 if is_available else 0)
                or not isinstance(metric.get("years"), list)):
            raise ValueError(f"{mid}: incomplete or incorrectly labelled coverage")
        periods = set()
        evidence = manifest.get("input_evidence", {}).get(mid, {})
        digest = evidence.get("preview_sha256", "") if isinstance(evidence, dict) else ""
        if digest and (len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest)):
            raise ValueError(f"{mid}: invalid source digest")
        for code, observation in zip(sorted(names), found):
            period, value = "", ""
            if observation is not None:
                if not isinstance(observation, dict):
                    raise ValueError(f"{mid}/{code}: invalid observation")
                raw, period = observation.get("value"), observation.get("year")
                if not isinstance(period, str) or not period.strip():
                    raise ValueError(f"{mid}/{code}: period is missing")
                periods.add(period)
                if metric.get("unit") == "categoria":
                    if not isinstance(raw, str) or not raw.strip():
                        raise ValueError(f"{mid}/{code}: invalid category")
                    value = raw
                else:
                    if (isinstance(raw, bool) or not isinstance(raw, (int, float))
                            or not math.isfinite(raw) or raw < 0
                            or metric.get("unit") == "%" and raw > 100):
                        raise ValueError(f"{mid}/{code}: invalid numeric value")
                    value = repr(raw)
            candidate = enriched.get(mid, {}).get(code, {})
            rows.append({
                "municipality_code": code, "municipality": names[code],
                "indicator_id": mid, "indicator_name": metric.get("name", ""),
                "family": metric.get("family", ""), "reference_period": period,
                "value": candidate.get("value", value), "unit": metric.get("unit", ""),
                "source": metric.get("source", ""), "evidence_status": metric.get("evidence", ""),
                "source_preview_sha256": digest,
                "numerator": candidate.get("numerator", ""),
                "denominator": candidate.get("denominator", ""),
                "universe": candidate.get("universe", ""), "geography_version": "",
                "missing_reason": "" if is_available else "not_acquired",
                "human_review_status": "not_approved", "publication_allowed": "false",
            })
        if sorted(periods) != metric["years"]:
            raise ValueError(f"{mid}: reference-period metadata mismatch")
        if is_available and not metric.get("evidence", "").startswith("technical_"):
            raise ValueError(f"{mid}: missing technical evidence status")
        if not is_available and metric.get("evidence") != "not_available":
            raise ValueError(f"{mid}: pending metric must be marked not available")
        summary.append({"indicator_id": mid, "available": is_available,
                        "municipalities": 27 if is_available else 0,
                        "reference_periods": sorted(periods)})
    out_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".epah-v04-obs-", dir=out_dir.parent) as temporary:
        stage = Path(temporary) / "observations"
        stage.mkdir()
        with (stage / "observations.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
        metadata = {
            "schema_version": "0.4-technical-preview", "status": STATUS,
            "publication_allowed": False, "scientific_approval": False,
            "observations": len(rows), "municipalities": 27, "indicators": summary,
            "enriched_candidates": sorted(enriched),
            "source_model": "v0.3 atlas snapshot, not original source tables",
            "not_preserved_without_source_preview": ["numerator", "denominator", "universe"],
            "not_preserved_in_source": [
                "geography_version",
                "original_decimal_precision", "individual_source_audit",
            ],
            "missingness": "not_acquired means absent from atlas; no suppression inference",
        }
        (stage / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        receipt = {
            "schema_version": "0.4-technical-preview", "status": STATUS,
            "publication_allowed": False, "scientific_approval": False,
            "inputs_sha256": {
                "atlas_data.json": _sha(atlas_file), "atlas_manifest.json": _sha(manifest_file),
                "municipalities.csv": _sha(registry),
            },
            "candidate_preview_integrity_receipts": candidate_receipts,
            "outputs_sha256": {p.name: _sha(p) for p in stage.iterdir() if p.is_file()},
        }
        (stage / "manifest.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        if out_dir.exists():
            raise FileExistsError("Output was created concurrently")
        os.replace(stage, out_dir)
    return out_dir
