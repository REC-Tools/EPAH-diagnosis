"""Capability probes for tests that require actual filesystem features."""
import errno

import pytest


@pytest.fixture
def symlink_support(tmp_path):
    """Skip real-symlink attacks only when the host cannot create a symlink."""
    source, link = tmp_path / "probe-source", tmp_path / "probe-link"
    source.write_text("synthetic capability probe", encoding="utf-8")
    try:
        link.symlink_to(source)
    except OSError as exc:
        if getattr(exc, "winerror", None) == 1314 or exc.errno in (errno.EPERM, errno.EACCES):
            pytest.skip("Host cannot create symlinks; run this security test on a capable host")
        raise
    else:
        link.unlink()
    finally:
        source.unlink()
