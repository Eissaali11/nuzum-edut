# Move routes files to organized directories
# نقل ملفات الراوتس إلى المجلدات المنظمة

Set-Location d:\nuzm\routes

# Move documents files
"Moving documents files..." | Write-Host -ForegroundColor Green
@('documents.py', 'documents_controller.py') | Where-Object {Test-Path $_} | ForEach-Object {
    Move-Item $_ documents/ -Force
    Write-Host "✅ OK: $_"
}

# Move requests files
"Moving requests files..." | Write-Host -ForegroundColor Green
@('employee_requests.py', 'employee_requests_controller.py', 'api_employee_requests.py', 'api_employee_requests_v2.py') | Where-Object {Test-Path $_} | ForEach-Object {
    Move-Item $_ requests/ -Force
    Write-Host "✅ OK: $_"
}

# Move accounting files
"Moving accounting files..." | Write-Host -ForegroundColor Green
@('accounting.py', 'accounting_analytics.py', 'accounting_extended.py', 'e_invoicing.py', 'fees_costs.py') | Where-Object {Test-Path $_} | ForEach-Object {
    Move-Item $_ accounting/ -Force
    Write-Host "✅ OK: $_"
}

# Move communications files
"Moving communications files..." | Write-Host -ForegroundColor Green
@('notifications.py', 'email_queue.py') | Where-Object {Test-Path $_} | ForEach-Object {
    Move-Item $_ communications/ -Force
    Write-Host "✅ OK: $_"
}

# Move integrations files
"Moving integrations files..." | Write-Host -ForegroundColor Green
@('voicehub.py', 'google_drive_settings.py', 'drive_browser.py', 'external_safety.py', 'external_safety_refactored.py', 'geofences.py') | Where-Object {Test-Path $_} | ForEach-Object {
    Move-Item $_ integrations/ -Force
    Write-Host "✅ OK: $_"
}

# Move admin files
"Moving admin files..." | Write-Host -ForegroundColor Green
@('admin_dashboard.py', 'payroll_management.py', 'payroll_admin.py') | Where-Object {Test-Path $_} | ForEach-Object {
    Move-Item $_ admin/ -Force
    Write-Host "✅ OK: $_"
}

# Move analytics files
"Moving analytics files..." | Write-Host -ForegroundColor Green
@('analytics.py', 'analytics_direct.py', 'analytics_real.py', 'analytics_simple.py', 'enhanced_reports.py', 'insights.py') | Where-Object {Test-Path $_} | ForEach-Object {
    Move-Item $_ analytics/ -Force
    Write-Host "✅ OK: $_"
}

Write-Host ""
Write-Host "Done!" -ForegroundColor Yellow
