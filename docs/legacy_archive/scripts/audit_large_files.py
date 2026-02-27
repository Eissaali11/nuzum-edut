from pathlib import Path
from collections import Counter

ROOT = Path('.')
EXTS = {
    '.py', '.html', '.js', '.ts', '.css', '.md', '.txt', '.json', '.yml', '.yaml',
    '.ini', '.toml', '.sql', '.sh', '.ps1', '.bat'
}
SKIP = {
    'venv', '.git', '__pycache__', 'node_modules', '.mypy_cache', '.pytest_cache',
    'dist', 'build', '_graveyard_archive', 'emails_queue', 'docs', 'backups'
}


def should_skip(path: Path) -> bool:
    return any(part in SKIP for part in path.parts)


def scan():
    rows = []
    for path in ROOT.rglob('*'):
        if not path.is_file():
            continue
        if should_skip(path):
            continue
        if path.suffix.lower() not in EXTS:
            continue

        try:
            raw = path.read_bytes()
        except Exception:
            continue

        size = len(raw)
        if size == 0:
            continue

        text = None
        for enc in ('utf-8', 'latin-1'):
            try:
                text = raw.decode(enc)
                break
            except Exception:
                pass
        if text is None:
            continue

        lines = text.splitlines()
        line_count = len(lines)
        max_len = max((len(line) for line in lines), default=0)
        long_120 = sum(1 for line in lines if len(line) > 120)
        long_180 = sum(1 for line in lines if len(line) > 180)

        nonempty = [line.strip() for line in lines if line.strip()]
        dup_ratio = 0.0
        if nonempty:
            counter = Counter(nonempty)
            duplicates = sum(count - 1 for count in counter.values() if count > 1)
            dup_ratio = duplicates / len(nonempty)

        rows.append({
            'path': str(path).replace('\\', '/'),
            'size': size,
            'lines': line_count,
            'maxlen': max_len,
            'long120': long_120,
            'long180': long_180,
            'dup_ratio': round(dup_ratio, 3),
        })
    return rows


def print_table(title, items, limit=40, sort_key=None):
    print(title)
    if sort_key is not None:
        items = sorted(items, key=sort_key, reverse=True)
    for row in items[:limit]:
        print(
            f"{row['size']:>9} | {row['lines']:>6} | {row['maxlen']:>4} | "
            f"{row['long120']:>4} | {row['dup_ratio']:.3f} | {row['path']}"
        )


if __name__ == '__main__':
    rows = scan()

    print_table('TOP_SIZE', rows, limit=40, sort_key=lambda r: r['size'])
    print_table('TOP_LINES', rows, limit=40, sort_key=lambda r: r['lines'])

    risk = [
        r for r in rows
        if (
            r['lines'] > 1200
            or r['size'] > 120000
            or r['long120'] > 200
            or r['dup_ratio'] > 0.25
        )
    ]
    print_table(
        'RISK',
        sorted(risk, key=lambda r: (r['lines'], r['size']), reverse=True),
        limit=120,
    )
