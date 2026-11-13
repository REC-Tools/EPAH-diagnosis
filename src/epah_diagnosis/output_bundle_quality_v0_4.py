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
from epah_diagnosis.review_pack_v0_4 import _format_row, _read_rows


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


def _report_pdf_matches(review: Path, metrics: list[dict]) -> None:
    normalise = lambda text: " ".join(text.split())
    text = normalise(" ".join(page.extract_text() or "" for page in PdfReader(review / "review.pdf").pages))
    rows = _read_rows(review / "observations.csv")
    cursor = 0
    for index, metric in enumerate(metrics):
        heading = normalise(metric["id"] + " | " + metric["name"])
        start = text.find(heading, cursor)
        if start < 0:
            raise ValueError("PDF report indicator heading missing or reordered")
        end = len(text)
        if index + 1 < len(metrics):
            following = metrics[index + 1]
            end = text.find(normalise(following["id"] + " | " + following["name"]), start + len(heading))
            if end < 0:
                raise ValueError("PDF report indicator heading missing or reordered")
        section = text[start:end]
        for prefix, value in (("Fonte: ", metric["source"]), ("Unità: ", metric["unit"]),
                              ("Periodo: ", ", ".join(metric["years"]) or "non acquisito")):
            if normalise(prefix + value) not in section:
                raise ValueError("PDF report source/unit/period differs from atlas")
        for row in (r for r in rows if r["indicator_id"] == metric["id"]):
            if normalise(" ".join(_format_row(row))) not in section:
                raise ValueError("PDF report displayed observation differs from CSV")
        cursor = end


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
    metrics, towns, _ = _read(payload, review / "observations.csv")
    _report_pdf_matches(review, metrics)
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
        "municipal_sheets": 27, "pages_per_sheet": 2, "combined_pages": 54,
        "summary_pages": 2, "chart_files_checked": charts, **_links(hub),
        "visual_review_completed": False,
        "human_checks_required": ["real_sources", "real_output_visual_review", "screen_reader",
                                  "print_legibility", "direct_file_offline_navigation"],
    }
