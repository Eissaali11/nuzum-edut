"""I/O operations for employees (import/export/documents)."""
from .import_service import (
    process_employee_import,
    generate_sample_import_template,
    generate_empty_import_template,
    ImportResult,
)
from .export_service import (
    export_employees_excel,
    export_employees_comprehensive,
)
from .document_service import (
    upload_employee_image,
    delete_housing_image,
    DocumentResult,
)

__all__ = [
    'process_employee_import',
    'generate_sample_import_template',
    'generate_empty_import_template',
    'ImportResult',
    'export_employees_excel',
    'export_employees_comprehensive',
    'upload_employee_image',
    'delete_housing_image',
    'DocumentResult',
]
