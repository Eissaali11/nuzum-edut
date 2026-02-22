# Install GTK3 Runtime for WeasyPrint on Windows
#
# This script downloads and installs GTK3 runtime which provides
# the required libgobject-2.0-0 library for WeasyPrint PDF generation  
#
# Run with: powershell -ExecutionPolicy Bypass -File install_gtk3_windows.ps1

Write-Host "="*70
Write-Host "GTK3 Runtime Installation for WeasyPrint"
Write-Host "="*70

# Check if running as Administrator
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
$isAdmin = $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host ""
    Write-Warning "This script should be run as Administrator for system-wide installation!"
    Write-Host "Right-click PowerShell and select 'Run as Administrator', then run this script again."
    Write-Host ""
    Read-Host "Press Enter to continue anyway (user-level install)..."
}

Write-Host ""
Write-Host "GTK3 Installation Options:"
Write-Host "="*70

Write-Host ""
Write-Host "OPTION 1: Install via MSYS2 (Recommended)"
Write-Host "----------------------------------------"
Write-Host "1. Download MSYS2 from: https://www.msys2.org/"
Write-Host "2. Install MSYS2 to C:\msys64"
Write-Host "3. Open MSYS2 terminal and run:"
Write-Host "   pacman -S mingw-w64-x86_64-gtk3"
Write-Host "4. Add to system PATH:"  
Write-Host "   C:\msys64\mingw64\bin"
Write-Host ""

Write-Host "OPTION 2: Install via Chocolatey"
Write-Host "--------------------------------"
Write-Host "If you have Chocolatey installed:"
Write-Host "   choco install gtk-runtime"
Write-Host ""
Write-Host "To install Chocolatey first:"
Write-Host "   Set-ExecutionPolicy Bypass -Scope Process -Force"
Write-Host "   [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072"
Write-Host "   iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))"
Write-Host ""

Write-Host "OPTION 3: Manual Download"
Write-Host "------------------------"
Write-Host "1. Download GTK3 bundle from:"
Write-Host "   https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases"
Write-Host "2. Run the installer"
Write-Host "3. Restart your terminal"
Write-Host ""

Write-Host "="*70
Write-Host ""

$choice = Read-Host "Would you like to attempt automatic installation via Chocolatey? (Y/N)"

if ($choice -eq "Y" -or $choice -eq "y") {
    Write-Host ""
    Write-Host "Checking for Chocolatey..."
    
    $chocoCmd = Get-Command choco -ErrorAction SilentlyContinue
    
    if ($chocoCmd) {
        Write-Host "Chocolatey found! Installing GTK runtime..."
        choco install gtk-runtime -y
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host ""
            Write-Host "="*70
            Write-Host "SUCCESS: GTK3 Runtime installed!"
            Write-Host "="*70
            Write-Host ""
            Write-Host "Next steps:"
            Write-Host "1. Close and reopen your terminal"
            Write-Host "2. Uncomment workshop_reports in app.py"
            Write-Host "3. Restart your Flask server"
            Write-Host ""
        } else {
            Write-Host ""
            Write-Warning "Installation failed. Please try manual installation (Option 1 or 3)."
        }
    } else {
        Write-Host ""
        Write-Warning "Chocolatey not found!"
        Write-Host "Would you like to install Chocolatey now? (Y/N)"
        $installChoco = Read-Host
        
        if ($installChoco -eq "Y" -or $installChoco -eq "y") {
            Write-Host "Installing Chocolatey..."
            Set-ExecutionPolicy Bypass -Scope Process -Force
            [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
            iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
            
            Write-Host ""
            Write-Host "Chocolatey installed! Please close this terminal and run the script again."
        } else {
            Write-Host "Please use Option 1 or 3 for manual installation."
        }
    }
} else {
    Write-Host ""
    Write-Host "Please follow one of the manual installation options above."
}

Write-Host ""
Write-Host "="*70
Write-Host "For more help, see: https://weasyprint.readthedocs.io/en/stable/first_steps.html#windows"
Write-Host "="*70
Write-Host ""

Read-Host "Press Enter to close..."
