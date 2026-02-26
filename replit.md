# NUZUM (نُظُم) - Employee & Vehicle Management System

## Overview
A comprehensive Flask-based management system for employees, vehicles, attendance, accounting, and operational workflows. Built with Arabic RTL support.

## Architecture
The project follows a **Layered Modular Architecture** transitioning from legacy monolith to Clean Architecture:

- **`app.py`** — Main Flask application setup, middleware, blueprint registration
- **`main.py`** — Entry point for Gunicorn (loads app.py)
- **`core/`** — Extensions (db, login), app factory, domain models (User, Roles), scheduler, security
- **`modules/`** — Domain-driven vertical slices (employees, vehicles, attendance, etc.) each with domain/application/presentation layers
- **`routes/`** — HTTP route blueprints (legacy + modern)
- **`presentation/`** — Modern web and API delivery layers
- **`application/`** — Business services and cross-module orchestration
- **`domain/`** — Central domain model registry
- **`infrastructure/`** — Database config, cache, storage, scripts
- **`services/`** — Business logic services
- **`utils/`** — Shared utilities (Excel, PDF, Arabic text)
- **`forms/`** — WTForms form definitions
- **`templates/`** — Jinja2 HTML templates
- **`static/`** — CSS, JS, images, fonts

## Tech Stack
- **Backend:** Python 3.11, Flask 3.x, Gunicorn
- **Database:** PostgreSQL (via SQLAlchemy + Flask-Migrate)
- **Auth:** Flask-Login, PyJWT for API auth
- **Security:** CSRF (Flask-WTF), rate limiting (Flask-Limiter)
- **Reports:** ReportLab (PDF), OpenPyXL/Pandas (Excel), FPDF2
- **Integrations:** WhatsApp, SendGrid, OpenAI, Twilio

## Entry Point
- Gunicorn runs `main:app` which loads `app.py`
- `wsgi.py` exists as alternative entry using `core/app_factory.py`

## Security Notes
- `SESSION_SECRET` must be set as environment variable (no fallback)
- `LOCATION_API_KEY` must be set for external API access
- CSRF enabled globally with exemptions for specific API blueprints

## Attendance Module
- Modular architecture is active by default (7 core files + 3 auxiliary)
- Core files: `attendance_list.py`, `attendance_record.py`, `attendance_edit_delete.py`, `attendance_export.py`, `attendance_stats.py`, `attendance_circles.py`, `attendance_api.py`
- Auxiliary blueprints (registered separately): `mass_attendance.py`, `attendance_dashboard.py`, `leave_management.py`
- Legacy monolith `routes/legacy/_attendance_main.py` kept as fallback (set `ATTENDANCE_USE_MODULAR=0` to force legacy)
- Phase 1 and v1/ bridge files have been removed — only modular + legacy fallback remain

## Database
- PostgreSQL via `DATABASE_URL` environment variable
- Models defined in `core/domain/models.py` and `modules/*/domain/models.py`
- Migrations managed by Flask-Migrate (Alembic)
