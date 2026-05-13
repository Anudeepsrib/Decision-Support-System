$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location (Join-Path $Root "frontend")

npm ci

Write-Host "Frontend setup complete."
Write-Host "Start it with: npm start"
