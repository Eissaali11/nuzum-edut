from flask import Blueprint

def register_salaries_routes(app):
    try:
        from .v1.salary_routes import salaries_bp as original_bp
        app.register_blueprint(original_bp)
    except ImportError:
        pass

try:
    from .v1.salary_routes import salaries_bp
except ImportError:
    salaries_bp = Blueprint('salaries', __name__)

__all__ = ['salaries_bp', 'register_salaries_routes']
