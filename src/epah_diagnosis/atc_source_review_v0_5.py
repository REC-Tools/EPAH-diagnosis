"""Independent review of public ATC management tables; never an ERP stock estimator."""
import argparse
from collections import defaultdict
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re

HEADERS = ("Comune", "Indirizzo", "Proprietà", "Gestione", "Alloggi locati",
           "Alloggi riscattati", "Altro (Locali commerciali/posti auto)", "Riscaldamento")


class _Table(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables = 0
        self.inside = False
        self.cells = None
        self.parts = None
        self.kinds = []
        self.rows = []

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.tables += 1
            if self.inside or self.tables != 1:
                raise ValueError("Expected one standalone ATC response table")
            self.inside = True
        elif self.inside and tag == "tr":
            if self.cells is not None:
                raise ValueError("Unclosed table row")
            self.cells, self.kinds = [], []
        elif self.inside and tag in {"td", "th"}:
            if self.cells is None or self.parts is not None:
                raise ValueError("Malformed table cell")
            self.parts = []
            self.kinds.append(tag)
        elif self.parts is not None and tag == "br":
            self.parts.append(" ")

    def handle_data(self, data):
        if self.parts is not None:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if self.inside and tag in {"td", "th"}:
            if self.parts is None or not self.kinds or tag != self.kinds[-1]:
                raise ValueError("Unexpected closing cell")
            self.cells.append(" ".join("".join(self.parts).split()))
            self.parts = None
        elif self.inside and tag == "tr":
            if self.cells is None or self.parts is not None:
                raise ValueError("Malformed table row")
            self.rows.append((self.kinds, self.cells))
            self.cells = None
        elif tag == "table":
            if not self.inside or self.cells is not None or self.parts is not None:
                raise ValueError("Malformed table boundary")
            self.inside = False


def audit_response(raw: bytes) -> dict:
    """Report rows and equality groups; preserve originals and never sum/deduplicate."""
    parser = _Table()
    parser.feed(raw.decode("utf-8-sig"))
    parser.close()
    if parser.tables != 1 or parser.inside or not parser.rows:
        raise ValueError("Missing or incomplete ATC response table")
    kinds, header = parser.rows[0]
    if kinds != ["th"] * len(HEADERS) or tuple(header) != HEADERS:
        raise ValueError("Unexpected ATC headers; source contract requires review")
    rows = []
    for kinds, cells in parser.rows[1:]:
        if kinds != ["td"] * len(HEADERS) or len(cells) != len(HEADERS):
            raise ValueError("Unexpected ATC data row shape")
        rows.append(tuple(cells))
    equality = defaultdict(list)
    issues = []
    for index, row in enumerate(rows, start=1):
        equality[row].append(index)
        for column in [4, 5, 6]:
            if not re.fullmatch(r"[0-9]+", row[column]):
                issues.append({"row": index, "column": HEADERS[column], "issue": "missing_or_non_integer"})
    return {"schema_version": "0.5-atc-source-review-1",
            "status": "technical_draft_do_not_publish", "result": "source_review_required",
            "source_sha256": hashlib.sha256(raw).hexdigest(), "table_rows": len(rows),
            "identical_row_groups": [indices for indices in equality.values() if len(indices) > 1],
            "numeric_cell_issues": issues, "rows_removed": 0,
            "stock_totals_calculated": False, "stock_reference_date_verified": False,
            "municipal_istat_identity_verified": False, "erp_scope_verified": False,
            "scientific_approval": False, "publication_allowed": False,
            "municipal_series_added": 0}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--html", type=Path, required=True)
    parser.add_argument("--json-out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = audit_response(args.html.read_bytes())
        # Exclusive creation also prevents replacing the source if paths coincide.
        with args.json_out.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
    except (ValueError, OSError, TypeError) as exc:
        parser.exit(2, f"BLOCKED: {exc}\n")
    print("ATC source response reviewed; stock, date and ERP scope still unverified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
