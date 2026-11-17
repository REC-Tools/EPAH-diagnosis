"""Publish a completed local directory without replacing earlier evidence.

Callers own staging and validation; this boundary only handles filesystem
publication. Staging must be on the destination filesystem. No files are
copied piecemeal, and no existing output tree is recursively removed.
"""
from __future__ import annotations

import os
from pathlib import Path


def publish_directory(stage: Path, destination: Path) -> Path:
    """Expose a completed staging tree, refusing any prior destination.

    Windows rename already refuses an existing target, including an empty
    directory. POSIX rename may replace an empty directory, so first reserve
    the destination exclusively and replace only that reservation. The final
    rename is atomic on the local filesystem. A failed operation retains the
    stage; only an empty reservation created by this call may be removed.
    """
    if stage.is_symlink() or not stage.is_dir():
        raise ValueError("Publication requires a real staging directory")
    source, target = stage.resolve(), destination.resolve()
    if source == target or source.is_relative_to(target) or target.is_relative_to(source):
        raise ValueError("Staging and destination must be separate directories")
    if destination.exists() or destination.is_symlink():
        raise FileExistsError("Preserve previous output; choose a new destination")
    if os.name == "nt":
        os.rename(stage, destination)
    else:
        destination.mkdir(exist_ok=False)
        try:
            os.replace(stage, destination)
        except OSError:
            try:
                destination.rmdir()
            except OSError:
                # Preserve anything added concurrently. Never recursively clean
                # a destination whose contents this operation does not own.
                pass
            raise
    return destination
