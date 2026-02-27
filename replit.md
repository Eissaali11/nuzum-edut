# NUZUM (نُظُم) - Employee & Vehicle Management System

## Overview
A comprehensive Flask-based management system for employees, vehicles, attendance, accounting, and operational workflows. Built with Arabic RTL support.

## Architecture
The project follows a **Layered Modular Architecture** transitioning from legacy monolith to Clean Architecture:

- **`app.py`** — Main Flask application setup, middleware, blueprint registration
- **`main.py`** — Entry point for Gunicorn (loads app.py); `wsgi.py` deleted
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

## Security Notes
- `SESSION_SECRET` must be set as environment variable (no fallback)
- `LOCATION_API_KEY` must be set for external API access
- CSRF enabled globally with exemptions for specific API blueprints
- Static upload serving uses `safe_join` + `realpath` validation to prevent path traversal

## File Uploads
- All uploads stored in `static/uploads/` (absolute path via `app.config["UPLOAD_FOLDER"]`)
- Employee images: `static/uploads/employees/`
- Vehicle files: `static/uploads/vehicles/` (registration_forms, plates, insurance)
- Other: handovers, maintenance, safety_checks, workshop, properties, accidents, invoices
- DB stores relative paths like `uploads/employees/...` or `static/uploads/vehicles/...`

## Attendance Module
- Modular architecture only (legacy fallback removed, archived to `docs/legacy_archive/attendance/`)
- Core files: `attendance_list.py`, `attendance_record.py`, `attendance_edit_delete.py`, `attendance_export.py`, `attendance_stats.py`, `attendance_circles.py`, `attendance_api.py`
- Auxiliary blueprints (registered separately): `mass_attendance.py`, `attendance_dashboard.py`, `leave_management.py`
- `__init__.py` builds a single modular blueprint with lazy initialization

## Payroll Module
- Routes: `routes/admin/payroll_admin.py` (blueprint: `payroll`)
- Dashboard (`/payroll/dashboard`): Professional design with 4 donut charts (status distribution, department salaries, financial breakdown, employee distribution)
- Review (`/payroll/review`): Filterable table with summary donut chart, batch approve/reject, modal dialogs
- Excel Export (`/payroll/review/export-excel`): Professional openpyxl export with navy/teal styling, KPI summary row, attendance deduction columns, totals row, signature fields (accountant, HR manager, GM)
- Uses Chart.js 4.x via CDN for all charts
- Models: `PayrollRecord`, `PayrollConfiguration`, `BankTransferFile`, `PayrollHistory` in `modules/payroll/domain/models.py`

## Admin Access Pattern
- `User.is_admin` DB column is `None` for all users; use `_is_admin_role()` method which checks both `is_admin` flag AND `role == 'admin'`
- Templates must use `current_user._is_admin_role()` not `current_user.is_admin`
- Analytics routes use a local `admin_required` decorator that calls `_is_admin_role()`

## Responsive Design (Mobile)
- Master responsive CSS: `static/css/nuzum_mobile.css` (linked in `layout.html`)
- Table-to-card transformation: Tables with class `nuzum-responsive-table` + `data-label` attributes on `<td>` elements convert to cards on mobile (<768px)
- Dashboard: Stats cards use `col-6` on mobile (2 per row), charts stack full-width
- Sidebar: Fixed overlay on mobile with toggle button, backdrop, auto-close on link click
- Touch targets: All buttons enforce minimum 40-44px height on mobile
- Applied to: Dashboard, Employee list, Vehicle list, Operations list

## Project Profitability Module (Phase 5)
- **Models**: `ProjectContract`, `ContractResource` in `modules/accounting/domain/profitability_models.py`
- **Service**: `modules/accounting/application/profitability_service.py` — Quad-Sync calculation (HR + Fleet + Revenue + Attendance)
- **Routes**: `routes/accounting/profitability_routes.py` — Two blueprints: `profitability` (dashboard, report, Excel export) and `contracts` (CRUD for contracts and billing rates)
- **Templates**: `templates/accounting/profitability/` (dashboard, report), `templates/accounting/contracts/` (index, form, resources) — premium redesigned UI
- **Sidebar Links**: المحاسبة, إدارة العقود والأسعار, ربحية المشاريع, توزيع الفواتير — all use `_is_admin_role()` check
- **Vehicle.monthly_fixed_cost**: Added to Vehicle model — aggregated monthly cost (installment + insurance + maintenance)
- **ContractResource.billing_rate**: What the client pays per employee (monthly or daily)
- **Profitability = Revenue (billing rates) - Costs (salary + GOSI + vehicle + overhead + housing)**
- Chart.js charts: Revenue vs Cost bar chart, Margin % donut chart
- Excel export: Navy/teal styling matching payroll exports, KPI summary, per-employee breakdown, totals row, signature fields

## Database
- PostgreSQL via `DATABASE_URL` environment variable
- Models defined in `core/domain/models.py` and `modules/*/domain/models.py`
- Migrations managed by Flask-Migrate (Alembic)
