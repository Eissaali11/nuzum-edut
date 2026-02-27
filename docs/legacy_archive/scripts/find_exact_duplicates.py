from pathlib import Path
import hashlib
from collections import defaultdict

ROOT = Path('.')
EXTS = {'.html', '.css', '.js', '.py'}
SKIP = {
    'venv',
    '.git',
    '__pycache__',
    'node_modules',
    '.mypy_cache',
    '.pytest_cache',
    'build',
    'dist',
    '_graveyard_archive',
    'emails_queue',
}


def should_skip(path: Path) -> bool:
    return any(part in SKIP for part in path.parts)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    groups = defaultdict(list)
    for path in ROOT.rglob('*'):
        if not path.is_file():
            continue
        if should_skip(path):
            continue
        if path.suffix.lower() not in EXTS:
            continue
        try:
            if path.stat().st_size == 0:
                continue
        except Exception:
            continue
        try:
            digest = sha256(path)
            groups[digest].append(path)
        except Exception:
            continue

    duplicates = [paths for paths in groups.values() if len(paths) > 1]
    duplicates.sort(key=lambda paths: paths[0].stat().st_size if paths else 0, reverse=True)

    print('DUPLICATE_GROUPS', len(duplicates))
    for paths in duplicates[:50]:
        size = paths[0].stat().st_size
        print(f'\nSIZE {size}')
        for p in paths:
            print(str(p).replace('\\', '/'))


if __name__ == '__main__':
    main()