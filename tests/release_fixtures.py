"""Restore a historical software version in an isolated synthetic project copy."""
import tomllib


def restore_version(root, historical):
    current = tomllib.loads((root / 'pyproject.toml').read_text(encoding='utf-8'))['project']['version']
    changes = (
        ('pyproject.toml', f'version = "{current}"', f'version = "{historical}"'),
        ('src/epah_diagnosis/__init__.py', f'__version__ = "{current}"', f'__version__ = "{historical}"'),
        ('uv.lock', f'name = "epah-diagnosis"\nversion = "{current}"',
                    f'name = "epah-diagnosis"\nversion = "{historical}"'),
    )
    for relative, before, after in changes:
        path = root / relative
        text = path.read_text(encoding='utf-8')
        assert text.count(before) == 1
        path.write_text(text.replace(before, after), encoding='utf-8')
