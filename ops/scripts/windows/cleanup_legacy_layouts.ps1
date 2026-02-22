# لم Module Templates Cleanup Script
# Move old/legacy layout templates to archive folder

$archiveDir = "d:\nuzm\templates\old_layouts"

# Create archive directory if it doesn't exist
if (-not (Test-Path $archiveDir)) {
    New-Item -ItemType Directory -Path $archiveDir -Force | Out-Null
    Write-Host "✓ Created archive directory: $archiveDir" -ForegroundColor Green
}

# List of legacy layout files to archive
$legacyLayouts = @(
    "d:\nuzm\templates\layout_simple.html",
    "d:\nuzm\templates\admin_dashboard\layout.html",
    "d:\nuzm\templates\landing\layout.html",
    "d:\nuzm\templates\landing_admin\layout.html"
)

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "LEGACY LAYOUT CLEANUP" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

$movedCount = 0
$skippedCount = 0

foreach ($file in $legacyLayouts) {
    if (Test-Path $file) {
        $fileName = Split-Path $file -Leaf
        $destinationFolder = Join-Path $archiveDir (Split-Path (Split-Path $file -Parent) -Leaf)
        
        # Create subfolder if needed
        if (-not (Test-Path $destinationFolder)) {
            New-Item -ItemType Directory -Path $destinationFolder -Force | Out-Null
        }
        
        $destination = Join-Path $destinationFolder $fileName
        
        Move-Item -Path $file -Destination $destination -Force
        Write-Host "  ✓ Moved: $fileName → old_layouts/$(Split-Path (Split-Path $file -Parent) -Leaf)/" -ForegroundColor Green
        $movedCount++
    } else {
        Write-Host "  ○ Not found: $file" -ForegroundColor Yellow
        $skippedCount++
    }
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "✓ Cleanup complete!" -ForegroundColor Green
Write-Host "  Files moved: $movedCount" -ForegroundColor Green
Write-Host "  Files skipped: $skippedCount" -ForegroundColor Yellow
Write-Host "========================================`n" -ForegroundColor Cyan

# Note: mobile/layout.html is kept as it's actively used by the mobile interface
Write-Host "Note: templates/mobile/layout.html retained (active mobile UI)" -ForegroundColor Cyan
Write-Host "Note: templates/layout.html is the primary modern layout" -ForegroundColor Cyan
