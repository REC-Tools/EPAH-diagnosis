"""Library and legacy atlas commands must use the same implementation."""
import ast
import importlib.util
from pathlib import Path
import subprocess
import sys

import pytest

from epah_diagnosis import visual_atlas_v0_3, visual_atlas_v0_4

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("version,library", [("3", visual_atlas_v0_3), ("4", visual_atlas_v0_4)])
def test_legacy_command_delegates_to_the_library(version, library):
    path = ROOT / "scripts" / f"build_v0_{version}_visual_atlas.py"
    spec = importlib.util.spec_from_file_location(f"atlas_cli_v{version}_compatibility", path)
    command = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(command)
    assert command.main is library.main
    assert not any(isinstance(node, (ast.FunctionDef, ast.ClassDef))
                   for node in ast.parse(path.read_text(encoding="utf-8")).body)


@pytest.mark.parametrize("version", ["3", "4"])
def test_legacy_command_help_is_available_outside_checkout(tmp_path, version):
    result = subprocess.run([sys.executable, str(ROOT / "scripts" / f"build_v0_{version}_visual_atlas.py"),
                             "--help"], cwd=tmp_path, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    for option in ("--bundle", "--registry", "--out-dir", "--h47-zip", "--h50-dir", "--h46-dir"):
        assert option in result.stdout
    assert not list(tmp_path.iterdir())


def test_v04_uses_the_normal_v03_package_module():
    assert visual_atlas_v0_4.v3 is visual_atlas_v0_3
    assert visual_atlas_v0_3.ROOT == visual_atlas_v0_4.ROOT == ROOT


def test_atlas_libraries_import_without_reading_or_loading_scripts(tmp_path):
    # A fresh interpreter exercises real imports, not modules cached by pytest.
    script = r'''
import importlib.util
from pathlib import Path
import sys
source = Path(sys.argv[1])
sys.path.insert(0, str(source / "src"))
original = importlib.util.spec_from_file_location
def guarded(name, location, *args, **kwargs):
    if Path(location).resolve().is_relative_to(source / "scripts"):
        raise AssertionError("Library tried to load a command implementation")
    return original(name, location, *args, **kwargs)
importlib.util.spec_from_file_location = guarded
from epah_diagnosis import visual_atlas_v0_3, visual_atlas_v0_4
assert visual_atlas_v0_4.v3 is visual_atlas_v0_3
assert len(visual_atlas_v0_3.METRICS) == 13
assert len(visual_atlas_v0_4.NEW) == 3
'''
    result = subprocess.run([sys.executable, "-B", "-c", script, str(ROOT)], cwd=tmp_path,
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("library", [visual_atlas_v0_3, visual_atlas_v0_4])
def test_library_main_accepts_arguments_without_reading_originals(library, capsys):
    with pytest.raises(SystemExit) as result:
        library.main(["--help"])
    assert result.value.code == 0
    assert "--bundle" in capsys.readouterr().out
