@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    powershell -ExecutionPolicy Bypass -File scripts\setup_backend.ps1
)

if not exist "frontend\node_modules" (
    powershell -ExecutionPolicy Bypass -File scripts\setup_frontend.ps1
)

start "KSERC Backend" .venv\Scripts\python.exe -m uvicorn backend.app:app --reload --port 8000
start "KSERC Frontend" cmd /k "cd frontend && npm start"

echo Backend:  http://127.0.0.1:8000
echo Frontend: http://127.0.0.1:5173
echo API docs: http://127.0.0.1:8000/docs
echo.
echo Close the two opened terminal windows to stop the MVP.

endlocal
