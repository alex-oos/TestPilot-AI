@echo off
setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%..\..\.."

set BACKEND_PORT=8001
set FRONTEND_PORT=3008

echo [windows] Starting AI Test Platform...
echo [windows] Backend port: %BACKEND_PORT%
echo [windows] Frontend port: %FRONTEND_PORT%

if not exist "%PROJECT_ROOT%\.run" mkdir "%PROJECT_ROOT%\.run"

echo [windows] Starting backend...
cd /d "%PROJECT_ROOT%\backend"

if not exist ".venv" (
    echo [windows] Creating Python virtual environment...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    pip install -r requirements.txt
) else (
    call .venv\Scripts\activate.bat
)

start /B cmd /c ".venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port %BACKEND_PORT% > ..\backend-dev.log 2>&1"
echo %ERRORLEVEL% > "%PROJECT_ROOT%\.run\backend.pid"
echo [windows] Backend started

echo [windows] Starting frontend...
cd /d "%PROJECT_ROOT%\frontend"

if not exist "node_modules" (
    echo [windows] Installing frontend dependencies...
    call npm install
)

start /B cmd /c "npm run dev > ..\frontend-dev.log 2>&1"
echo %ERRORLEVEL% > "%PROJECT_ROOT%\.run\frontend.pid"
echo [windows] Frontend started

cd /d "%PROJECT_ROOT%"

echo.
echo [windows] ==========================================
echo [windows] Application started successfully!
echo [windows] Backend:  http://localhost:%BACKEND_PORT%
echo [windows] Frontend: http://localhost:%FRONTEND_PORT%
echo [windows] ==========================================

endlocal
