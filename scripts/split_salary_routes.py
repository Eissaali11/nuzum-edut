from pathlib import Path
import re

base_dir = Path(r'd:/nuzm/routes/salaries_mgmt/v1')
source_path = base_dir / 'salary_routes.py'
text = source_path.read_text(encoding='utf-8')
lines = text.splitlines(keepends=True)

route_starts = [i for i, line in enumerate(lines) if line.startswith('@salaries_bp.route(')]
if not route_starts:
    raise SystemExit('No routes found in salary_routes.py')

preamble = ''.join(lines[:route_starts[0]])

blocks = []
for idx, start in enumerate(route_starts):
    end = route_starts[idx + 1] if idx + 1 < len(route_starts) else len(lines)
    block = ''.join(lines[start:end]).strip() + '\n\n'
    match = re.search(r'^def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', block, re.M)
    if not match:
        raise SystemExit(f'No function definition found for block starting at line {start + 1}')
    blocks.append((match.group(1), block))

mapping = {
    'salary_core.py': {
        'index',
        'report',
    },
    'salary_ops.py': {
        'create', 'edit', 'calculate_from_attendance', 'bulk_calculate_attendance',
        'confirm_delete', 'delete', 'save_all_smart', 'save_smart', 'validate_incomplete',
    },
    'salary_io.py': {
        'import_excel', 'export_excel', 'report_pdf', 'salary_notification_pdf',
        'comprehensive_report', 'export_simple_employees_salary',
    },
    'salary_approval.py': {
        'share_salary_via_whatsapp', 'share_deduction_via_whatsapp',
        'salary_notification_whatsapp', 'salary_deduction_notification_whatsapp',
        'batch_deduction_notifications', 'batch_salary_notifications',
    },
}

found = {name for name, _ in blocks}
assigned = set().union(*mapping.values())
unassigned = sorted(found - assigned)
if unassigned:
    raise SystemExit(f'Unassigned route functions: {unassigned}')

# Shared preamble
(base_dir / 'salary_base.py').write_text(
    '"""Shared salaries v1 blueprint/context."""\n\n' + preamble.strip() + '\n',
    encoding='utf-8',
)

# Route modules
for file_name, functions in mapping.items():
    parts = [
        f'"""{file_name} - decomposed salaries routes."""\n\n',
        'from .salary_base import *\n\n',
    ]
    for name, block in blocks:
        if name in functions:
            parts.append(block)
    (base_dir / file_name).write_text(''.join(parts), encoding='utf-8')

aggregator = '''"""Salaries routes v1 aggregator (atomic decomposed modules)."""

from .salary_base import salaries_bp

from . import salary_core  # noqa: F401
from . import salary_ops  # noqa: F401
from . import salary_io  # noqa: F401
from . import salary_approval  # noqa: F401

__all__ = ['salaries_bp']
'''
source_path.write_text(aggregator, encoding='utf-8')

print('decomposition_done', len(blocks), 'routes')
