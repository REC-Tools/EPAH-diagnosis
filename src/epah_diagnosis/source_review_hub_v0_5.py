"""Compose existing source reviews; no acquisition, stock sums or indicators."""
from __future__ import annotations

import argparse
import csv
from datetime import date
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import tempfile
from urllib.parse import urlsplit

from .atc_source_review_v0_5 import audit_response
from .cli import read_municipality_codes
from .directory_publication import publish_directory
from .tenure_review_portal_v0_5 import assemble_snapshot
from .utci_export_review_v0_5 import inspect_export

SCHEMA = "0.5-source-review-hub-1"
STATUS = "technical_draft_do_not_publish"


def encode(value):
    return (json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def decode(raw):
    def invalid(value):
        raise ValueError("Non-finite JSON literal")
    return json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs, parse_constant=invalid)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _regular(path):
    # Includes Windows junctions, even on Python versions without is_junction().
    info = path.lstat()
    if path.is_symlink() or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
        raise ValueError("Source bundles must not contain links or junctions")


def tree(root):
    """Read a local tree without following links, including directory junctions."""
    _regular(root)
    files = {}
    for path in root.iterdir():
        _regular(path)
        if path.is_dir():
            files.update({path.name + "/" + name: raw for name, raw in tree(path).items()})
        elif path.is_file():
            files[path.name] = path.read_bytes()
        else:
            raise ValueError("Unsupported bundle member")
    return files


def write_files(root, files):
    for name, raw in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)


def _keys(value, expected):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise ValueError("Unexpected or missing input contract fields")


def _date(value):
    if value is not None:
        if not isinstance(value, str) or date.fromisoformat(value).isoformat() != value:
            raise ValueError("Use an ISO date or null; never infer a stock date")


def _atc(index, mapping, *, file_names):
    _keys(index, {"provider", "entries"})
    if not isinstance(index["provider"], str) or not index["provider"].strip():
        raise ValueError("Declare exactly one ATC provider")
    if not isinstance(index["entries"], list):
        raise ValueError("ATC entries must be a list")
    seen = set()
    for entry in index["entries"]:
        _keys(entry, {"istat_code", "source_selector", "reference_date", "acquired_on", "source_url"}
              | ({"file"} if file_names else set()))
        code = entry["istat_code"]
        if not isinstance(code, str) or code not in mapping.values() or code in seen:
            raise ValueError("Unknown or duplicate municipal association")
        seen.add(code)
        if not isinstance(entry["source_selector"], str) or not entry["source_selector"].strip():
            raise ValueError("Declare the original query selector; association is not ISTAT proof")
        for key in ("reference_date", "acquired_on"):
            _date(entry[key])
        url = entry["source_url"]
        if url is not None:
            if not isinstance(url, str):
                raise ValueError("Source URL must be public HTTP(S) or null")
            parts = urlsplit(url)
            if parts.scheme not in {"http", "https"} or not parts.netloc or parts.username or parts.password:
                raise ValueError("Source URL must be public HTTP(S) without credentials")
        if file_names:
            name = entry["file"]
            if not isinstance(name, str) or not name or PurePosixPath(name).name != name or "\\" in name or ":" in name or name in {".", ".."}:
                raise ValueError("ATC file must be a basename next to its index")


def snapshot(root):
    """Replay fixed archived inputs through the existing source adapters."""
    config = decode((root / "inputs.json").read_bytes())
    _keys(config, {"schema_version", "input_kind", "tenure", "utci", "atc"})
    if config["schema_version"] != SCHEMA or config["input_kind"] not in {"unclassified_local_sources", "synthetic_declared"} or type(config["tenure"]) is not bool:
        raise ValueError("Unknown hub input contract")
    mapping = read_municipality_codes(root / "sources/registry.csv")
    if len(mapping) != 27:
        raise ValueError("Require the complete 27-municipality registry")
    tenure = None
    expected = {"inputs.json", "sources/registry.csv"}
    if config["tenure"]:
        run = root / "sources/tenure"
        if (run / "inputs/registry.csv").read_bytes() != (root / "sources/registry.csv").read_bytes():
            raise ValueError("Tenure and hub registries differ")
        tenure, files, _ = assemble_snapshot(run, run / "inputs/review-notes.md")
        expected.update("sources/tenure/" + name for name in files)
    utci = None
    if config["utci"] is not None:
        options = config["utci"]
        _keys(options, {"field", "reference_year"})
        if not isinstance(options["field"], str) or type(options["reference_year"]) is not int:
            raise ValueError("Declare UTCI field and reference year explicitly")
        utci = inspect_export(root / "sources/utci.nc", **options)
        if "selected_values" not in utci:
            raise ValueError("Select an existing numeric UTCI field")
        expected.add("sources/utci.nc")
    atc = {}
    if config["atc"] is not None:
        _atc(config["atc"], mapping, file_names=False)
        original_index = decode((root / "sources/atc-index.json").read_bytes())
        _atc(original_index, mapping, file_names=True)
        normalized = {"provider": original_index["provider"],
                      "entries": [{k: v for k, v in entry.items() if k != "file"} for entry in original_index["entries"]]}
        if encode(normalized) != encode(config["atc"]):
            raise ValueError("ATC associations disagree with the archived input index")
        expected.add("sources/atc-index.json")
        for entry in config["atc"]["entries"]:
            name = "sources/atc/" + entry["istat_code"] + ".html.txt"
            atc[entry["istat_code"]] = {**entry, "state": "source_review_required",
                                       "original": name, "audit": audit_response((root / name).read_bytes())}
            expected.add(name)
    rows = []
    tenure_rows = {} if tenure is None else {r["istat_code"]: r for r in tenure["municipalities"]}
    tenure_records = {} if tenure is None else {r["istat_code"]: r for r in decode((root / "sources/tenure/run.json").read_bytes())["records"]}
    for name, code in mapping.items():
        t = tenure_rows.get(code)
        if t is not None:
            t = {**t, "acquired_at_utc": tenure_records[code].get("completed_at_utc")}
        rows.append({"municipality": name, "istat_code": code,
                     "tenure": t, "atc": atc.get(code),
                     "utci_municipal_state": "not_aggregated" if utci else "source_not_included"})
    # Exact input membership is checked separately from generated products.
    actual = {name for name in tree(root) if name == "inputs.json" or name.startswith("sources/")}
    if actual != expected:
        raise ValueError("Unexpected or missing source members")
    return {"schema_version": SCHEMA, "status": STATUS, "target_analysis_year": 2025,
            "input_kind": config["input_kind"], "municipalities": rows,
            "atc_provider": None if config["atc"] is None else config["atc"]["provider"],
            "source_sha256": {name: digest((root / name).read_bytes()) for name in sorted(expected) if name.startswith("sources/")},
            "utci": utci, "tenure_universe": None if tenure is None else tenure["source_notes"],
            "weights_applied": False, "indicator_calculated": False, "municipal_series_added": 0,
            "scientific_approval": False, "publication_allowed": False}


def differences(before, after):
    """Exact field changes; these are import differences, never temporal trends."""
    old_identity = [(r["municipality"], r["istat_code"]) for r in before["municipalities"]]
    if old_identity != [(r["municipality"], r["istat_code"]) for r in after["municipalities"]]:
        raise ValueError("Cannot compare different municipal registries")
    if before["input_kind"] != after["input_kind"] or (before["atc_provider"] is not None and after["atc_provider"] is not None and before["atc_provider"] != after["atc_provider"]):
        raise ValueError("Compare the same provider and input kind; no cross-provider aggregation")
    def walk(a, b, prefix=""):
        if type(a) is type(b) and isinstance(a, dict):
            result = []
            for key in sorted(set(a) | set(b)):
                if key not in a or key not in b:
                    result.append({"field": prefix + key, "before": a.get(key), "after": b.get(key)})
                else:
                    result.extend(walk(a[key], b[key], prefix + key + "."))
            return result
        if encode(a) == encode(b):
            return []
        return [{"field": prefix.rstrip("."), "before": a, "after": b}]
    rows = [{"istat_code": b["istat_code"], "changes": walk(a, b)}
            for a, b in zip(before["municipalities"], after["municipalities"])]
    return {"municipalities": rows, "utci_changes": walk(before["utci"], after["utci"]),
            "source_file_changes": walk(before["source_sha256"], after["source_sha256"]),
            "provider_change": walk(before["atc_provider"], after["atc_provider"]),
            "interpretation": "Import differences only; not trends, weights or scientific approval"}


def verify_sources(root):
    """Check checksums AND replay both versions before trusting a comparison."""
    files = tree(root)
    manifest = decode(files["manifest.json"])
    _keys(manifest, {"schema_version", "status", "files_sha256"})
    if manifest["schema_version"] != SCHEMA or manifest["status"] != STATUS:
        raise ValueError("Unknown source hub manifest")
    if {name: digest(raw) for name, raw in files.items() if name != "manifest.json"} != manifest["files_sha256"]:
        raise ValueError("Hub file set or checksum mismatch")
    current = snapshot(root)
    if encode(current) != encode(decode(files["snapshot.json"])):
        raise ValueError("Snapshot disagrees with replayed sources")
    expected = {"inputs.json", "snapshot.json", "index.html", "manifest.json", "comparison.json"}
    expected.update(name for name in files if name.startswith("sources/"))
    comparison = None
    if any(name.startswith("baseline/") for name in files):
        old = snapshot(root / "baseline")
        if encode(old) != encode(decode(files["baseline/snapshot.json"])):
            raise ValueError("Baseline disagrees with replayed sources")
        expected.update("baseline/" + name for name in tree(root / "baseline")
                        if name in {"inputs.json", "snapshot.json"} or name.startswith("sources/"))
        comparison = differences(old, current)
    if set(files) != expected or encode(comparison) != encode(decode(files["comparison.json"])):
        raise ValueError("Unexpected members or inconsistent comparison")
    if tree(root) != files:
        raise ValueError("Hub changed during verification")
    return current, comparison, files


def build_hub(registry: Path, out_dir: Path, *, tenure_run=None, notes=None,
              utci_source=None, utci_field=None, atc_index=None, previous=None, synthetic=False):
    """Archive local inputs in a fresh destination, then compose existing audits."""
    if out_dir.exists() or out_dir.is_symlink():
        raise FileExistsError("Choose a fresh output destination")
    if (tenure_run is None) != (notes is None) or (utci_source is None) != (utci_field is None):
        raise ValueError("Tenure needs notes; UTCI needs an explicit field")
    for source in (registry, tenure_run, notes, utci_source, atc_index, previous):
        if source is not None:
            source = Path(source)
            _regular(source)
            a, b = source.resolve(), out_dir.resolve()
            if a == b or a.is_relative_to(b) or b.is_relative_to(a):
                raise ValueError("Keep output separate from all input paths")
    mapping = read_municipality_codes(registry)
    files = {"sources/registry.csv": registry.read_bytes()}
    config = {"schema_version": SCHEMA, "input_kind": "synthetic_declared" if synthetic else "unclassified_local_sources",
              "tenure": tenure_run is not None, "utci": None, "atc": None}
    if tenure_run is not None:
        tree(tenure_run)  # Refuse linked source members before existing adapters read them.
        _, archived, _ = assemble_snapshot(tenure_run, notes)
        files.update({"sources/tenure/" + name: raw for name, raw in archived.items()})
    if utci_source is not None:
        files["sources/utci.nc"] = utci_source.read_bytes()
        config["utci"] = {"reference_year": 2025, "field": utci_field}
    if atc_index is not None:
        index = decode(atc_index.read_bytes())
        _atc(index, mapping, file_names=True)
        files["sources/atc-index.json"] = atc_index.read_bytes()
        config["atc"] = {"provider": index["provider"], "entries": []}
        for entry in index["entries"]:
            path = atc_index.parent / entry["file"]
            _regular(path)
            files["sources/atc/" + entry["istat_code"] + ".html.txt"] = path.read_bytes()
            config["atc"]["entries"].append({k: v for k, v in entry.items() if k != "file"})
    files["inputs.json"] = encode(config)
    old = None
    if previous is not None:
        from .source_review_hub_audit_v0_5 import audit_hub
        audit_hub(previous)
        old, _, archived = verify_sources(previous)
        files.update({"baseline/" + name: raw for name, raw in archived.items()
                      if name in {"inputs.json", "snapshot.json"} or name.startswith("sources/")})
    out_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".source-hub-", dir=out_dir.parent) as tmp:
        stage = Path(tmp) / "hub"
        write_files(stage, files)
        current = snapshot(stage)
        comparison = None if old is None else differences(old, current)
        from .source_review_hub_render_v0_5 import render
        files.update({"snapshot.json": encode(current), "comparison.json": encode(comparison),
                      "index.html": render(current, comparison).encode("utf-8")})
        files["manifest.json"] = encode({"schema_version": SCHEMA, "status": STATUS,
                                         "files_sha256": {n: digest(raw) for n, raw in files.items()}})
        write_files(stage, files)
        from .source_review_hub_audit_v0_5 import audit_hub
        audit_hub(stage)
        publish_directory(stage, out_dir)
    return out_dir


def build_example(out_dir):
    """Exercise the production composer with fictitious identities and public-table shape."""
    from .atc_source_review_v0_5 import HEADERS
    from .utci_export_review_v0_5 import create_example
    if out_dir.exists() or out_dir.is_symlink():
        raise FileExistsError("Choose a fresh example destination")
    out_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".hub-example-", dir=out_dir.parent) as tmp:
        root = Path(tmp)
        registry = root / "registry.csv"
        with registry.open("w", encoding="utf-8", newline="") as stream:
            csv.writer(stream).writerows([["municipality", "istat_code"],
                                         *[[f"Comune sintetico {i}", f"001{i:03}"] for i in range(1, 28)]])
        nc = create_example(root / "climate") / "synthetic.nc"
        raw = "<table><tr>" + "".join("<th>" + h + "</th>" for h in HEADERS) + "</tr></table>"
        (root / "table.html").write_text(raw, encoding="utf-8")
        index = root / "atc.json"
        index.write_bytes(encode({"provider": "Ente fittizio", "entries": [
            {"istat_code": "001001", "source_selector": "COMUNE SINTETICO 1", "file": "table.html",
             "reference_date": None, "acquired_on": None, "source_url": None}]}))
        return build_hub(registry, out_dir, utci_source=nc, utci_field="example_days", atc_index=index, synthetic=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--tenure-run", type=Path)
    parser.add_argument("--notes", type=Path)
    parser.add_argument("--utci-source", type=Path)
    parser.add_argument("--utci-field")
    parser.add_argument("--atc-index", type=Path)
    parser.add_argument("--previous", type=Path)
    parser.add_argument("--synthetic", action="store_true", help="Explicitly declare all supplied inputs synthetic")
    parser.add_argument("--example", action="store_true", help="Generate synthetic inputs and use the production composer")
    args = parser.parse_args(argv)
    try:
        options = vars(args).copy()
        example = options.pop("example")
        if example:
            if any(options[k] is not None for k in ("registry", "tenure_run", "notes", "utci_source", "utci_field", "atc_index", "previous")) or args.synthetic:
                raise ValueError("--example accepts only --out-dir")
            out = build_example(args.out_dir)
        else:
            if args.registry is None:
                raise ValueError("--registry is required for local source composition")
            out = build_hub(**options)
    except (ValueError, OSError, TypeError, KeyError) as exc:
        parser.exit(2, f"BLOCKED: {exc}\n")
    print(f"Portale fonti pronto: {out / 'index.html'}; nessuna approvazione scientifica.")
    return 0
