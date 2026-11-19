"""Bounded, sequential tenure-source intake; never calculate or approve indicators."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .cli import read_municipality_codes
from .tenure_source_review_v0_5 import DIMENSIONS, FLOW, SELECTION, check_run_receipt, inspect_response, metadata_profile

INTERVAL_SECONDS = 16
BASE = "https://esploradati.istat.it/SDMXWS/rest"


def source_url(code):
    selection = {**SELECTION, "REF_AREA": code, "TENURE_STATUS_HOU": ""}
    return (f"{BASE}/data/IT1,{FLOW},1.0/" + ".".join(selection[name] for name in DIMENSIONS)
            + "?dimensionAtObservation=TIME_PERIOD&lastNObservations=1")


def fetch_response(url):
    request = Request(url, headers={"Accept": "application/vnd.sdmx.genericdata+xml;version=2.1"})
    try:
        with urlopen(request, timeout=30) as response:
            return response.status, response.read(), None
    except HTTPError as exc:
        return exc.code, exc.read(), f"HTTP {exc.code}"
    except (TimeoutError, URLError, OSError) as exc:
        return None, None, f"{type(exc).__name__}: {exc}"


def _hash(raw):
    return hashlib.sha256(raw).hexdigest()


def _new_json(path, document):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(document, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def _update_run(path, document):
    # This run's receipt is the only evolving file; raw evidence is exclusive.
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", dir=path.parent,
                                     prefix=".tenure-receipt-", delete=False) as stream:
        temporary = Path(stream.name)
        json.dump(document, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def plan_inputs(metadata, seed, registry, seed_code, reuse_run=None):
    raw_metadata, raw_seed, raw_registry = metadata.read_bytes(), seed.read_bytes(), registry.read_bytes()
    profile = metadata_profile(raw_metadata)
    mapping = read_municipality_codes(registry)
    if len(mapping) != 27 or seed_code not in mapping.values() or not set(mapping.values()) <= profile["area_codes"]:
        raise ValueError("Require the 27 registry identities and a matching local pilot")
    seed_review = inspect_response(raw_seed, seed_code, profile)
    if seed_review["review_issues"]:
        raise ValueError("The reused pilot has unresolved source-quality issues")
    if registry.read_bytes() != raw_registry:
        raise ValueError("Registry changed during planning")
    inputs = {"metadata.xml": raw_metadata, "seed.xml": raw_seed, "registry.csv": raw_registry}
    reused = {seed_code: (raw_seed, seed_review)}
    if reuse_run is not None:
        receipt_raw = (reuse_run / "run.json").read_bytes()
        receipt = json.loads(receipt_raw.decode("utf-8"))
        records = check_run_receipt(receipt, _hash(raw_metadata), _hash(raw_registry), mapping.values())
        for record in records:
            code = record["istat_code"]
            if code == seed_code or record["state"] not in {"source_reviewed", "reused_source_reviewed"}:
                continue
            raw = (reuse_run / "raw" / f"{code}.xml").read_bytes()
            if _hash(raw) != record.get("response_sha256"):
                raise ValueError("Reused original checksum mismatch; preserve and review")
            reused[code] = (raw, inspect_response(raw, code, profile))
        inputs["reused-run.json"] = receipt_raw
    return profile, mapping, reused, inputs


def acquire(metadata: Path, seed: Path, registry: Path, seed_code: str, out_dir: Path,
            *, reuse_run: Path | None = None, fetch=fetch_response, wait=time.sleep):
    profile, mapping, reused, inputs = plan_inputs(metadata, seed, registry, seed_code, reuse_run)
    if out_dir.exists() or out_dir.is_symlink():
        raise FileExistsError("Preserve previous evidence; choose a fresh run destination")
    out_dir.mkdir(parents=True, exist_ok=False)
    for name in ["inputs", "raw", "reviews", "receipts"]:
        (out_dir / name).mkdir()
    for name in inputs.keys() - {"seed.xml"}:
        with (out_dir / "inputs" / name).open("xb") as stream:
            stream.write(inputs[name])
    for code, (raw, review) in reused.items():
        with (out_dir / "raw" / f"{code}.xml").open("xb") as stream:
            stream.write(raw)
        _new_json(out_dir / "reviews" / f"{code}.json", review)
    records = [{"municipality": name, "istat_code": code,
                "state": "reused_source_reviewed" if code in reused else "not_requested",
                "requested": False, "response_sha256": _hash(reused[code][0]) if code in reused else None,
                "observations_received": len(reused[code][1]["observations"]) if code in reused else 0,
                "source_periods": reused[code][1]["source_periods"] if code in reused else [],
                "review_issues": reused[code][1]["review_issues"] if code in reused else [],
                "missing_categories": reused[code][1]["missing_categories"] if code in reused else None}
               for name, code in mapping.items()]
    run = {"schema_version": "0.5-tenure-intake-1", "status": "technical_draft_do_not_publish",
           "phase": "running", "target_analysis_year": 2025, "latest_per_series_only": True,
           "minimum_interval_seconds": INTERVAL_SECONDS, "automatic_retries": 0,
           "input_sha256": {name: _hash(raw) for name, raw in inputs.items()},
           "records": records, "municipal_series_added": 0, "indicator_calculated": False,
           "scientific_approval": False, "publication_allowed": False}
    _update_run(out_dir / "run.json", run)
    consecutive_failures, requested = 0, 0
    try:
        for record in records:
            if record["istat_code"] in reused:
                continue
            if requested:
                wait(INTERVAL_SECONDS)
            code = record["istat_code"]
            record.update(state="request_started", requested=True, url=source_url(code),
                          started_at_utc=datetime.now(timezone.utc).isoformat())
            _update_run(out_dir / "run.json", run)
            requested += 1
            status, raw, error = fetch(record["url"])
            record.update(http_status=status, error=error,
                          completed_at_utc=datetime.now(timezone.utc).isoformat(),
                          response_sha256=None if raw is None else _hash(raw),
                          state="request_failed")
            if raw is not None:
                with (out_dir / "raw" / f"{code}.xml").open("xb") as stream:
                    stream.write(raw)
            halt = status in {403, 429}
            if status == 200 and raw is not None:
                try:
                    review = inspect_response(raw, code, profile)
                except ValueError as exc:
                    record.update(state="source_review_failed", error=str(exc))
                    halt = True  # Schema/identity drift needs review, not 25 more queries.
                else:
                    _new_json(out_dir / "reviews" / f"{code}.json", review)
                    record.update(state="source_reviewed", review_issues=review["review_issues"],
                                  source_periods=review["source_periods"], missing_categories=review["missing_categories"],
                                  observations_received=len(review["observations"]))
            consecutive_failures = 0 if record["state"] == "source_reviewed" else consecutive_failures + 1
            _new_json(out_dir / "receipts" / f"{code}.json", record)
            _update_run(out_dir / "run.json", run)
            print(f"{code}: {record['state']} (HTTP {status}); {requested}/{27 - len(reused)} richieste", flush=True)
            if halt or consecutive_failures >= 3:
                run["phase"] = "stopped_source_requires_review"
                break
        else:
            run["phase"] = "requests_completed"
    except BaseException as exc:
        run.update(phase="interrupted" if isinstance(exc, KeyboardInterrupt) else "failed",
                   execution_error=type(exc).__name__)
        raise
    finally:
        _update_run(out_dir / "run.json", run)
    reviewed = [r for r in records if r["state"] in {"source_reviewed", "reused_source_reviewed"}]
    coverage = {"status": "technical_draft_do_not_publish", "result": "source_coverage_not_indicator_approval",
                "target_municipalities": 27, "source_snapshots_reviewed": len(reviewed),
                "requests_made": requested, "reused_snapshots": len(reused),
                "codes_with_observations": [r["istat_code"] for r in reviewed if r["observations_received"]],
                "complete_category_period_codes": [r["istat_code"] for r in reviewed
                                                    if r["missing_categories"] == [] and len(r["source_periods"]) == 1],
                "review_issue_codes": [r["istat_code"] for r in records if r.get("review_issues")],
                "not_requested": [r["istat_code"] for r in records if not r["requested"] and r["istat_code"] not in reused],
                "failed_codes": [r["istat_code"] for r in records if r["requested"] and r not in reviewed],
                "scientific_approval": False, "publication_allowed": False, "municipal_series_added": 0}
    _new_json(out_dir / "coverage.json", coverage)
    return coverage


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--seed", type=Path, required=True)
    parser.add_argument("--seed-code", required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--reuse-run", type=Path, help="Reuse checksum-verified originals from one stopped run")
    parser.add_argument("--plan-only", action="store_true", help="Read local inputs; no files or network")
    args = parser.parse_args(argv)
    try:
        if args.plan_only:
            _, mapping, reused, _ = plan_inputs(args.metadata, args.seed, args.registry, args.seed_code, args.reuse_run)
            print(json.dumps({"requests_planned": len(mapping) - len(reused), "reused_seed": args.seed_code,
                              "reused_snapshots": len(reused),
                              "interval_seconds": INTERVAL_SECONDS, "automatic_retries": 0,
                              "scientific_approval": False, "publication_allowed": False}))
            return 0
        result = acquire(args.metadata, args.seed, args.registry, args.seed_code, args.out_dir, reuse_run=args.reuse_run)
    except (ValueError, OSError, TypeError, KeyError) as exc:
        parser.exit(2, f"BLOCKED: {exc}\n")
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["source_snapshots_reviewed"] == 27 else 2
