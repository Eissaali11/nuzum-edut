"""Mobile document and inspection routes."""

from .document_routes import register_document_routes
from .documents_ui_routes import register_documents_ui_routes
from .inspection_routes import register_inspection_routes

__all__ = [
	"register_document_routes",
	"register_documents_ui_routes",
	"register_inspection_routes",
]

