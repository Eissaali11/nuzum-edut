# تشغيل نواة نُظم (يُنشئ venv ويثبت المتطلبات إن لزم)
$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $RepoRoot

if (-not (Test-Path ".\venv\Scripts\python.exe")) {
    Write-Host "جاري إنشاء البيئة الافتراضية (venv)..."
    python -m venv .\venv
}
& ".\venv\Scripts\Activate.ps1"

if (-not (Get-Command flask -ErrorAction SilentlyContinue) -and -not (python -c "import flask" 2>$null)) {
    Write-Host "جاري تثبيت المتطلبات من requirements.txt..."
    python -m pip install --upgrade pip -q
    pip install -r requirements.txt -q
}

$env:FLASK_APP = "wsgi:app"
$env:FLASK_ENV = "development"
Write-Host "تشغيل الخادم على http://0.0.0.0:5000"
python -m flask run --host=0.0.0.0 --port=5000
