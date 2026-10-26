"""Offline integrity checks for the methodology registry (not the data pipelines)."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ID = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
ROLES = {"vulnerability", "context", "accessibility"}
DIRECTIONS = {"higher", "lower", "contextual", "ordinal_contextual"}
MATURITY = {"PROPOSED", "EXPERIMENTAL", "OPERATIONAL", "VALIDATED", "RETIRED"}
REQUIRED = {"id", "name", "role", "dimension", "unit", "interpretation_direction",
            "source_ids", "source_registry_coverage", "methodological_maturity",
            "definition", "territorial_level", "documentation", "caveat"}


def load_json(path: Path, errors: list[str]):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        errors.append(f"{path}: unreadable or invalid JSON: {exc}")
        return None


def validate(root: Path = ROOT) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    catalog = load_json(root / "config/indicators.json", errors)
    registry = load_json(root / "config/sources.json", errors)
    if not isinstance(catalog, dict) or not isinstance(registry, dict):
        return errors or ["invalid registry structures"], warnings
    indicators, sources = catalog.get("indicators"), registry.get("sources")
    if not isinstance(indicators, list) or not isinstance(sources, list):
        return ["indicators and sources must be arrays"], warnings

    source_ids = set()
    for n, source in enumerate(sources, 1):
        if not isinstance(source, dict):
            errors.append(f"source {n}: must be an object")
            continue
        sid = source.get("id")
        if not isinstance(sid, str) or not ID.fullmatch(sid):
            errors.append(f"source {n}: invalid id {sid!r}")
        elif sid in source_ids:
            errors.append(f"source {n}: duplicate id {sid}")
        else:
            source_ids.add(sid)

    seen = set()
    for n, item in enumerate(indicators, 1):
        if not isinstance(item, dict):
            errors.append(f"indicator {n}: must be an object")
            continue
        missing = REQUIRED - item.keys()
        if missing:
            errors.append(f"indicator {n}: missing fields {sorted(missing)}")
        iid = item.get("id")
        if not isinstance(iid, str) or not ID.fullmatch(iid):
            errors.append(f"indicator {n}: invalid id {iid!r}")
        elif iid in seen:
            errors.append(f"indicator {n}: duplicate id {iid}")
        else:
            seen.add(iid)
        for field in ("name", "dimension", "unit", "definition", "caveat"):
            if not isinstance(item.get(field), str) or not item[field].strip():
                errors.append(f"indicator {iid}: missing/invalid {field}")
        for field, accepted in (("role", ROLES), ("interpretation_direction", DIRECTIONS),
                                ("methodological_maturity", MATURITY)):
            if item.get(field) not in accepted:
                errors.append(f"indicator {iid}: invalid {field}")
        if item.get("territorial_level") != "municipality":
            errors.append(f"indicator {iid}: territorial_level must be municipality")
        path = item.get("documentation")
        if not isinstance(path, str) or not path.startswith("docs/") or not path.endswith(".md") or ".." in Path(path).parts:
            errors.append(f"indicator {iid}: invalid documentation path")
        elif not (root / path).is_file():
            errors.append(f"indicator {iid}: missing documentation {path}")
        refs = item.get("source_ids")
        if not isinstance(refs, list) or any(not isinstance(s, str) for s in refs):
            errors.append(f"indicator {iid}: source_ids must be a string array")
        else:
            if len(refs) != len(set(refs)):
                errors.append(f"indicator {iid}: duplicate source reference")
            for sid in refs:
                if sid not in source_ids:
                    errors.append(f"indicator {iid}: unknown source {sid}")
            coverage = item.get("source_registry_coverage")
            if coverage not in {"registered", "pending"}:
                errors.append(f"indicator {iid}: invalid source_registry_coverage")
            elif (coverage == "registered") != bool(refs):
                errors.append(f"indicator {iid}: source coverage inconsistent with references")
            if not refs:
                warnings.append(f"indicator {iid}: source registration pending")

    # Uncatalogued indicator dossiers are advisory until intentional additions
    # to the registry have been reviewed. No automatic registry mutation.
    documented = {x.get("documentation") for x in indicators if isinstance(x, dict)}
    for path in sorted((root / "docs").glob("indicator_[0-9][0-9]_*.md")):
        if "docs/" + path.name not in documented:
            warnings.append(f"uncatalogued indicator dossier: docs/{path.name}")
    return errors, warnings


def main() -> int:
    errors, warnings = validate()
    for message in warnings:
        print(f"WARNING: {message}")
    for message in errors:
        print(f"ERROR: {message}", file=sys.stderr)
    print(f"Framework checks: {len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
