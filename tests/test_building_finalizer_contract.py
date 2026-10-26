import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_canonical_building_finalizer_uses_safe_upsert_and_coverage_checks():
    path = ROOT / "scripts/finalize_building_stock_single_source.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = {node.func.id for node in ast.walk(tree)
             if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
    assert "upsert_indicator_rows" in names
    assert "filter_by_codes" in names
    source = path.read_text(encoding="utf-8")
    assert "len(target_codes) != len(target_names)" in source
    assert "len(records) != len(target_names)" in source
    assert 'MATRIX_FILE.open("w"' not in source
