@echo off
setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%..\..\.."
for %%I in ("%PROJECT_ROOT%") do set "PROJECT_ROOT=%%~fI"

if "%BACKEND_PORT%"=="" set "BACKEND_PORT=8001"
if "%FRONTEND_PORT%"=="" set "FRONTEND_PORT=3008"

echo [windows] Stopping AI Test Platform...

call :stop_by_port backend %BACKEND_PORT%
call :stop_by_port frontend %FRONTEND_PORT%

echo [windows] All services stopped.

endlocal
exit /b 0

:stop_by_port
setlocal enabledelayedexpansion
set "SERVICE_NAME=%~1"
set "SERVICE_PORT=%~2"
set "HAS_PID="

for /f "tokens=5" %%a in ('netstat -ano ^| findstr :!SERVICE_PORT! ^| findstr LISTENING') do (
    set "HAS_PID=1"
    echo [windows] Stopping !SERVICE_NAME! on port !SERVICE_PORT! pid=%%a ...
    taskkill /F /PID %%a >nul 2>&1
)

if not defined HAS_PID (
    echo [windows] No !SERVICE_NAME! service found on port !SERVICE_PORT!
    endlocal
    exit /b 0
)

ping -n 2 127.0.0.1 >nul
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :!SERVICE_PORT! ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
)

endlocal
exit /b 0
