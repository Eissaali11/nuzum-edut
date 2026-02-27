#!/usr/bin/env python3
"""Scan repository for large files and critical items.

Outputs a concise JSON-like report to stdout.
"""
import os
import sys
from pathlib import Path
from collections import defaultdict


ROOT = Path(__file__).resolve().parents[1]


def human(n):
    for unit in ['B','KB','MB','GB']:
        if n < 1024.0:
            return f"{n:.2f}{unit}"
        n /= 1024.0
    return f"{n:.2f}TB"


def find_large_files(root: Path, limit=50):
    files = []
    for p in root.rglob('*'):
        if p.is_file():
            try:
                files.append((p, p.stat().st_size))
            except Exception:
                pass
    files.sort(key=lambda x: x[1], reverse=True)
    return files[:limit]


def count_extensions(root: Path, exts=None):
    cnt = defaultdict(int)
    for p in root.rglob('*'):
        if p.is_file():
            e = p.suffix.lower()
            cnt[e] += 1
    return dict(cnt)


def check_critical_paths(root: Path):
    report = {}
    report['db'] = {'path': str(root / 'instance' / 'nuzum_local.db'), 'exists': (root / 'instance' / 'nuzum_local.db').exists()}
    report['migrations_count'] = len(list((root / 'migrations' / 'versions').glob('*.py'))) if (root / 'migrations' / 'versions').exists() else 0
    report['routes_blueprint'] = {'path': str(root / 'routes' / 'blueprint_registry.py'), 'exists': (root / 'routes' / 'blueprint_registry.py').exists()}
    report['docs_count'] = len(list((root / 'docs').rglob('*'))) if (root / 'docs').exists() else 0
    return report


def detect_blueprint_prefix_collisions(reg_path: Path):
    if not reg_path.exists():
        return []
    import re
    txt = reg_path.read_text(encoding='utf-8')
    pattern = re.compile(r"app\.register_blueprint\(([^,\)]+)(?:,\s*url_prefix\s*=\s*['\"]([^'\"]+)['\"])?")
    mapping = defaultdict(list)
    for m in pattern.finditer(txt):
        bp = m.group(1).strip()
        prefix = m.group(2) or ''
        mapping[prefix].append(bp)
    collisions = [(p, bps) for p, bps in mapping.items() if p and len(bps) > 1]
    return collisions


def search_dangerous_migration_patterns(root: Path):
    hits = []
    for p in root.rglob('migrations/versions/*.py'):
        #!/usr/bin/env python3
        """Scan repository for large files and critical items.

        Outputs a concise JSON-like report to stdout.
        """
        import os
        import sys
        from pathlib import Path
        from collections import defaultdict


        ROOT = Path(__file__).resolve().parents[1]


        def human(n):
            for unit in ['B','KB','MB','GB']:
                if n < 1024.0:
                    return f"{n:.2f}{unit}"
                n /= 1024.0
            return f"{n:.2f}TB"


        def find_large_files(root: Path, limit=50):
            files = []
            for p in root.rglob('*'):
                if p.is_file():
                    try:
                        files.append((p, p.stat().st_size))
                    except Exception:
                        pass
            files.sort(key=lambda x: x[1], reverse=True)
            return files[:limit]


        def count_extensions(root: Path, exts=None):
            cnt = defaultdict(int)
            for p in root.rglob('*'):
                if p.is_file():
                    e = p.suffix.lower()
                    cnt[e] += 1
            return dict(cnt)


        def check_critical_paths(root: Path):
            report = {}
            report['db'] = {'path': str(root / 'instance' / 'nuzum_local.db'), 'exists': (root / 'instance' / 'nuzum_local.db').exists()}
            report['migrations_count'] = len(list((root / 'migrations' / 'versions').glob('*.py'))) if (root / 'migrations' / 'versions').exists() else 0
            report['routes_blueprint'] = {'path': str(root / 'routes' / 'blueprint_registry.py'), 'exists': (root / 'routes' / 'blueprint_registry.py').exists()}
            report['docs_count'] = len(list((root / 'docs').rglob('*'))) if (root / 'docs').exists() else 0
            return report


        def detect_blueprint_prefix_collisions(reg_path: Path):
            if not reg_path.exists():
                return []
            import re
            txt = reg_path.read_text(encoding='utf-8')
            pattern = re.compile(r"app\.register_blueprint\(([^,\)]+)(?:,\s*url_prefix\s*=\s*['\"]([^'\"]+)['\"])?")
            mapping = defaultdict(list)
            for m in pattern.finditer(txt):
                bp = m.group(1).strip()
                prefix = m.group(2) or ''
                mapping[prefix].append(bp)
            collisions = [(p, bps) for p, bps in mapping.items() if p and len(bps) > 1]
            return collisions


        def search_dangerous_migration_patterns(root: Path):
            hits = []
            for p in root.rglob('migrations/versions/*.py'):
                try:
                    txt = p.read_text(encoding='utf-8')
                    if 'drop_table' in txt or 'drop_column' in txt or 'ALTER TABLE' in txt:
                        hits.append(str(p))
                except Exception:
                    pass
            return hits


        def main():
            print('REPO_SCAN_ROOT:', str(ROOT))
            print('\nTop large files:')
            for p, s in find_large_files(ROOT, limit=40):
                print(f" - {human(s):8}  {p.relative_to(ROOT)}")

            print('\nFile type counts (top 10):')
            exts = count_extensions(ROOT)
            for k, v in sorted(exts.items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f" - {k or '[noext]':6} : {v}")

            print('\nCritical paths:')
            crit = check_critical_paths(ROOT)
            for k, v in crit.items():
                print(f" - {k}: {v}")

            print('\nBlueprint prefix collisions:')
            collisions = detect_blueprint_prefix_collisions(ROOT / 'routes' / 'blueprint_registry.py')
            if collisions:
                for prefix, bps in collisions:
                    print(f" - COLLISION prefix='{prefix}' blueprints={bps}")
            else:
                print(' - None found')

            print('\nPotentially dangerous migration files (contain drop/ALTER):')
            for p in search_dangerous_migration_patterns(ROOT):
                print(' -', p)

            print('\nSummary:')
            print(' - Total files scanned:', sum(exts.values()))
            print(' - Suggestion: Backup instance/ and large files before schema changes')


        if __name__ == '__main__':
            main()
            print('REPO_SCAN_ROOT:', str(ROOT))
            print('\nTop large files:')
            for p, s in find_large_files(ROOT, limit=40):
                print(f" - {human(s):8}  {p.relative_to(ROOT)}")

            print('\nFile type counts (top 10):')
            exts = count_extensions(ROOT)
            for k, v in sorted(exts.items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f" - {k or '[noext]':6} : {v}")

            print('\nCritical paths:')
            crit = check_critical_paths(ROOT)
            for k, v in crit.items():
                print(f" - {k}: {v}")

            print('\nBlueprint prefix collisions:')
            collisions = detect_blueprint_prefix_collisions(ROOT / 'routes' / 'blueprint_registry.py')
            if collisions:
                for prefix, bps in collisions:
                    print(f" - COLLISION prefix='{prefix}' blueprints={bps}")
            else:
                print(' - None found')

            print('\nPotentially dangerous migration files (contain drop/ALTER):')
            for p in search_dangerous_migration_patterns(ROOT):
                print(' -', p)

            print('\nSummary:')
            print(' - Total files scanned:', sum(exts.values()))
            print(' - Suggestion: Backup instance/ and large files before schema changes')


        if __name__ == '__main__':
            main()
