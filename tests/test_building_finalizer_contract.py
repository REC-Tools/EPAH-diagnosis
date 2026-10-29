"""Contract: reviewed building-stock promotion only, no auto-validation."""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_canonical_building_finalizer_requires_human_review_and_safe_upsert():
    path = ROOT / "scripts/finalize_building_stock_single_source.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    names = {node.func.id for node in ast.walk(tree)
             if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
    assert "upsert_indicator_rows" in names
    assert "validate_approval" in names
    assert "prepare" in names
    assert "--approval" in source
    assert "len(matches) != 27" in source
    assert 'MATRIX_FILE.open("w"' not in source


def test_legacy_finalizer_no_longer_promotes_unreviewed_data():
    path = ROOT / "scripts/finalize_building_stock.py"
    source = path.read_text(encoding="utf-8")
    assert "disabled" in source
    assert 'row["status"] = "Dato validato"' not in source
    assert "upsert_indicator_rows" not in source
