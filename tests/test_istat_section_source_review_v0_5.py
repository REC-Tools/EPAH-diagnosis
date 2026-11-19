import csv
import hashlib
import json

from openpyxl import Workbook
import pytest

from epah_diagnosis.istat_section_source_review_v0_5 import audit_source, main


FIELDS = {"PROCOM": "Identità comunale", "SEZ21_ID": "Identità sezione",
          "PF1": "Famiglie residenti - totale", "A2": "Abitazioni occupate da residenti"}


def workbook(path, rows, extra_sheet=False):
    book = Workbook()
    for row in rows:
        book.active.append(row)
    if extra_sheet:
        book.create_sheet("Unexpected")
    book.save(path)
    book.close()


@pytest.fixture
def inputs(tmp_path):
    data, layout, registry = [tmp_path / name for name in ["source.xlsx", "layout.xlsx", "registry.csv"]]
    workbook(layout, [["NOME_CAMPO", "DEFINIZIONE"], *FIELDS.items()])
    workbook(data, [list(FIELDS), [1001, 101, None, "not checked"], ["001001", "102", 0, 0],
                    [1003, 301, 9, 12]])
    with registry.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerows([["municipality", "istat_code"], ["Comune sintetico A", "001001"],
                         ["Comune sintetico B", "001002"]])
    return data, layout, registry


def test_row_presence_is_not_indicator_completeness_or_zero(inputs):
    originals = {path: path.read_bytes() for path in inputs}
    result = audit_source(*inputs, 2023)
    assert result["source_identity_rows"] == 3 and result["matched_identity_rows"] == 2
    assert [(row["istat_code"], row["source_section_rows"], row["row_presence"])
            for row in result["municipalities"]] == [("001001", 2, "present"), ("001002", 0, "not_observed")]
    assert result["declared_reference_year"] == 2023
    for flag in ["reference_year_verified", "indicator_values_checked", "territorial_compatibility_verified",
                 "indicators_calculated", "scientific_approval", "publication_allowed"]:
        assert result[flag] is False
    assert result["municipal_series_added"] == 0
    assert result["fields"] == [{"name": key, "definition": value} for key, value in FIELDS.items()]
    assert result["input_sha256"] == {name: hashlib.sha256(originals[path]).hexdigest()
                                       for name, path in zip(["data", "layout", "registry"], inputs)}
    assert all(path.read_bytes() == raw for path, raw in originals.items())
    assert str(inputs[0].parent) not in json.dumps(result)
    assert audit_source(*inputs, 2023) == result


@pytest.mark.parametrize("code", [None, True, 1001.5, "1e3", "1234567", "=1001"])
def test_invalid_identity_is_not_silently_dropped(inputs, code):
    workbook(inputs[0], [list(FIELDS), [code, 101, 0, 0]])
    with pytest.raises(ValueError):
        audit_source(*inputs, 2023)


@pytest.mark.parametrize("rows", [
    [list(FIELDS)],
    [list(FIELDS), [1001, None, 1, 1]],
    [list(FIELDS), [1001, 101, 1, 1], [1001, 101, 2, 2]],
    [["PROCOM", "SEZ21_ID", "PF1", "Unexpected"], [1001, 101, 1, 1]],
    [["PROCOM", "SEZ21_ID", "PF1", "PF1"], [1001, 101, 1, 1]],
])
def test_empty_duplicate_or_changed_source_requires_review(inputs, rows):
    workbook(inputs[0], rows)
    with pytest.raises(ValueError):
        audit_source(*inputs, 2023)


@pytest.mark.parametrize("rows", [
    [["wrong", "DEFINIZIONE"], *FIELDS.items()],
    [["NOME_CAMPO", "DEFINIZIONE"], *FIELDS.items(), ["PF1", "duplicate"]],
    [["NOME_CAMPO", "DEFINIZIONE"], ["PROCOM", None]],
    [["NOME_CAMPO", "DEFINIZIONE"], ["PROCOM", "=1"]],
])
def test_ambiguous_layout_is_rejected(inputs, rows):
    workbook(inputs[1], rows)
    with pytest.raises(ValueError):
        audit_source(*inputs, 2023)


def test_multiple_sheets_and_changed_input_are_rejected(inputs, monkeypatch):
    workbook(inputs[0], [list(FIELDS), [1001, 101, 0, 0]], extra_sheet=True)
    with pytest.raises(ValueError, match="single"):
        audit_source(*inputs, 2023)
    workbook(inputs[0], [list(FIELDS), [1001, 101, 0, 0]])
    import epah_diagnosis.istat_section_source_review_v0_5 as module
    original = module._digest
    calls = []
    def digest(path):
        calls.append(path)
        return original(path) if len(calls) <= 3 else "changed"
    monkeypatch.setattr(module, "_digest", digest)
    with pytest.raises(ValueError, match="changed"):
        audit_source(*inputs, 2023)


def test_cli_requires_new_output_and_never_publishes_failed_review(inputs, tmp_path):
    out = tmp_path / "review.json"
    argv = ["--data", str(inputs[0]), "--layout", str(inputs[1]), "--registry", str(inputs[2]),
            "--reference-year", "2023", "--json-out", str(out)]
    assert main(argv) == 0
    before = out.read_bytes()
    with pytest.raises(SystemExit) as exc:
        main(argv)
    assert exc.value.code == 2 and out.read_bytes() == before
    out2 = tmp_path / "failed.json"
    with pytest.raises(SystemExit) as exc:
        main(argv[:-1] + [str(out2)] + ["--reference-year", "25"])
    assert exc.value.code == 2 and not out2.exists()


def test_corrupt_workbook_fails_without_a_report(inputs, tmp_path):
    inputs[0].write_bytes(b"not a workbook")
    out = tmp_path / "failed.json"
    with pytest.raises(SystemExit) as exc:
        main(["--data", str(inputs[0]), "--layout", str(inputs[1]), "--registry", str(inputs[2]),
              "--reference-year", "2023", "--json-out", str(out)])
    assert exc.value.code == 2 and not out.exists()
