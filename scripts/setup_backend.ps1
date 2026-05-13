$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example"
}

python -m venv .venv
$Python = Join-Path $Root ".venv\Scripts\python.exe"

& $Python -m pip install --upgrade pip
& $Python -m pip install -r requirements.txt
& $Python scripts\check_env.py
& $Python scripts\init_db.py

Write-Host "Backend setup complete."
Write-Host "Start it with: .\.venv\Scripts\python.exe -m uvicorn backend.app:app --reload --port 8000"
