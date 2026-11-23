"""Read-only source replay and HTML contract checks, independent of the renderer."""
import argparse
import hashlib
from html.parser import HTMLParser
from pathlib import Path

from .source_review_hub_v0_5 import encode, verify_sources

# Pinned presentation resource; arbitrary CSS is not trusted as offline content.
STYLE_SHA256 = "732200da6ec702d5d412e5bfe7b6d765614161b201ef2b081c8e9477ec11d3d2"


class Page(HTMLParser):
    def __init__(self, raw):
        super().__init__(convert_charrefs=True)
        self.links, self.rows, self.pres, self.styles, self.text = [], [], [], [], []
        self.metas, self.doctypes = [], 0
        self.row = self.cell = self.pre = self.style = None
        self.stack = []
        self.feed(raw.decode("utf-8"))
        self.close()
        if self.stack or self.doctypes != 1 or self.metas != [{"charset": "utf-8"}, {"name": "viewport", "content": "width=device-width,initial-scale=1"}]:
            raise ValueError("Incomplete HTML")

    def handle_comment(self, data):
        raise ValueError("Comments are not part of the presentation contract")

    def handle_decl(self, decl):
        if decl.lower() != "doctype html":
            raise ValueError("Unsupported declaration")
        self.doctypes += 1

    def unknown_decl(self, data):
        raise ValueError("Unsupported declaration")

    def handle_pi(self, data):
        raise ValueError("Unsupported processing instruction")

    def handle_starttag(self, tag, attrs):
        allowed = {"html", "head", "meta", "title", "style", "body", "header", "p", "h1", "h2", "main", "section", "nav", "a", "div", "table", "caption", "thead", "tbody", "tr", "th", "td", "pre", "strong", "footer"}
        if tag not in allowed or len(dict(attrs)) != len(attrs):
            raise ValueError("Unsupported or ambiguous HTML")
        permitted = {"html": {"lang"}, "meta": {"charset", "name", "content"}, "p": {"class"},
                     "nav": {"aria-label"}, "a": {"href"}, "div": {"class", "tabindex", "aria-label"},
                     "tr": {"data-code"}, "th": {"scope"}}
        if not set(dict(attrs)) <= permitted.get(tag, set()):
            raise ValueError("Unsupported HTML attribute")
        if tag != "meta":
            self.stack.append(tag)
        else:
            self.metas.append(dict(attrs))
        if tag == "a":
            self.links.append(dict(attrs).get("href"))
        if tag == "tr":
            self.row = [dict(attrs).get("data-code"), []]
        if tag in {"th", "td"}:
            self.cell = []
        if tag == "pre":
            self.pre = []
        if tag == "style":
            self.style = []

    def handle_endtag(self, tag):
        if not self.stack or self.stack.pop() != tag:
            raise ValueError("Malformed HTML nesting")
        if tag == "style":
            self.styles.append("".join(self.style))
            self.style = None
        if tag == "pre":
            self.pres.append("".join(self.pre))
            self.pre = None
        if tag in {"th", "td"}:
            self.row[1].append("".join(self.cell))
            self.cell = None
        if tag == "tr":
            self.rows.append(self.row)
            self.row = None

    def handle_data(self, data):
        self.text.append(data)
        for target in (self.cell, self.pre, self.style):
            if target is not None:
                target.append(data)


def audit_hub(pack):
    source, comparison, files = verify_sources(pack)
    page = Page(files["index.html"])
    if len(page.styles) != 1 or hashlib.sha256(page.styles[0].encode()).hexdigest() != STYLE_SHA256:
        raise ValueError("Unreviewed HTML style")
    if len(page.rows) != 28 or any(len(cells) != 6 for _, cells in page.rows):
        raise ValueError("Require a heading and 27 complete municipal rows")
    changes = {} if comparison is None else {r["istat_code"]: r["changes"] for r in comparison["municipalities"]}
    expected_links = {"snapshot.json", "comparison.json", "manifest.json", "inputs.json", "sources/registry.csv"}
    for (code, cells), row in zip(page.rows[1:], source["municipalities"]):
        if code != row["istat_code"] or cells[0] != row["municipality"] + " · " + code:
            raise ValueError("HTML municipal identity mismatch")
        t, a = row["tenure"], row["atc"]
        if t is not None:
            expected = "Anni: " + (", ".join(t["periods"]) or "non disponibili")
            expected += "; scarto 2025: " + (", ".join(str(2025 - int(y)) for y in t["periods"]) or "non disponibile")
            expected += "".join("; " + k + ": " + (t["values"].get(k) if t["values"].get(k) is not None else "non disponibile") for k in ("ALL", "RENT", "OWN", "OTH_OR"))
            expected += "; stato: " + t["state"] + "; residuo: " + str(t["partition_difference"])
            expected += "; acquisita UTC: " + (t["acquired_at_utc"] or "non documentata")
            expected += "; questioni: " + ", ".join(t["issues"])
            if not t["values"]:
                expected += "; prossimo passo: completare lo snapshot della fonte."
            for key in ("raw_link", "review_link", "request_receipt_link"):
                if t[key]:
                    expected_links.add("sources/tenure/" + t[key])
        else:
            expected = "Fonte non inclusa. Prossimo passo: includere una run ISTAT verificabile."
        if cells[1] != expected:
            raise ValueError("HTML tenure values, years or missingness disagree")
        if a is None:
            expected = "Tabella non inclusa; stock sconosciuto. Prossimo passo: verificare disponibilità della fonte pubblica."
        else:
            expected = ("Righe della tabella: " + str(a["audit"]["table_rows"]) + "; gruppi identici: " + str(len(a["audit"]["identical_row_groups"]))
                        + "; data stock dichiarata: " + (a["reference_date"] or "sconosciuta")
                        + "; acquisita il: " + (a["acquired_on"] or "sconosciuto")
                        + "; selettore dichiarato: " + a["source_selector"]
                        + "; identità ISTAT, stock ERP e data da verificare. Prossimo passo: chiarire perimetro, data e duplicati.")
            expected_links.add(a["original"])
        if cells[2] != expected or cells[3] != ("Fonte UTCI inclusa; nessun valore comunale aggregato." if source["utci"] else "Fonte UTCI non inclusa."):
            raise ValueError("HTML source coverage or ATC facts disagree")
        if cells[5] != ("Primo pacchetto; confronto non richiesto." if comparison is None else ("Modificato" if changes[code] else "Invariato")):
            raise ValueError("HTML comparison state disagrees")
    expected_pres = []
    if source["tenure_universe"] is not None:
        expected_pres.append(encode(source["tenure_universe"]).decode().rstrip("\n"))
        expected_links.update({"sources/tenure/inputs/review-notes.md", "sources/tenure/inputs/metadata.xml"})
    if source["utci"] is not None:
        expected_pres.append(encode(source["utci"]).decode().rstrip("\n"))
        expected_links.add("sources/utci.nc")
    if comparison is not None:
        expected_pres.append(encode(comparison).decode().rstrip("\n"))
    if page.pres != expected_pres or set(page.links) != expected_links or any(link not in files for link in page.links):
        raise ValueError("HTML controls or local links disagree")
    text = " ".join(page.text)
    for warning in ("technical_draft_do_not_publish", "Pubblicazione territoriale non autorizzata.", "senza tetto", "Nessun indicatore o peso temporale calcolato."):
        if warning not in text:
            raise ValueError("Missing review warning")
    if ("DATI SINTETICI" in text) != (source["input_kind"] == "synthetic_declared"):
        raise ValueError("Synthetic label disagrees")
    if source["atc_provider"] is not None and source["atc_provider"] not in text:
        raise ValueError("Missing provider label")
    return {"result": "consistent_source_review_not_scientific_approval", "municipalities": 27,
            "comparison_replayed": comparison is not None, "scientific_approval": False, "publication_allowed": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        audit_hub(args.pack)
    except (ValueError, OSError, TypeError, KeyError) as exc:
        parser.exit(2, f"BLOCKED: {exc}\n")
    print("COERENTE: originali, replay delle versioni e contratto HTML verificati. Nessuna approvazione scientifica.")
    return 0
