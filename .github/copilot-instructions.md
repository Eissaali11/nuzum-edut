# NUZUM (نُظم) - AI Assistant Instructions

Welcome to the NUZUM project! This guide provides essential context and conventions to help AI agents be immediately productive in this codebase.

## 🏗️ Architecture & Project Structure

NUZUM is a Flask-based application transitioning to a Domain-Driven Design (DDD) modular architecture.

- **Domain Modules (`modules/`)**: Core business logic is organized by domain (e.g., `employees`, `vehicles`, `attendance`, `operations`). Each module contains its own `domain/models.py`, `presentation/`, and `services/`.
- **Central Models Registry (`models.py`)**: This file acts as a shim, re-exporting all domain models from their respective modules to maintain backward compatibility and ensure `flask db migrate` recognizes all tables. **Always import models from `models.py` or `core.extensions.db` to avoid circular imports.**
- **Hierarchical Routes (`routes/`)**: Routes are organized into 12 domain categories (e.g., `core/`, `hr/`, `accounting/`, `attendance/`). 
- **Refactored Wrappers**: Monolithic route files have been split into smaller, specialized files (e.g., `accounting_dashboard_routes.py`, `accounting_accounts_routes.py`). The main file (e.g., `accounting.py`) acts as a lightweight wrapper that imports and registers these sub-blueprints.
- **Helper Modules**: Complex business logic and shared functions are extracted into `*_helpers.py` files (e.g., `accounting_helpers.py`, `properties_helpers.py`).

## 🚀 Developer Workflows

- **Starting the Server**: Always use `python startup.py`. This script verifies required files, sets up environment variables, and starts the Flask server correctly. Do not run `flask run` or `python app.py` directly unless debugging specific issues.
- **Health Check**: Run `python health_check.py` to verify system health and database integrity.
- **Database**: The project uses SQLite locally (`instance/nuzum_local.db`) and MySQL in production. Use `flask db migrate` and `flask db upgrade` for schema changes.

## 📝 Coding Conventions & Patterns

- **Blueprint Registration**: When creating new routes, use Flask Blueprints. Wrap blueprint registrations in `try-except` blocks to prevent a single module failure from crashing the entire application (see `modules/vehicles/presentation/web/main_routes.py` for an example).
- **Templates**: Prefer module-specific templates (e.g., `modules/vehicles/presentation/templates/`) over global templates. The `app.jinja_loader` is configured to check module directories first.
- **Language & Localization**: The primary language for the UI, comments, and documentation is **Arabic**. Ensure HTML templates support RTL (Right-to-Left) layout.
- **Logging**: Use the structured JSON logger configured in `app.py`. Example: `logger.info("Message", extra={"user_id": current_user.id})`.
- **CSRF Protection**: Most routes are protected by `flask_wtf.csrf.CSRFProtect`. Exempt specific API routes using `csrf.exempt(blueprint)` in `app.py` if necessary.

## 🔌 Integration Points

- **WhatsApp**: Handled via `whatsapp_client.py` (`WhatsAppWrapper`). It initializes automatically if `WHATSAPP_ACCESS_TOKEN` is present in `.env`.
- **External APIs**: API routes are located in `routes/api/` and `api/v2/`. They often require specific rate limiting (`init_rate_limiter`) and security guards (`register_api_v2_guard`).
