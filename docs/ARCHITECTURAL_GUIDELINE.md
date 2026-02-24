# Architectural Guideline (Nuzum)

## Source of Truth Policy
- Vehicle handover routes must live only in:
  - [modules/vehicles/presentation/web/handover_routes.py](modules/vehicles/presentation/web/handover_routes.py)
- Do not add parallel handover route implementations under legacy paths.

## Blueprint Registration Policy
- Register `/vehicles` only once from:
  - `modules.vehicles.presentation.web.main_routes.get_vehicles_blueprint()`
- Any additional `/vehicles` registration is treated as architecture violation.

## Template Duplication Policy
- Keep one active handover template path.
- Any edits to handover UI must target the active template used by route rendering.
- Before merging, verify no duplicated `_content.html` variants are diverging for same feature.

## Design Lock (Handover Report)
- Must preserve:
  - `grid-template-columns: 52% 1fr`
  - diagram container height `220px`
  - `object-fit: contain` for dynamic images/signatures

## Verification Checklist (Required)
1. `python -m py_compile core/app_factory.py modules/vehicles/presentation/web/handover_routes.py`
2. Verify public PDF URL returns 200:
   - `/vehicles/handover/<id>/pdf/public`
3. Confirm no duplicate handover route files are introduced.
