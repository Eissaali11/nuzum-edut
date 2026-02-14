# Project Structure Tree Map & Migration Status

**Generated:** 2025-02-10  
**Purpose:** Clarify the split between the new `presentation/web/` (and `application/`) layers and the legacy `routes/` layer, and list what is migrated vs still coupled in legacy (especially `routes/mobile.py`).

---

## 1. High-Level Tree Map (Relevant Directories)

```
nuzm/
├── app.py                          # Legacy entry: registers all routes.* blueprints (incl. mobile); no presentation
├── wsgi.py                         # May use app or create_app — check which is used in production
│
├── core/
│   ├── app_factory.py              # New entry: create_app() → presentation first, then legacy subset
│   ├── extensions.py
│   └── ...
│
├── presentation/
│   └── web/
│       ├── __init__.py
│       ├── routes.py               # web_bp  → "/" (home)
│       ├── api_routes.py           # api_bp  → /api (e.g. /api/health)
│       ├── auth_routes.py          # auth_bp → /auth
│       │
│       ├── vehicles/               # NEW — Vertical Slice (vehicles)
│       │   ├── __init__.py         # exports vehicles_web_bp
│       │   ├── routes.py           # vehicles_web_bp → /app/vehicles (list); uses application.vehicles.services
│       │   ├── handover_routes.py  # register_handover_routes(vehicles_bp) → mounted on legacy vehicles_bp
│       │   ├── workshop_routes.py # register_workshop_routes(vehicles_bp)
│       │   └── accident_routes.py  # register_accident_routes(vehicles_bp)
│       │
│       ├── employees/              # NEW — Vertical Slice (employees)
│       │   ├── __init__.py         # exports employees_bp (employees_web)
│       │   └── routes.py           # employees_bp → /app/employees (list); uses application.employees.services
│       │
│       ├── templates/              # presentation/web templates (layout, pages, vehicles, employees, auth, macros)
│       └── static/                 # CSS, fonts
│
├── application/                    # Application services (business logic used by presentation or legacy)
│   ├── __init__.py
│   ├── vehicles/
│   │   ├── __init__.py
│   │   ├── services.py            # list_vehicles_service, handover context/actions
│   │   ├── workshop_services.py   # create_workshop_record_action, vehicle_already_in_workshop
│   │   └── accident_services.py    # create_accident_record_action
│   ├── employees/
│   │   ├── __init__.py
│   │   └── services.py            # list_employees_page_data
│   └── operations/
│       ├── __init__.py
│       └── services.py            # get_handover_approval_state (used by vehicles handover logic)
│
├── routes/                         # LEGACY — 57 route modules; most logic still here
│   ├── __init__.py
│   ├── vehicles.py                # vehicles_bp (/vehicles); imports presentation.web.vehicles.* register_*; uses application.vehicles.*
│   ├── mobile.py                  # mobile_bp (/mobile) — HUGE: 7400+ lines, all logic coupled
│   ├── employees.py
│   ├── dashboard.py
│   ├── departments.py
│   ├── attendance.py
│   ├── salaries.py
│   ├── documents.py
│   ├── reports.py
│   ├── auth.py
│   ├── fees_costs.py
│   ├── api.py
│   ├── users.py
│   ├── operations.py              # create_operation_request used by vehicles + mobile
│   ├── ... (see list below)
│   └── (50+ other blueprint files)
│
├── domain/                         # Domain models (used by application layer)
│   ├── vehicles/
│   │   ├── models.py
│   │   └── handover_models.py
│   └── employees/
│       └── models.py
│
├── models.py                       # Legacy/global models (still used by routes/* and mobile.py)
├── infrastructure/
│   └── storage/                   # save_base64_image, save_uploaded_file used by app layer
├── utils/                          # Helpers (audit, vehicle helpers, PDF, etc.)
└── ...
```

---

## 2. Split: New vs Legacy

| Aspect | New (presentation + application) | Legacy (routes/) |
|--------|-----------------------------------|------------------|
| **Entry** | `core.app_factory.create_app()` | `app.py` (direct `app = Flask(...)`) |
| **Web UI** | `presentation/web`: `/`, `/app/vehicles`, `/app/employees`, `/auth`, `/api` | `routes/*`: `/dashboard`, `/employees`, `/vehicles`, `/mobile`, etc. |
| **Templates** | `presentation/web/templates/` (layout/base, vehicles/list, employees/list) | Root `templates/` |
| **Vehicles** | `presentation/web/vehicles/`: list + handover/workshop/accident *routes*; logic in `application/vehicles/*` | `routes/vehicles.py`: bulk of vehicle CRUD, reports, PDF, state updates; *registers* handover/workshop/accident from presentation |
| **Employees** | `presentation/web/employees/`: list only; data from `application/employees/services` | `routes/employees.py`: full CRUD, import/export, tracking, etc. |
| **Registration** | In `app_factory`: web_bp, api_bp, auth_bp, employees_web_bp, vehicles_web_bp; then legacy subset | In `app.py`: all blueprints (incl. mobile, landing, admin); no presentation blueprints |

**Important:** The legacy `vehicles_bp` (`routes/vehicles.py`) both:
- Defines most vehicle routes and logic (5500+ lines), and
- Imports and mounts the new slice routes: `register_handover_routes(vehicles_bp)`, `register_workshop_routes(vehicles_bp)`, `register_accident_routes(vehicles_bp)`.

So handover/workshop/accident *endpoints* live on the same blueprint prefix `/vehicles` but are implemented in `presentation/web/vehicles/*` and call `application/vehicles/*`.

---

## 3. Business Modules: Migrated to application/services/

| Module | Location | Used by |
|--------|----------|---------|
| **Vehicles** | `application/vehicles/services.py` | `presentation/web/vehicles/routes.py` (list), handover/workshop flows |
| | `application/vehicles/workshop_services.py` | `presentation/web/vehicles/workshop_routes.py`, `routes/vehicles.py` |
| | `application/vehicles/accident_services.py` | `presentation/web/vehicles/accident_routes.py` |
| **Employees** | `application/employees/services.py` | `presentation/web/employees/routes.py` (list only) |
| **Operations** | `application/operations/services.py` | Vehicles handover approval state (used by application/services, not directly by routes) |

**Summary:** Migrated to application layer: **vehicles** (list, handover, workshop, accident), **employees** (list page data), **operations** (handover approval state). No other business domains (attendance, salaries, documents, reports, fees, users, etc.) have been moved to `application/` yet.

---

## 4. Still Coupled in Legacy Route Files (Especially routes/mobile.py)

`routes/mobile.py` is a single ~7,400-line file that contains **all** of the following **inside the route layer** (no extraction to application/services):

### 4.1 Auth & Session
- `LoginForm`, `splash`, `root`, `index`, `login`, `google_login`, `logout`, `forgot_password`

### 4.2 Employees (mobile)
- `employees`, `add_employee`, `employee_details`, `edit_employee`

### 4.3 Attendance
- `attendance`, `attendance_dashboard`, `export_attendance`, `add_attendance`, `edit_attendance`, `delete_attendance`

### 4.4 Departments
- `departments`, `add_department`, `department_details`

### 4.5 Salaries
- `salaries`, `add_salary`, `salary_details`, `edit_salary`

### 4.6 Documents
- `documents_dashboard`, `documents`, `add_document`, `document_details`, `update_document_expiry`

### 4.7 Reports
- `reports`, `report_employees`, `report_attendance`, `report_salaries`, `share_salary_via_whatsapp`, `report_documents`, `report_vehicles`, `report_fees`

### 4.8 Vehicles (mobile — full CRUD and workflows)
- `vehicles`, `vehicle_details`, `edit_vehicle`, `delete_vehicle`, `upload_vehicle_document`, `delete_vehicle_document`, `add_vehicle`
- `maintenance_details`, `edit_maintenance`, `vehicle_documents`, `delete_maintenance`
- `save_base64_image`, `save_uploaded_file`, `save_file`
- `get_employee_details_api`, `create_handover_mobile`, `edit_handover_mobile`, `save_as_next_handover_mobile`
- `mobile_vehicle_checklist_pdf`, `add_vehicle_checklist`
- `fees_old`, `add_fee`, `edit_fee`, `mark_fee_as_paid`, `fee_details`
- `notifications`, `mark_notification_as_read`, `mark_all_notifications_as_read`, `delete_notification`
- `settings`, `profile`, `change_password`, `terms`, `privacy`, `contact`, `offline`, `check_connection`
- `tracking_status`
- **Users:** `users_new`, `add_user_new`, `user_details_new`, `edit_user_new`, `delete_user_new`
- **Fees (new):** `fees_new`, `notifications_new`
- **Handover/workshop/inspection (mobile):** `create_handover`, `view_handover`, `handover_pdf`, `create_periodic_inspection`, `create_safety_check`, `test_workshop_save`, `add_workshop_record`, `edit_workshop_record`, `delete_workshop_record`, `view_workshop_details`
- **External auth:** `view_external_authorization`, `edit_external_authorization`, `delete_external_authorization`, `create_external_authorization`, `approve_external_authorization`, `reject_external_authorization`
- **Misc:** `delete_handover`, `get_current_driver_info`, `quick_vehicle_return`, `get_vehicle_driver_info`, `edit_workshop_mobile`
- **Operations:** `operations_dashboard`, `operations_list`, `operation_details`, `operations_notifications`

### 4.9 Tracking & Geo
- `mobile_tracking`, `geofence_details`, `get_live_locations`

### 4.10 Helpers (in same file)
- `update_vehicle_driver` (also in routes/vehicles.py), `log_audit`; mobile imports `update_vehicle_state`, `update_vehicle_driver` from `routes.vehicles` and `create_operation_request` from `routes.operations`.

**Summary:** None of the mobile-specific business logic has been moved to `application/`. All of it lives in `routes/mobile.py`, with direct use of `models`, `db`, and helpers from `routes.vehicles` and `routes.operations`.

---

## 5. Legacy routes/ Directory (Full List of Blueprint Files)

- `api.py`, `api_accident_reports.py`, `api_employee_requests.py`, `api_external.py`, `api_external_safety.py`
- `accounting.py`, `accounting_analytics.py`, `accounting_extended.py`
- `admin_dashboard.py`, `analytics_direct.py`, `analytics_real.py`, `analytics_simple.py`, `ai_services_simple.py`
- `attendance.py`, `attendance_api.py`, `attendance_dashboard.py`
- `database_backup.py`, `dashboard.py`, `departments.py`, `device_assignment.py`, `device_management.py`
- `documents.py`, `drive_browser.py`, `e_invoicing.py`, `email_queue.py`, `employee_portal.py`, `employee_requests.py`
- `employees.py`, `enhanced_reports.py`, `external_safety.py`, `fees_costs.py`, `geofences.py`
- `google_drive_settings.py`, `insights.py`, `integrated_management.py`, `integrated_simple.py`
- `landing.py`, `landing_admin.py`, `mass_attendance.py`, `mobile.py`, `mobile_devices.py`
- `notifications.py`, `operations.py`, `powerbi_dashboard.py`, `properties.py`
- `reports.py`, `salaries.py`, `sim_management.py`, `simple_analytics.py`
- `users.py`, `vehicle_operations.py`, `vehicles.py`, `vehicles_temp.py`, `voicehub.py`
- `workshop_reports.py`, `auth.py`

All of these are still legacy; only the vehicles and employees *slices* in `presentation/web` use `application/` services, and only vehicles (handover/workshop/accident) are partially delegated from `routes/vehicles.py`.

---

## 6. Recommendations (Concise)

1. **Tree map:** Use the tree above to onboard and to see where new code should go (presentation + application vs routes).
2. **Migration priority:** Next application modules to extract: **attendance**, **salaries**, **documents**, **operations** (full flow), then mobile-specific use cases.
3. **Mobile:** Treat `routes/mobile.py` as the top technical-debt target: split by domain (e.g. `application/attendance/`, `application/salaries/`) and add thin `presentation/web/mobile/` or keep mobile routes but delegate to application services.
4. **Single entry:** Decide whether the app runs from `app.py` or `create_app()` (e.g. wsgi) and document it; unify blueprint registration so both paths see the same set of routes if needed.
