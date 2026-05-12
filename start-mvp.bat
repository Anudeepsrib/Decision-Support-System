@echo off
REM KSERC DSS MVP Startup Script for Windows

echo 🚀 Starting KSERC Decision Support System MVP...

REM Check if Docker is available
docker --version >nul 2>&1
if %errorlevel% equ 0 (
    docker-compose --version >nul 2>&1
    if %errorlevel% equ 0 (
        echo 📦 Using Docker Compose...
        docker-compose up --build
        goto :end
    )
)

echo 🐍 Docker not found, starting locally...

REM Start backend
echo 🔧 Starting backend...
cd backend
start /B python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000

REM Wait for backend to start
timeout /t 3 /nobreak >nul

REM Start frontend
echo 🎨 Starting frontend...
cd ..\frontend
start /B npm run dev

echo ✅ MVP started!
echo 📊 Backend: http://localhost:8000
echo 🖥️  Frontend: http://localhost:5173
echo 📚 API Docs: http://localhost:8000/docs
echo.
echo Press any key to stop...
pause >nul

REM Cleanup (optional - you may need to manually stop the processes)
taskkill /f /im python.exe >nul 2>&1
taskkill /f /im node.exe >nul 2>&1

:end
echo 👋 Stopped.
