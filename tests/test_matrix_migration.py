import csv
import importlib.util
import json
from pathlib import Path

import pytest

MODULE = Path(__file__).resolve().parents[1] / "scripts/migrate_matrix_preview.py"
spec = importlib.util.spec_from_file_location("migrate_matrix_preview", MODULE)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)
preview = module.preview


def setup(tmp_path):
    (tmp_path / "config").mkdir()
    (tmp_path / "data").mkdir()
    indicators = [{"id": "a", "name": "A", "unit": "%", "dimension": "economic",
                   "source_ids": [], "caveat": "proxy"},
                  {"id": "rail", "name": "Rail", "unit": "minutes",
                   "dimension": "accessibility", "source_ids": [], "caveat": "context"}]
    (tmp_path / "config/catalog.json").write_text(json.dumps({"indicators": indicators}))
    (tmp_path / "data/municipalities.csv").write_text("municipality\nAlpette\nBorgiallo\n")
    row = {k: "" for k in module.FIELDS}
    row.update(municipality="Alpette", indicator_id="a", indicator_name="old name",
               status="Dato validato", value="42", notes="preserve me")
    path = tmp_path / "data/matrix.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=module.FIELDS)
        w.writeheader()
        w.writerow(row)
    return path, tmp_path / "data/municipalities.csv", tmp_path / "config/catalog.json"


def test_additive_preserves_existing_values(tmp_path):
    matrix, municipalities, catalog = setup(tmp_path)
    output = tmp_path / "new.csv"
    assert preview(matrix, municipalities, catalog, output) == (1, 3)
    with output.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 4
    assert rows[0]["notes"] == "preserve me"
    assert rows[0]["value"] == "42"
    assert rows[0]["status"] == "Dato validato"
    assert all(r["status"] == "Da verificare" for r in rows[1:])


def test_no_overwrite(tmp_path):
    args = setup(tmp_path)
    with pytest.raises(ValueError, match="Refusing"):
        preview(*args, args[0])
    output = tmp_path / "new.csv"
    preview(*args, output)
    with pytest.raises(ValueError, match="already exists"):
        preview(*args, output)


def test_duplicate_existing_key_fails(tmp_path):
    matrix, municipalities, catalog = setup(tmp_path)
    content = matrix.read_text(encoding="utf-8").splitlines()
    matrix.write_text("\n".join(content + [content[-1]]) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Duplicate"):
        preview(matrix, municipalities, catalog, tmp_path / "new.csv")
