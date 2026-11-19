import hashlib
import json

import pytest

from epah_diagnosis.atc_source_review_v0_5 import HEADERS, audit_response, main


def html(rows, headers=HEADERS):
    return ("<table><thead><tr>" + "".join(f"<th>{h}</th>" for h in headers)
            + "</tr></thead><tbody>" + "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
            + "</tbody></table>").encode("utf-8")


ROW = ("COMUNE FITTIZIO", "Indirizzo sintetico", "ATC", "PUBBLICA", "0", "2", "3", "AUTONOMO")


def test_identical_rows_are_flagged_without_removing_or_summing():
    raw = html([ROW, ROW, (" COMUNE  FITTIZIO\n",) + ROW[1:]])
    result = audit_response(raw)
    assert result["table_rows"] == 3 and result["identical_row_groups"] == [[1, 2, 3]]
    assert result["rows_removed"] == result["municipal_series_added"] == 0
    assert result["stock_totals_calculated"] is result["scientific_approval"] is False
    assert result["stock_reference_date_verified"] is result["erp_scope_verified"] is False
    assert result["source_sha256"] == hashlib.sha256(raw).hexdigest()
    assert "Indirizzo sintetico" not in json.dumps(result)


def test_similar_rows_are_not_assumed_to_be_the_same_property():
    changed = list(ROW)
    changed[4] = "1"
    assert audit_response(html([ROW, changed]))["identical_row_groups"] == []


def test_missing_is_not_zero_and_formatted_counts_are_not_guessed():
    missing = list(ROW)
    missing[4], missing[5] = "", "1.000"
    result = audit_response(html([ROW, missing]))
    assert result["numeric_cell_issues"] == [
        {"row": 2, "column": "Alloggi locati", "issue": "missing_or_non_integer"},
        {"row": 2, "column": "Alloggi riscattati", "issue": "missing_or_non_integer"}]


@pytest.mark.parametrize("raw", [b"SQL connection failed", b"<table><tr><th>Comune",
    html([ROW[:-1]]), html([ROW], headers=("Changed",) + HEADERS[1:]),
    html([ROW]) + html([ROW]), b"<table><table></table></table>"])
def test_invalid_or_changed_source_is_refused(raw):
    with pytest.raises(ValueError):
        audit_response(raw)


def test_empty_table_is_not_a_verified_zero_erp_stock():
    record = audit_response(html([]))
    assert record["table_rows"] == 0 and record["stock_totals_calculated"] is False
    assert record["result"] == "source_review_required"


def test_cli_preserves_source_and_existing_report(tmp_path):
    source, out = tmp_path / "source.html", tmp_path / "review.json"
    raw = html([ROW])
    source.write_bytes(raw)
    assert main(["--html", str(source), "--json-out", str(out)]) == 0
    record = out.read_bytes()
    for destination in (out, source):
        with pytest.raises(SystemExit) as error:
            main(["--html", str(source), "--json-out", str(destination)])
        assert error.value.code == 2
    assert source.read_bytes() == raw and out.read_bytes() == record
