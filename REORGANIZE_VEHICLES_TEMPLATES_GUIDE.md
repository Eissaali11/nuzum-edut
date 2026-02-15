# 🔧 Vehicle Templates Reorganization Guide

## Overview
This guide provides step-by-step instructions to reorganize all 68 HTML templates in `modules/vehicles/presentation/templates/vehicles/` into logical subdirectories.

---

## ✅ Step 1: Create Subdirectories

Open PowerShell in: `d:\nuzm\modules\vehicles\presentation\templates\vehicles`

```powershell
# Create all subdirectories
$dirs = @('modals', 'handovers', 'forms', 'views', 'reports', 'utilities')
foreach ($dir in $dirs) {
    New-Item -ItemType Directory -Name $dir -Force
    Write-Host "✓ Created: $dir" -ForegroundColor Green
}
```

---

## ✅ Step 2: Move Files to Subdirectories

### 📂 Move to `modals/` (7 files)
```powershell
Move-Item confirm_delete.html modals\ -Force
Move-Item confirm_delete_handovers.html modals\ -Force
Move-Item confirm_delete_inspection.html modals\ -Force
Move-Item confirm_delete_safety_check.html modals\ -Force
Move-Item confirm_delete_single_handover.html modals\ -Force
Move-Item confirm_delete_workshop.html modals\ -Force
Move-Item confirm_delete_workshop_image.html modals\ -Force
```

### 📂 Move to `handovers/` (12 files)
```powershell
Move-Item handover_create.html handovers\ -Force
Move-Item handover_create_refactored.html handovers\ -Force
Move-Item handover_form_view.html handovers\ -Force
Move-Item handover_pdf_public.html handovers\ -Force
Move-Item handover_report.html handovers\ -Force
Move-Item handover_report1.html handovers\ -Force
Move-Item handover_simple_view.html handovers\ -Force
Move-Item handover_view.html handovers\ -Force
Move-Item handover_view_public.html handovers\ -Force
Move-Item handovers_list.html handovers\ -Force
Move-Item edit_handover.html handovers\ -Force
Move-Item update_handover_link.html handovers\ -Force
```

### 📂 Move to `forms/` (15 files)
```powershell
Move-Item create.html forms\ -Force
Move-Item edit.html forms\ -Force
Move-Item create_accident.html forms\ -Force
Move-Item edit_accident.html forms\ -Force
Move-Item create_external_authorization.html forms\ -Force
Move-Item edit_external_authorization.html forms\ -Force
Move-Item edit_documents.html forms\ -Force
Move-Item inspection_create.html forms\ -Force
Move-Item inspection_edit.html forms\ -Force
Move-Item project_create.html forms\ -Force
Move-Item project_edit.html forms\ -Force
Move-Item rental_create.html forms\ -Force
Move-Item rental_edit.html forms\ -Force
Move-Item safety_check_create.html forms\ -Force
Move-Item safety_check_edit.html forms\ -Force
Move-Item workshop_create.html forms\ -Force
Move-Item workshop_edit.html forms\ -Force
```

### 📂 Move to `views/` (15 files)
```powershell
Move-Item view.html views\ -Force
Move-Item index.html views\ -Force
Move-Item 1view.html views\ -Force
Move-Item 3view.html views\ -Force
Move-Item 4view.html views\ -Force
Move-Item view_cards.html views\ -Force
Move-Item view_clean.html views\ -Force
Move-Item view_documents.html views\ -Force
Move-Item view_external_authorization.html views\ -Force
Move-Item view_modern.html views\ -Force
Move-Item view_simple.html views\ -Force
Move-Item view_with_sidebar.html views\ -Force
Move-Item accident_details.html views\ -Force
Move-Item workshop_details.html views\ -Force
Move-Item workshop_image_view.html views\ -Force
```

### 📂 Move to `reports/` (6 files)
```powershell
Move-Item dashboard.html reports\ -Force
Move-Item dashboard_stats.html reports\ -Force
Move-Item reports.html reports\ -Force
Move-Item detailed_list.html reports\ -Force
Move-Item print_workshop.html reports\ -Force
Move-Item share_workshop.html reports\ -Force
```

### 📂 Move to `utilities/` (13 files)
```powershell
Move-Item delete_accident.html utilities\ -Force
Move-Item drive_files.html utilities\ -Force
Move-Item drive_management.html utilities\ -Force
Move-Item expired_documents.html utilities\ -Force
Move-Item valid_documents.html utilities\ -Force
Move-Item import_vehicles.html utilities\ -Force
Move-Item inspections.html utilities\ -Force
Move-Item license_image.html utilities\ -Force
Move-Item safety_checks.html utilities\ -Force
```

---

## ✅ Step 3: Update Backend Routes

### File: `modules/vehicles/presentation/web/vehicle_routes.py`

```python
# Line 58-59: create.html
"vehicles/create.html" → "vehicles/forms/create.html"

# Line 74: index.html
"vehicles/index.html" → "vehicles/views/index.html"

# Line 82-83: expired_documents.html
"vehicles/expired_documents.html" → "vehicles/utilities/expired_documents.html"

# Line 106: view.html
"vehicles/view.html" → "vehicles/views/view.html"

# Line 146: edit.html
"vehicles/edit.html" → "vehicles/forms/edit.html"

# Line 161: dashboard.html
"vehicles/dashboard.html" → "vehicles/reports/dashboard.html"

# Line 180: confirm_delete.html
"vehicles/confirm_delete.html" → "vehicles/modals/confirm_delete.html"
```

### File: `modules/vehicles/presentation/web/handover_routes.py`

```python
# Line 38-39: handover_create.html
"vehicles/handover_create.html" → "vehicles/handovers/handover_create.html"

# Line 236: handover_create.html (edit mode)
"vehicles/handover_create.html" → "vehicles/handovers/handover_create.html"

# Line 265: handover_view.html
"vehicles/handover_view.html" → "vehicles/handovers/handover_view.html"

# Line 289: confirm_delete_handovers.html
"vehicles/confirm_delete_handovers.html" → "vehicles/modals/confirm_delete_handovers.html"

# Line 350: handover_pdf_public.html
"vehicles/handover_pdf_public.html" → "vehicles/handovers/handover_pdf_public.html"

# Line 390: handover_form_view.html
"vehicles/handover_form_view.html" → "vehicles/handovers/handover_form_view.html"

# Line 420: update_handover_link.html
"vehicles/update_handover_link.html" → "vehicles/handovers/update_handover_link.html"

# Line 428: confirm_delete_single_handover.html
"vehicles/confirm_delete_single_handover.html" → "vehicles/modals/confirm_delete_single_handover.html"
```

### File: `modules/vehicles/presentation/web/accident_routes.py`

```python
# Line 60: create_accident.html
"vehicles/create_accident.html" → "vehicles/forms/create_accident.html"

# Line 89: edit_accident.html
"vehicles/edit_accident.html" → "vehicles/forms/edit_accident.html"

# Line 114: delete_accident.html
"vehicles/delete_accident.html" → "vehicles/utilities/delete_accident.html"
```

### File: `modules/vehicles/presentation/web/workshop_routes.py`

```python
# Line 77: workshop_create.html
"vehicles/workshop_create.html" → "vehicles/forms/workshop_create.html"

# Line 177: workshop_edit.html
"vehicles/workshop_edit.html" → "vehicles/forms/workshop_edit.html"

# Line 197: workshop_details.html
"vehicles/workshop_details.html" → "vehicles/views/workshop_details.html"

# Line 210: confirm_delete_workshop_image.html
"vehicles/confirm_delete_workshop_image.html" → "vehicles/modals/confirm_delete_workshop_image.html"

# Line 240: confirm_delete_workshop.html
"vehicles/confirm_delete_workshop.html" → "vehicles/modals/confirm_delete_workshop.html"

# Line 301: share_workshop.html
"vehicles/share_workshop.html" → "vehicles/reports/share_workshop.html"

# Line 323: print_workshop.html
"vehicles/print_workshop.html" → "vehicles/reports/print_workshop.html"

# Line 341: workshop_image_view.html
"vehicles/workshop_image_view.html" → "vehicles/views/workshop_image_view.html"
```

### File: `modules/vehicles/presentation/web/vehicle_extra_routes.py`

```python
# Line 56: view_documents.html
'vehicles/view_documents.html' → 'vehicles/views/view_documents.html'

# Line 189: edit_documents.html
'vehicles/edit_documents.html' → 'vehicles/forms/edit_documents.html'

# Line 289: rental_create.html
'vehicles/rental_create.html' → 'vehicles/forms/rental_create.html'

# Line 338: rental_edit.html
'vehicles/rental_edit.html' → 'vehicles/forms/rental_edit.html'

# Line 395: project_create.html
'vehicles/project_create.html' → 'vehicles/forms/project_create.html'

# Line 448: project_edit.html
'vehicles/project_edit.html' → 'vehicles/forms/project_edit.html'

# Line 487: reports.html
'vehicles/reports.html' → 'vehicles/reports/reports.html'

# Line 596: detailed_list.html
'vehicles/detailed_list.html' → 'vehicles/reports/detailed_list.html'

# Line 634: inspections.html
'vehicles/inspections.html' → 'vehicles/utilities/inspections.html'

# Line 694: inspection_create.html
'vehicles/inspection_create.html' → 'vehicles/forms/inspection_create.html'

# Line 738: inspection_edit.html
'vehicles/inspection_edit.html' → 'vehicles/forms/inspection_edit.html'

# Line 756: confirm_delete_inspection.html
'vehicles/confirm_delete_inspection.html' → 'vehicles/modals/confirm_delete_inspection.html'

# Line 791: safety_checks.html
'vehicles/safety_checks.html' → 'vehicles/utilities/safety_checks.html'

# Line 867: safety_check_create.html
'vehicles/safety_check_create.html' → 'vehicles/forms/safety_check_create.html'

# Line 931: safety_check_edit.html
'vehicles/safety_check_edit.html' → 'vehicles/forms/safety_check_edit.html'

# Line 950: confirm_delete_safety_check.html
'vehicles/confirm_delete_safety_check.html' → 'vehicles/modals/confirm_delete_safety_check.html'

# Line 1030: edit_external_authorization.html
'vehicles/edit_external_authorization.html' → 'vehicles/forms/edit_external_authorization.html'

# Line 1201: handovers_list.html
'vehicles/handovers_list.html' → 'vehicles/handovers/handovers_list.html'

# Line 1322: license_image.html
'vehicles/license_image.html' → 'vehicles/utilities/license_image.html'

# Line 1376: drive_files.html
'vehicles/drive_files.html' → 'vehicles/utilities/drive_files.html'

# Line 1405, 1410, 1427: drive_management.html
'vehicles/drive_management.html' → 'vehicles/utilities/drive_management.html'

# Line 1570: import_vehicles.html
'vehicles/import_vehicles.html' → 'vehicles/utilities/import_vehicles.html'

# Line 1682: create_external_authorization.html
'vehicles/create_external_authorization.html' → 'vehicles/forms/create_external_authorization.html'

# Line 1694: view_external_authorization.html
'vehicles/view_external_authorization.html' → 'vehicles/views/view_external_authorization.html'

# Line 1705: valid_documents.html
'vehicles/valid_documents.html' → 'vehicles/utilities/valid_documents.html'

# Line 1737: edit_documents.html (duplicate)
'vehicles/edit_documents.html' → 'vehicles/forms/edit_documents.html'
```

---

## ✅ Step 4: Update Template Include Paths

Search all HTML files in `modules/vehicles/presentation/templates/vehicles/` and its subdirectories for these patterns:

### Update Pattern 1: Partials
```html
<!-- FIND -->
{% include 'vehicles/_

<!-- REPLACE WITH -->
{% include 'vehicles/partials/_
```

### Update Pattern 2: Handover includes
```html
<!-- FIND -->
{% include 'vehicles/handover_

<!-- REPLACE WITH -->
{% include 'vehicles/handovers/handover_
```

### Update Pattern 3: Modal includes
```html
<!-- FIND -->
{% include 'vehicles/confirm_delete

<!-- REPLACE WITH -->
{% include 'vehicles/modals/confirm_delete
```

### Update Pattern 4: View includes
```html
<!-- FIND -->
{% include 'vehicles/view_

<!-- REPLACE WITH -->
{% include 'vehicles/views/view_
```

### Update Pattern 5: Dashboard/Reports includes
```html
<!-- FIND -->
{% include 'vehicles/dashboard

<!-- REPLACE WITH -->
{% include 'vehicles/reports/dashboard
```

---

## ✅ Step 5: Verification Commands

### Check directory structure
```powershell
tree /F modules\vehicles\presentation\templates\vehicles
```

### Verify no files remain in root
```powershell
# Should return 0 HTML files (only directories)
(Get-ChildItem -Path "modules\vehicles\presentation\templates\vehicles\*.html").Count
```

### Count files in each subdirectory
```powershell
Write-Host "modals: $((Get-ChildItem modals\*.html).Count)"
Write-Host "handovers: $((Get-ChildItem handovers\*.html).Count)"
Write-Host "forms: $((Get-ChildItem forms\*.html).Count)"
Write-Host "views: $((Get-ChildItem views\*.html).Count)"
Write-Host "reports: $((Get-ChildItem reports\*.html).Count)"
Write-Host "utilities: $((Get-ChildItem utilities\*.html).Count)"
```

Expected output:
```
modals: 7
handovers: 12
forms: 17
views: 15
reports: 6
utilities: 11
```

---

## ✅ Step 6: Test Application

```powershell
# Start the Flask application
python app.py

# Or use your preferred method
python run_local.py
```

Test these critical pages:
1. `/vehicles/` - Vehicle index
2. `/vehicles/view/<id>` - Vehicle view
3. `/vehicles/handover/create/<id>` - Handover creation
4. `/vehicles/dashboard` - Dashboard
5. `/vehicles/workshop/create/<id>` - Workshop entry

---

## 📊 Summary of Changes

| Category | Files Count | Subdirectory |
|----------|-------------|--------------|
| Deletion modals | 7 | `modals/` |
| Handover templates | 12 | `handovers/` |
| Create/Edit forms | 17 | `forms/` |
| View/Display pages | 15 | `views/` |
| Reports/Dashboard | 6 | `reports/` |
| Utilities/Tools | 11 | `utilities/` |
| **TOTAL** | **68** | |

---

## 🚀 Quick Execution Script

Save this as `reorganize_now.ps1`:

```powershell
# Navigate to templates directory
cd "d:\nuzm\modules\vehicles\presentation\templates\vehicles"

# Create directories
$dirs = @('modals', 'handovers', 'forms', 'views', 'reports', 'utilities')
foreach ($dir in $dirs) {
    New-Item -ItemType Directory -Name $dir -Force
}

# Move modals
Move-Item confirm_delete*.html modals\ -Force

# Move handovers
Move-Item handover*.html handovers\ -Force
Move-Item edit_handover.html handovers\ -Force
Move-Item update_handover_link.html handovers\ -Force

# Move forms
Move-Item create*.html forms\ -Force
Move-Item edit*.html forms\ -Force
Move-Item *_create.html forms\ -Force
Move-Item *_edit.html forms\ -Force

# Move views
Move-Item view.html views\ -Force
Move-Item index.html views\ -Force
Move-Item *view*.html views\ -Force
Move-Item accident_details.html views\ -Force
Move-Item workshop_details.html views\ -Force if present
Move-Item workshop_image_view.html views\ -Force

# Move reports
Move-Item dashboard*.html reports\ -Force
Move-Item reports.html reports\ -Force
Move-Item detailed_list.html reports\ -Force
Move-Item print_workshop.html reports\ -Force
Move-Item share_workshop.html reports\ -Force

# Move utilities
Move-Item delete_accident.html utilities\ -Force
Move-Item drive_*.html utilities\ -Force
Move-Item *_documents.html utilities\ -Force
Move-Item import_vehicles.html utilities\ -Force
Move-Item inspections.html utilities\ -Force
Move-Item license_image.html utilities\ -Force
Move-Item safety_checks.html utilities\ -Force

Write-Host "✅ Files reorganized successfully!" -ForegroundColor Green
Write-Host "⚠️ Now update the backend routes in Python files" -ForegroundColor Yellow
```

Then run:
```powershell
.\reorganize_now.ps1
```

---

## 📝 Notes

- Keep `partials/` and `backup/` directories as-is
- After moving files, update ALL render_template() calls in backend
- Test thoroughly before deploying to production
- Consider running tests if available
- Back up database before major structural changes

