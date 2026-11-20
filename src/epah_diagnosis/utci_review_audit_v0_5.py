"""Independently check a UTCI review pack, without approving its source science."""
from __future__ import annotations

import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
import re

from .provenance import sha256_file
from .utci_export_review_v0_5 import inspect_export

MEMBERS = ("source/original.nc", "review.json", "index.html")
SCHEMA = "0.5-utci-review-portal-manifest-1"


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON member")
        result[key] = value
    return result


def _constant(value):
    raise ValueError("Non-finite JSON literal")


def _json(raw):
    return json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs, parse_constant=_constant)


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":"))


class _Page(HTMLParser):
    """Read the v1 presentation contract, independently of the renderer."""
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.rows, self.links, self.codes, self.text, self.header = [], [], [], [], []
        self._row = self._cell = self._code = None
        self.headings, self._heading = {}, None
        self._in_header = False
        self.feed(html)
        self.close()
        if self._row is not None or self._cell is not None or self._code is not None or self._in_header or self._heading is not None:
            raise ValueError("Incomplete HTML presentation")

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag in {"script", "iframe", "object", "embed", "base", "link", "img"}:
            raise ValueError("Unsupported active or external HTML content")
        if any(key in {"src", "srcset"} or key.startswith("on") for key, _ in attrs):
            raise ValueError("Unsupported HTML resource or event attribute")
        if values.get("http-equiv", "").lower() == "refresh":
            raise ValueError("Unsupported HTML redirect")
        if "href" in values:
            self.links.append(values["href"])
        if tag == "header":
            self._in_header = True
        if tag == "h2":
            if self._heading is not None or values.get("id") in self.headings:
                raise ValueError("Ambiguous section heading")
            self._heading = (values.get("id"), [])
        if tag == "tr":
            if self._row is not None:
                raise ValueError("Nested table row")
            self._row = []
        if tag in {"th", "td"}:
            if self._row is None or self._cell is not None:
                raise ValueError("Ambiguous table cell")
            self._cell = []
        if tag == "code":
            if self._code is not None:
                raise ValueError("Nested code element")
            self._code = []

    def handle_data(self, data):
        self.text.append(data)
        if self._in_header:
            self.header.append(data)
        if self._cell is not None:
            self._cell.append(data)
        if self._code is not None:
            self._code.append(data)
        if self._heading is not None:
            self._heading[1].append(data)

    def handle_endtag(self, tag):
        if tag == "header":
            self._in_header = False
        if tag == "h2":
            if self._heading is None:
                raise ValueError("Unmatched section heading")
            key, parts = self._heading
            self.headings[key] = "".join(parts)
            self._heading = None
        if tag in {"th", "td"}:
            if self._cell is None:
                raise ValueError("Unmatched table cell")
            self._row.append("".join(self._cell))
            self._cell = None
        if tag == "tr":
            if self._row is None or self._cell is not None or len(self._row) != 2:
                raise ValueError("Require two cells per presentation row")
            self.rows.append(self._row)
            self._row = None
        if tag == "code":
            if self._code is None:
                raise ValueError("Unmatched code element")
            self.codes.append("".join(self._code))
            self._code = None


def _display(value):
    if value is None or value == "":
        return "Non dichiarato / non disponibile"
    return json.dumps(value, ensure_ascii=False, allow_nan=False) if isinstance(value, (list, dict)) else str(value)


def _check_html(raw: bytes, report: dict, kind: str):
    page = _Page(raw.decode("utf-8"))
    attrs = report["variables"][report["selected_field"]]["attributes"]
    time = report.get("time", {})
    expected = {
        "Campo selezionato esplicitamente": report["selected_field"],
        "Descrizione ricevuta": attrs.get("long_name"), "Unità dichiarata nel file": attrs.get("units"),
        "Anno richiesto al controllo": report["reference_year"],
        "Tempo decodificato della fonte": time.get("decoded_values"),
        "Limiti temporali decodificati": time.get("decoded_bounds"),
        "Calendario dichiarato": time.get("attributes", {}).get("calendar"),
        "Calendario usato per decodificare": time.get("calendar_used_for_decoding"),
    }
    for label, key in (("Valori totali nel campo", "cells"), ("Valori finiti", "finite"),
                       ("Valori mascherati", "masked"), ("Non finiti non mascherati", "unmasked_nonfinite"),
                       ("Zeri validi", "zero"), ("Minimo numerico", "minimum"), ("Massimo numerico", "maximum"),
                       ("Valori frazionari", "fractional"),
                       ("Valori fuori dall'intervallo numerico candidato", "outside_day_range"),
                       ("Limite gregoriano usato nella diagnostica", "gregorian_year_day_limit")):
        expected[label] = report["selected_values"][key]
    for label, coord, key in (("Latitudini dei centri", "latitude", "values"),
                              ("Passi di latitudine", "latitude", "steps"),
                              ("Longitudini dei centri", "longitude", "values"),
                              ("Passi di longitudine", "longitude", "steps")):
        expected[label] = report.get(coord, {}).get(key)
    if len(page.rows) != len(expected) or dict(page.rows) != {k: _display(v) for k, v in expected.items()}:
        raise ValueError("HTML table disagrees with the independently replayed source")
    if sorted(page.links) != sorted(["source/original.nc", "review.json", "manifest.json"]):
        raise ValueError("HTML links disagree with the pack contract")
    if page.codes != [report["source_sha256"], *report["issues"]]:
        raise ValueError("HTML source hash or review issue codes disagree")
    if page.headings.get("issues") != f"Questioni da revisionare ({len(report['issues'])})":
        raise ValueError("HTML issue count disagrees with the source review")
    header = " ".join(page.header)
    if "BOZZA TECNICA" not in header or "technical_draft_do_not_publish" not in header:
        raise ValueError("Draft warning missing from HTML header")
    if ("DATI SINTETICI · NON SONO DATI TERRITORIALI" in header) != (kind == "synthetic_declared"):
        raise ValueError("Synthetic declaration disagrees between manifest and HTML")
    if "Nessun risultato è approvato e la pubblicazione territoriale non è autorizzata." not in " ".join(page.text):
        raise ValueError("Scientific/publication warning missing from HTML")


def audit_pack(pack: Path) -> dict:
    """Read only four fixed members; never follow paths supplied by a manifest."""
    if pack.is_symlink() or not pack.is_dir():
        raise ValueError("Require a real local pack directory")
    if {p.name for p in pack.iterdir()} != {"source", "index.html", "review.json", "manifest.json"}:
        raise ValueError("Unexpected or missing pack members")
    source_dir = pack / "source"
    if source_dir.is_symlink() or not source_dir.is_dir() or {p.name for p in source_dir.iterdir()} != {"original.nc"}:
        raise ValueError("Unexpected source directory or symbolic link")
    paths = {name: pack / name for name in (*MEMBERS, "manifest.json")}
    if any(path.is_symlink() or not path.is_file() for path in paths.values()):
        raise ValueError("Require regular pack files; symbolic links are not supported")
    before = {name: sha256_file(path) for name, path in paths.items()}
    manifest = _json(paths["manifest.json"].read_bytes())
    fields = {"schema_version", "status", "entrypoint", "input_kind", "reference_year", "selected_field",
              "source_sha256", "files_sha256", "scientific_approval", "publication_allowed", "aggregation_performed"}
    if not isinstance(manifest, dict) or manifest.get("schema_version") != SCHEMA or set(manifest) != fields:
        raise ValueError("Unsupported UTCI pack manifest")
    if (manifest.get("status") != "technical_draft_do_not_publish"
            or any(manifest.get(key) is not False for key in ("scientific_approval", "publication_allowed", "aggregation_performed"))
            or manifest.get("entrypoint") != "epah methodology utci-portal"):
        raise ValueError("Require an unapproved source-review pack")
    kind = manifest.get("input_kind")
    if kind not in ("synthetic_declared", "unclassified_local_source"):
        raise ValueError("Unsupported input declaration")
    hashes = manifest.get("files_sha256")
    if not isinstance(hashes, dict) or set(hashes) != set(MEMBERS):
        raise ValueError("Manifest must describe exactly the fixed pack members")
    for name in MEMBERS:
        if not isinstance(hashes[name], str) or not re.fullmatch(r"[0-9a-f]{64}", hashes[name]) or hashes[name] != before[name]:
            raise ValueError("Pack member checksum mismatch")
    if manifest.get("source_sha256") != before["source/original.nc"]:
        raise ValueError("Original source hash disagrees with manifest")
    year, field = manifest.get("reference_year"), manifest.get("selected_field")
    if type(year) is not int or not isinstance(field, str) or not field:
        raise ValueError("Require an explicit integer year and field")
    replay = inspect_export(paths["source/original.nc"], reference_year=year, field=field)
    saved = _json(paths["review.json"].read_bytes())
    if "selected_values" not in replay or _canonical(saved) != _canonical(replay):
        raise ValueError("Saved review disagrees with an independent original replay")
    _check_html(paths["index.html"].read_bytes(), replay, kind)
    if before != {name: sha256_file(path) for name, path in paths.items()}:
        raise ValueError("Pack changed during audit; discard this audit")
    return {"schema_version": "0.5-utci-pack-audit-1", "result": "consistent_source_review_not_scientific_approval",
            "software_integrity_passed": True, "pack_files_sha256": before,
            "reference_year": year, "selected_field": field, "input_kind": kind,
            "source_review_issues": replay["issues"], "pack_unchanged": True,
            "scientific_approval": False, "publication_allowed": False,
            "municipal_coverage_verified": False, "visual_layout_verified": False,
            "daily_completeness_verified": False, "threshold_semantics_verified": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", type=Path, required=True)
    parser.add_argument("--json-out", type=Path, help="Fresh audit receipt outside the preserved pack")
    args = parser.parse_args(argv)
    if args.json_out is not None and (args.json_out.resolve().is_relative_to(args.pack.resolve())
                                     or args.json_out.exists() or args.json_out.is_symlink()):
        parser.exit(2, "BLOCKED: choose a fresh audit destination outside the pack.\n")
    try:
        result = audit_pack(args.pack)
        code = 0
    except (ValueError, OSError, TypeError, KeyError, RuntimeError) as exc:
        result = {"schema_version": "0.5-utci-pack-audit-1", "result": "blocked_inconsistent_pack",
                  "software_integrity_passed": False, "error_type": type(exc).__name__,
                  "error": str(exc) if isinstance(exc, ValueError) else "Unreadable input or unsupported structure",
                  "scientific_approval": False, "publication_allowed": False}
        code = 2
    if args.json_out is not None:
        try:
            args.json_out.parent.mkdir(parents=True, exist_ok=True)
            with args.json_out.open("x", encoding="utf-8", newline="\n") as handle:
                json.dump(result, handle, ensure_ascii=False, allow_nan=False, indent=2)
                handle.write("\n")
        except (OSError, ValueError) as exc:
            parser.exit(2, f"BLOCKED: audit receipt could not be written ({type(exc).__name__}).\n")
    if code == 0:
        print(f"COERENTE: integrità e replay verificati. Questioni della fonte ancora aperte: {len(result['source_review_issues'])}. Nessuna approvazione scientifica.")
    else:
        print("BLOCKED: " + result["error"])
    return code
