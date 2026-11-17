"""Read-only acceptance checks for the complete, unpublished v0.4 output hub.

These checks never mark visual, accessibility, source or scientific review done.
A locally rewritten set of manifests is not a signed authenticity receipt.
"""
from __future__ import annotations

from html.parser import HTMLParser
import struct
import math
from pathlib import Path
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree

from pypdf import PdfReader

from epah_diagnosis.evidence_ledger_v0_4 import FILES
from epah_diagnosis.municipality_sheets_v0_4 import _read
from epah_diagnosis.output_hub_v0_4 import _safe_input_files, _validate_inputs
from epah_diagnosis.output_quality_v0_4 import _checked_path, _json, _manifest, _sha, audit


class _Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if attributes.get("id"):
            self.ids.add(attributes["id"])
        for key in ("href", "src"):
            if attributes.get(key):
                self.links.append((attributes[key], key == "src" or tag == "link"))


def _reference(root: Path, origin: Path, address: str, *, dependency: bool = False):
    parts = urlsplit(address)
    if parts.scheme or parts.netloc:
        if dependency or parts.scheme not in {"http", "https"}:
            raise ValueError("External or executable dependency in offline output")
        return None
    target = origin.parent / unquote(parts.path) if parts.path else origin
    try:
        relative = target.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError("Local link escapes output bundle") from exc
    return _checked_path(root, relative)


def _links(root: Path) -> dict:
    checked, external = 0, set()
    pages = {}
    for path in sorted(root.rglob("*.html")):
        parser = _Links()
        parser.feed(path.read_text(encoding="utf-8"))
        pages[path.resolve()] = parser
    for path, parser in pages.items():
        for address, dependency in parser.links:
            target = _reference(root, path, address, dependency=dependency)
            if target is None:
                external.add(address)
                continue
            fragment = urlsplit(address).fragment
            if fragment and target.resolve() in pages:
                if unquote(fragment) not in pages[target.resolve()].ids:
                    raise ValueError(f"Broken HTML fragment in {path.name}")
            checked += 1
    pdf_references = 0
    for path in sorted(root.rglob("*.pdf")):
        for page in PdfReader(path).pages:
            for reference in page.get("/Annots", []):
                action = reference.get_object().get("/A")
                if action and action.get("/URI"):
                    address = str(action["/URI"])
                    target = _reference(root, path, address)
                    if target is None:
                        external.add(address)
                    else:
                        pdf_references += 1
    return {"local_references_checked": checked, "pdf_references_checked": pdf_references,
            "external_source_links": sorted(external)}


def _media(path: Path) -> None:
    if path.suffix == ".png":
        data = path.read_bytes()[:24]
        if (len(data) != 24 or data[:8] != b"\x89PNG\r\n\x1a\n"
                or data[12:16] != b"IHDR" or min(struct.unpack(">II", data[16:24])) <= 0):
            raise ValueError("Invalid PNG chart header")
    elif path.suffix == ".svg":
        try:
            element = ElementTree.parse(path).getroot()
            box = [float(v) for v in element.attrib["viewBox"].split()]
            if element.tag != "{http://www.w3.org/2000/svg}svg" or len(box) != 4 or not all(math.isfinite(v) for v in box) or min(box[2:]) <= 0:
                raise ValueError("Invalid SVG chart dimensions")
            for item in element.iter():
                for key, address in item.attrib.items():
                    if (key.rsplit("}", 1)[-1] == "href" and not address.startswith("#")
                            and not (item.tag == "{http://www.w3.org/2000/svg}image"
                                     and address.startswith("data:image/png;base64,"))):
                        raise ValueError("External SVG dependency")
        except (ElementTree.ParseError, KeyError) as exc:
            raise ValueError("Invalid SVG chart") from exc


def _pdf(path: Path, count: int) -> list[str]:
    try:
        pages = PdfReader(path).pages
        if len(pages) != count:
            raise ValueError(f"Wrong PDF page count: {path.name}")
        texts = []
        for page in pages:
            box = page.mediabox
            if abs(float(box.width) - 595.28) > 1 or abs(float(box.height) - 841.89) > 1:
                raise ValueError(f"PDF page is not portrait A4: {path.name}")
            texts.append(page.extract_text() or "")
        return texts
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"Unreadable bundle PDF: {path.name}") from exc


def _sheet_pdf_matches(texts: list[str], town: dict, records: list[dict]) -> None:
    """Check extracted sheet text against CSV, independently of sheet formatting.

    Hashes and equality with the combined book cannot detect the same wrong
    observation rendered in both PDFs. Compare each indicator's own section,
    including missingness and counts, rather than searching the whole page.
    """
    normalise = lambda text: " ".join(text.split())
    pages = [normalise(text) for text in texts]
    identity = normalise(town["name"] + " (" + town["code"] + ") | Tutti gli indicatori previsti")
    if identity not in pages[1] or normalise(town["name"]) not in pages[0]:
        raise ValueError("Municipal PDF identifier differs from CSV")

    def sections(text, rows, footer):
        cursor = 0
        for index, row in enumerate(rows):
            heading = normalise(row["indicator_id"] + " | " + row["indicator_name"])
            start = text.find(heading, cursor)
            following = (normalise(rows[index + 1]["indicator_id"] + " | " +
                                   rows[index + 1]["indicator_name"])
                         if index + 1 < len(rows) else footer)
            end = text.find(following, start + len(heading)) if start >= 0 else -1
            if start < 0 or end < 0:
                raise ValueError("Municipal PDF indicator section differs from CSV")
            yield row, heading, text[start:end].strip()
            cursor = end

    def value(row):
        if row["missing_reason"] == "not_acquired":
            return "Non acquisito"
        return row["value"] + (" " + row["unit"] if row["unit"] else "")

    for row, heading, section in sections(pages[1], records, "Universi, definizioni e limiti:"):
        expected = heading + " " + value(row) + " | " + (row["reference_period"] or "Periodo non acquisito")
        if row["numerator"]:
            expected += " N / D: " + row["numerator"] + " / " + row["denominator"]
        expected += " Fonte: " + row["source"]
        if section != normalise(expected):
            raise ValueError("Municipal PDF displayed observation differs from CSV")
    previews = [row for row in records if not row["missing_reason"]][:6]
    for row, _, section in sections(pages[0], previews, "Criteri di lettura"):
        # Page one also contains an editorial universe between heading and value.
        # The observation and period must end that indicator's own section.
        if not section.endswith(" " + normalise(value(row) + " " + row["reference_period"])):
            raise ValueError("Municipal PDF preview observation differs from CSV")


def audit_bundle(hub: Path) -> dict:
    """Check snapshot bindings, all local links, charts, sheets and page budgets."""
    manifest = _manifest(hub, "manifest.json")
    if (manifest.get("scientific_approval") is not False
            or manifest.get("no_composite_score") is not True):
        raise ValueError("Bundle is not explicitly an unapproved descriptive output")
    _safe_input_files(hub, set(manifest["outputs_sha256"]) | {"manifest.json"})
    for name in ("index.html", "sintesi.pdf", "atlas/atlas_manifest.json",
                 "review/manifest.json", "sheets/manifest.json"):
        if name not in manifest["outputs_sha256"]:
            raise ValueError(f"Required bundle artifact missing: {name}")
    atlas, review, sheets = (hub / name for name in ("atlas", "review", "sheets"))
    payload, _ = _validate_inputs(atlas, review)
    if (payload.get("scientific_approval", False) is not False
            or _json(atlas / "atlas_manifest.json").get("scientific_approval", False) is not False):
        raise ValueError("Atlas cannot claim scientific approval")
    report = audit(review, atlas=atlas)
    metrics, towns, per_code = _read(payload, review / "observations.csv")
    if (manifest.get("municipalities") != 27 or manifest.get("indicator_slots") != len(metrics)
            or manifest.get("atlas_data_sha256") != _sha(atlas / "atlas_data.json")
            or manifest.get("atlas_manifest_sha256") != _sha(atlas / "atlas_manifest.json")
            or manifest.get("review_manifest_sha256") != _sha(review / "manifest.json")):
        raise ValueError("Bundle reference snapshot mismatch")
    sheet_manifest = _manifest(sheets, "manifest.json")
    _safe_input_files(sheets, set(sheet_manifest["outputs_sha256"]) | {"manifest.json"})
    metadata = _json(sheets / "metadata.json")
    if (metadata.get("scientific_approval") is not False
            or metadata.get("publication_allowed") is not False
            or metadata.get("reference_atlas_data_sha256") != _sha(atlas / "atlas_data.json")
            or metadata.get("reference_observations_csv_sha256") != _sha(review / "observations.csv")
            or metadata.get("municipalities") != 27 or metadata.get("indicator_slots") != len(metrics)
            or metadata.get("pages_per_municipality") != 2 or metadata.get("combined_book_pages") != 54
            or metadata.get("municipality_codes") != [t["code"] for t in towns]):
        raise ValueError("Municipal sheet metadata differs from snapshot")
    if (review / FILES[0]).exists():
        if metadata.get("evidence_ledger") != FILES[0]:
            raise ValueError("Municipal sheets omit the evidence ledger reference")
        for name in FILES:
            if (sheets / name).read_bytes() != (review / name).read_bytes():
                raise ValueError("Municipal sheet ledger differs from review")
    combined = _pdf(sheets / "schede_27_comuni.pdf", 54)
    for index, town in enumerate(towns):
        texts = _pdf(sheets / "pdf" / (town["code"] + ".pdf"), 2)
        if texts != combined[2 * index:2 * index + 2]:
            raise ValueError("Combined PDF differs from individual municipal sheets")
        if any(town["code"] not in text or "NON PUBBLICARE" not in text for text in texts):
            raise ValueError("Municipal PDF lacks identifier or draft notice")
        if any(m["id"] not in texts[1] for m in metrics):
            raise ValueError("Municipal PDF lacks an indicator slot")
        _sheet_pdf_matches(texts, town, per_code[town["code"]])
    _pdf(hub / "sintesi.pdf", 2)
    charts = 0
    for metric in metrics:
        if metric["available"]:
            for kind in ("map", "distribution"):
                for extension in ("png", "svg"):
                    relative = f"charts/{metric['id']}_{kind}.{extension}"
                    _media(_checked_path(atlas, relative))
                    charts += 1
    return {
        "schema_version": "0.4-output-bundle-quality-1",
        "status": "technical_bundle_consistency_passed",
        "publication_allowed": False, "scientific_approval": False,
        "municipalities": 27, "indicator_slots": len(metrics),
        "observations": report["observations"], "hashes_verified": True,
        "pdf_csv_display_match": True,
        "municipal_pdf_csv_display_match": True,
        "municipal_sheets": 27, "pages_per_sheet": 2, "combined_pages": 54,
        "summary_pages": 2, "chart_files_checked": charts, **_links(hub),
        "visual_review_completed": False,
        "human_checks_required": ["real_sources", "real_output_visual_review", "screen_reader",
                                  "print_legibility", "direct_file_offline_navigation"],
    }
