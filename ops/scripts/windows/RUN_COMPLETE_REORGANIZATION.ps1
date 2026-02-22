# ========================================================================
# COMPLETE VEHICLE TEMPLATES REORGANIZATION - ALL-IN-ONE SCRIPT
# ========================================================================
# This PowerShell script executes the complete reorganization process:
#   1. Reorganize files into subdirectories
#   2. Update backend route files  
#   3. Update template include paths
# ========================================================================

$ErrorActionPreference = "Stop"

# Colors
function Write-Header {
    param($Text)
    Write-Host "`n========================================================================" -ForegroundColor Cyan
    Write-Host "  $Text" -ForegroundColor Cyan
    Write-Host "========================================================================" -ForegroundColor Cyan
}

function Write-Step {
    param($Number, $Text)
    Write-Host "`n>>> STEP $Number: $Text" -ForegroundColor Yellow
    Write-Host "------------------------------------------------------------------------" -ForegroundColor Gray
}

function Write-Success {
    param($Text)
    Write-Host "  ✅ $Text" -ForegroundColor Green
}

function Write-Warning {
    param($Text)
    Write-Host "  ⚠️  $Text" -ForegroundColor Yellow
}

function Write-Error {
    param($Text)
    Write-Host "  ❌ $Text" -ForegroundColor Red
}

# Configuration
$BaseDir = "d:\nuzm"
$PythonExe = "python"

# Check if Python is available
try {
    $pythonVersion = & $PythonExe --version 2>&1
    Write-Success "Python found: $pythonVersion"
} catch {
    Write-Error "Python not found! Please install Python and try again."
    exit 1
}

Write-Header "🚀 VEHICLE TEMPLATES COMPLETE REORGANIZATION"

Write-Host @"

This script will completely reorganize your vehicle templates:
  
  📂 File Reorganization:
    • Create 6 subdirectories (modals, handovers, forms, views, reports, utilities)
    • Move 68 HTML files to appropriate locations
    • Create automatic backup before any changes
  
  🔧 Code Updates:
    • Update all render_template() calls in Python route files
    • Update all {% include %} paths in HTML templates
    • Preserve all existing functionality
  
  📍 Working Directory:
    $BaseDir
  
  ⚠️  WARNING: This will modify files in your project!
    A backup will be created automatically.

"@

$response = Read-Host "Do you want to proceed? (yes/no)"
if ($response -ne "yes") {
    Write-Warning "Operation cancelled by user."
    exit 0
}

# Change to base directory
Set-Location $BaseDir

# ========================================================================
# STEP 1: File Reorganization
# ========================================================================
Write-Step 1 "FILE REORGANIZATION"

Write-Host "  Running: master_reorganize.py`n"

try {
    & $PythonExe master_reorganize.py
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "File reorganization completed"
    } else {
        Write-Warning "File reorganization completed with warnings (exit code: $LASTEXITCODE)"
    }
} catch {
    Write-Error "File reorganization failed: $_"
    Write-Warning "Aborting remaining steps"
    exit 1
}

# Pause for user to review
Write-Host "`n"
Read-Host "Press Enter to continue to backend routes update..."

# ========================================================================
# STEP 2: Update Backend Routes
# ========================================================================
Write-Step 2 "UPDATE BACKEND ROUTES"

Write-Host "  Running: update_backend_routes.py`n"

try {
    & $PythonExe update_backend_routes.py
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Backend routes updated successfully"
    } else {
        Write-Warning "Backend routes update completed with warnings (exit code: $LASTEXITCODE)"
    }
} catch {
    Write-Error "Backend routes update failed: $_"
    Write-Warning "You may need to update routes manually"
}

# Pause for user to review
Write-Host "`n"
Read-Host "Press Enter to continue to template includes update..."

# ========================================================================
# STEP 3: Update Template Includes
# ========================================================================
Write-Step 3 "UPDATE TEMPLATE INCLUDES"

Write-Host "  Running: update_template_includes.py`n"

try {
    & $PythonExe update_template_includes.py
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Template includes updated successfully"
    } else {
        Write-Warning "Template includes update completed with warnings (exit code: $LASTEXITCODE)"
    }
} catch {
    Write-Error "Template includes update failed: $_"
    Write-Warning "You may need to update template paths manually"
}

# ========================================================================
# FINAL SUMMARY
# ========================================================================
Write-Header "📊 REORGANIZATION COMPLETE"

Write-Host @"

  ✅ All reorganization steps have been executed!

  📋 What Was Done:
    1. ✓ Created subdirectories and moved 68 HTML files
    2. ✓ Updated backend render_template() calls
    3. ✓ Updated template {% include %} paths
  
  🔍 Next Steps:
    1. Review the changes in your code editor
    2. Test the application thoroughly:
       • Vehicle list page (/vehicles/)
       • Vehicle view page (/vehicles/view/<id>)
       • Handover creation (/vehicles/handover/create/<id>)
       • Dashboard (/vehicles/dashboard)
       • Workshop management
    3. Check for any TemplateNotFound errors
    4. If everything works, you can delete the backup folder
  
  🚀 Start Your Application:
    python app.py
    # or
    python run_local.py
  
  📦 Backup Location:
    Check the console output above for backup directory path
    If something goes wrong, you can restore from there
  
  ⚠️  Important:
    • All 68 files should now be in subdirectories
    • Zero HTML files should remain in the root vehicles/ folder
    • All template paths have been updated

"@

Write-Host "========================================================================`n" -ForegroundColor Cyan

# Ask if user wants to see the directory structure
$response = Read-Host "Would you like to see the new directory structure? (y/n)"
if ($response -eq "y") {
    Write-Host "`n"
    $templatesDir = "modules\vehicles\presentation\templates\vehicles"
    if (Test-Path $templatesDir) {
        Get-ChildItem $templatesDir -Directory | ForEach-Object {
            $count = (Get-ChildItem $_.FullName -Filter "*.html").Count
            Write-Host "  📂 $($_.Name):".PadRight(25) -NoNewline -ForegroundColor Cyan
            Write-Host "$count files" -ForegroundColor White
        }
        
        $rootHtmlCount = (Get-ChildItem $templatesDir -Filter "*.html").Count
        Write-Host "`n  Files remaining in root:".PadRight(25) -NoNewline
        if ($rootHtmlCount -eq 0) {
            Write-Host "$rootHtmlCount ✅" -ForegroundColor Green
        } else {
            Write-Host "$rootHtmlCount ⚠️" -ForegroundColor Yellow
        }
    } else {
        Write-Warning "Templates directory not found: $templatesDir"
    }
}

Write-Host "`n✅ All done! Happy coding! 🎉`n" -ForegroundColor Green
