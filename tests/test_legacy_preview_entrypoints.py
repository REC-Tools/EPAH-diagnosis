"""Ensure retired preview entrypoints stay runnable and out of the v0.2 path."""
from __future__ import annotations

import importlib.util
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEGACY_NAMES = (
    "build_municipality_comparison.py",
    "build_multidimensional_overlap.py",
    "generate_overlap_map.py",
)


def test_legacy_previews_are_grouped_not_deleted() -> None:
    for name in LEGACY_NAMES:
        assert not (ROOT / "scripts" / name).exists()
        assert (ROOT / "scripts" / "legacy" / name).is_file()


def test_legacy_previews_preserve_root_and_default_paths() -> None:
    for name in LEGACY_NAMES:
        namespace = runpy.run_path(
            str(ROOT / "scripts" / "legacy" / name),
            run_name="epah_legacy_test_import",
        )
        assert namespace["ROOT"] == ROOT
        assert callable(namespace["main"])
        # Importing a legacy script must not create derived or canonical outputs.
        assert namespace.get("__name__") != "__main__"


def test_v02_cli_does_not_call_legacy_previews() -> None:
    cli = (ROOT / "src/epah_diagnosis/workflow_cli.py").read_text(encoding="utf-8")
    for name in LEGACY_NAMES:
        assert name not in cli
    for name in (
        "build_v0_2_territorial_report.py",
        "build_v0_2_multidimensional_analysis.py",
        "build_v0_2_dashboard.py",
        "build_v0_2_review_package.py",
    ):
        assert name in cli


def test_workflows_do_not_call_legacy_previews() -> None:
    for workflow in (ROOT / ".github/workflows").glob("*.yml"):
        text = workflow.read_text(encoding="utf-8")
        for name in LEGACY_NAMES:
            assert name not in text


def test_documentation_checker_supports_nested_script_paths(tmp_path: Path) -> None:
    spec = importlib.util.spec_from_file_location(
        "epah_documentation", ROOT / "scripts" / "check_documentation.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sample = ROOT / "docs" / "diagnostic_maps.md"
    assert "scripts/legacy/generate_overlap_map.py" in sample.read_text(encoding="utf-8")
    assert not module.problems_for_document(sample)
    # Nested paths must also be rejected if they are absent.
    module.ROOT = tmp_path
    orphan = tmp_path / "missing.md"
    orphan.write_text("Run scripts/legacy/not_a_real_script.py", encoding="utf-8")
    assert any("scripts/legacy/not_a_real_script.py" in x for x in module.problems_for_document(orphan))
