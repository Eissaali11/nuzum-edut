"""Mobile identity routes (authentication and social login)."""

from .auth_routes import register_auth_routes
from .google_routes import register_google_routes

__all__ = [
	"register_auth_routes",
	"register_google_routes",
]

