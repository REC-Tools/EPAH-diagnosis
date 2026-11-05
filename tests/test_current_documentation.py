"""Current-doc claims, historical archive and v0.2 release boundaries."""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVED = (
    "pipeline_audit.md",
    "pipeline_dependencies.md",
    "finalizer_id_alignment.md",
    "legacy_indicator_id_migration.md",
    "priority_81_promotion_20261029.md",
)


def load_checker():
    spec = importlib.util.spec_from_file_location(
        "epah_docs_audit", ROOT / "scripts" / "check_documentation.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_outdated_pipeline_documents_are_archived_not_lost() -> None:
    for basename in ARCHIVED:
        assert not (ROOT / "docs" / basename).exists()
        path = ROOT / "docs" / "archive" / "2026-10" / basename
        assert path.is_file()
        assert "ARCHIVIO" in path.read_text(encoding="utf-8")


def test_current_docs_have_no_known_superseded_release_claims() -> None:
    checker = load_checker()
    for path in checker.CURRENT_STATUS_DOCUMENTS:
        assert path.exists(), str(path)
        assert checker.stale_release_claims(path.read_text(encoding="utf-8")) == [], str(path)


def test_stale_detector_rejects_historical_instructions() -> None:
    checker = load_checker()
    for snippet in (
        "catalogo metodologico di otto voci",
        "matrice attuale contiene 81 righe",
        "maturità proposta per la PR B e non ancora implementata",
        "python scripts/generate_overlap_map.py",
    ):
        assert checker.stale_release_claims(snippet), snippet
    assert not checker.stale_release_claims(
        "Catalogo canonico: nove indicatori, matrice di 243 righe; "
        "software v0.2.0, ricerca v0.3 sperimentale."
    )


def test_framework_describes_9_by_27_and_experimental_methodology() -> None:
    framework = (ROOT / "docs/framework.md").read_text(encoding="utf-8")
    pipeline = (ROOT / "docs/pipeline.md").read_text(encoding="utf-8")
    assert "243 righe" in framework
    assert "nove indicatori" in framework
    assert "EXPERIMENTAL" in framework
    assert "methodological_maturity" in pipeline
    assert "v0.2.0" in pipeline


def test_archive_cross_links_point_to_actual_files() -> None:
    checker = load_checker()
    for basename in ARCHIVED:
        path = ROOT / "docs/archive/2026-10" / basename
        assert checker.problems_for_document(path) == [], str(path)


def test_current_migration_is_not_advertised_as_routine() -> None:
    instructions = (ROOT / "docs/operational_guide.md").read_text(encoding="utf-8")
    archive = (ROOT / "docs/archive/README.md").read_text(encoding="utf-8")
    assert "scripts/migrate_legacy_indicator_ids.py" not in instructions
    assert "non eseguirlo come manutenzione corrente" in archive
