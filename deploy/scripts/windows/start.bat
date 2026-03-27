@echo off
setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%..\..\.."
for %%I in ("%PROJECT_ROOT%") do set "PROJECT_ROOT=%%~fI"

if "%BACKEND_PORT%"=="" set "BACKEND_PORT=8001"
if "%FRONTEND_PORT%"=="" set "FRONTEND_PORT=3008"
set "BACKEND_LOG=%PROJECT_ROOT%\backend-dev.log"
set "FRONTEND_LOG=%PROJECT_ROOT%\frontend-dev.log"
set "BACKEND_ERR_LOG=%PROJECT_ROOT%\backend-dev.err.log"
set "FRONTEND_ERR_LOG=%PROJECT_ROOT%\frontend-dev.err.log"

echo [windows] Starting AI Test Platform...
echo [windows] Backend port: %BACKEND_PORT%
echo [windows] Frontend port: %FRONTEND_PORT%

call :kill_by_port backend %BACKEND_PORT%

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

del /f /q "%BACKEND_LOG%" 2>nul
del /f /q "%BACKEND_ERR_LOG%" 2>nul
start "" /B cmd /c ".venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port %BACKEND_PORT% --reload 1> %BACKEND_LOG% 2> %BACKEND_ERR_LOG%"
set "BACKEND_PID="
for /l %%i in (1,1,15) do (
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr :%BACKEND_PORT% ^| findstr LISTENING') do (
        set "BACKEND_PID=%%a"
        goto :backend_started
    )
    ping -n 2 127.0.0.1 >nul
)

:backend_started
if not defined BACKEND_PID (
    echo [windows] ERROR: failed to start backend process
    exit /b 1
)
echo [windows] Backend started pid=!BACKEND_PID!

echo [windows] Starting frontend...
cd /d "%PROJECT_ROOT%\frontend"

call :kill_by_port frontend %FRONTEND_PORT%

if not exist "node_modules\vite\bin\vite.js" (
    echo [windows] Installing frontend dependencies...
    call npm install
)

if exist "%FRONTEND_PID_FILE%" del /f /q "%FRONTEND_PID_FILE%" 2>nul
start "" /B cmd /c "node .\node_modules\vite\bin\vite.js --host 127.0.0.1 --port %FRONTEND_PORT% --strictPort"
set "FRONTEND_PID="
for /l %%i in (1,1,15) do (
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr :%FRONTEND_PORT% ^| findstr LISTENING') do (
        set "FRONTEND_PID=%%a"
        goto :frontend_started
    )
    ping -n 2 127.0.0.1 >nul
)

:frontend_started
if not defined FRONTEND_PID (
    echo [windows] ERROR: failed to start frontend process
    exit /b 1
)
echo [windows] Frontend started pid=!FRONTEND_PID!

cd /d "%PROJECT_ROOT%"

echo.
echo [windows] ==========================================
echo [windows] Application started successfully!
echo [windows] Backend:  http://localhost:%BACKEND_PORT%
echo [windows] Frontend: http://localhost:%FRONTEND_PORT%
echo [windows] ==========================================

endlocal
exit /b 0

:kill_by_port
setlocal enabledelayedexpansion
set "SERVICE_NAME=%~1"
set "SERVICE_PORT=%~2"
set "HAS_PID="

for /f "tokens=5" %%a in ('netstat -ano ^| findstr :!SERVICE_PORT! ^| findstr LISTENING') do (
    set "HAS_PID=1"
    echo [windows] Existing !SERVICE_NAME! service found on port !SERVICE_PORT! pid=%%a, restarting...
    taskkill /F /PID %%a >nul 2>&1
)

if not defined HAS_PID (
    echo [windows] No existing !SERVICE_NAME! service on port !SERVICE_PORT!, starting directly
    endlocal
    exit /b 0
)

ping -n 2 127.0.0.1 >nul
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :!SERVICE_PORT! ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
)
ping -n 2 127.0.0.1 >nul

for /f "tokens=5" %%a in ('netstat -ano ^| findstr :!SERVICE_PORT! ^| findstr LISTENING') do (
    echo [windows] ERROR: failed to stop !SERVICE_NAME! on port !SERVICE_PORT! pid=%%a
    endlocal
    exit /b 1
)

endlocal
exit /b 0
