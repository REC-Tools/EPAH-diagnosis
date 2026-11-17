"""Publication failures must preserve previous and concurrent evidence."""
import os
from pathlib import Path

import pytest

from epah_diagnosis.directory_publication import publish_directory


def staged(tmp_path):
    stage = tmp_path / "stage"
    stage.mkdir()
    (stage / "manifest.json").write_bytes(b'{"synthetic":true}')
    (stage / "nested").mkdir()
    (stage / "nested/data.csv").write_bytes(b"value\n0\n")
    return stage


def test_complete_tree_is_published_with_identical_bytes(tmp_path):
    stage = staged(tmp_path)
    output = tmp_path / "output"
    publish_directory(stage, output)
    assert not stage.exists()
    assert (output / "nested/data.csv").read_bytes() == b"value\n0\n"
    assert (output / "manifest.json").read_bytes() == b'{"synthetic":true}'


@pytest.mark.parametrize("kind", ["empty_directory", "evidence_directory", "file"])
def test_existing_destination_is_never_replaced(tmp_path, kind):
    stage = staged(tmp_path)
    output = tmp_path / "output"
    if kind == "file":
        output.write_bytes(b"prior evidence")
    else:
        output.mkdir()
        if kind == "evidence_directory":
            (output / "prior.json").write_bytes(b"prior evidence")
    with pytest.raises(FileExistsError):
        publish_directory(stage, output)
    assert stage.is_dir()
    if kind == "file":
        assert output.read_bytes() == b"prior evidence"
    elif kind == "evidence_directory":
        assert (output / "prior.json").read_bytes() == b"prior evidence"
    else:
        assert list(output.iterdir()) == []


def test_failed_publication_retains_staging(tmp_path, monkeypatch):
    stage = staged(tmp_path)
    def fail(*args):
        raise OSError("synthetic filesystem failure")
    monkeypatch.setattr(os, "rename" if os.name == "nt" else "replace", fail)
    output = tmp_path / "output"
    with pytest.raises(OSError, match="synthetic"):
        publish_directory(stage, output)
    assert not output.exists()
    assert (stage / "nested/data.csv").read_bytes() == b"value\n0\n"


def test_unrelated_content_is_not_removed_on_failure(tmp_path, monkeypatch):
    stage = staged(tmp_path)
    output = tmp_path / "output"
    def fail(*args):
        output.mkdir(exist_ok=True)
        (output / "concurrent.txt").write_bytes(b"preserve me")
        raise OSError("synthetic concurrent writer")
    monkeypatch.setattr(os, "rename" if os.name == "nt" else "replace", fail)
    with pytest.raises(OSError, match="concurrent"):
        publish_directory(stage, output)
    assert (output / "concurrent.txt").read_bytes() == b"preserve me"
    assert stage.is_dir()


def test_rejects_overlapping_destination_without_mutating_stage(tmp_path):
    stage = staged(tmp_path)
    with pytest.raises(ValueError, match="separate"):
        publish_directory(stage, stage / "child")
    assert (stage / "manifest.json").is_file()


def test_competing_publishers_cannot_merge_or_replace_snapshots(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    first, second = tmp_path / "first", tmp_path / "second"
    for directory, marker in ((first, b"first"), (second, b"second")):
        directory.mkdir()
        (directory / "marker").write_bytes(marker)
    output, barrier = tmp_path / "output", Barrier(2)
    def publish(stage):
        barrier.wait()
        try:
            publish_directory(stage, output)
            return "published"
        except FileExistsError:
            return "preserved"
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(publish, (first, second)))
    assert sorted(results) == ["preserved", "published"]
    assert (output / "marker").read_bytes() in (b"first", b"second")
    assert sum(path.exists() for path in (first, second)) == 1
