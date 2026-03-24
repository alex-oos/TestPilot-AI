@echo off
setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%..\..\.."

set BACKEND_PORT=8001
set FRONTEND_PORT=3008

echo [windows] Stopping AI Test Platform...

if exist "%PROJECT_ROOT%\.run\backend.pid" (
    set /p BACKEND_PID=<"%PROJECT_ROOT%\.run\backend.pid"
    if defined BACKEND_PID (
        echo [windows] Stopping backend (pid=!BACKEND_PID!)...
        taskkill /F /PID !BACKEND_PID! 2>nul
    )
    del /f /q "%PROJECT_ROOT%\.run\backend.pid" 2>nul
)

if exist "%PROJECT_ROOT%\.run\frontend.pid" (
    set /p FRONTEND_PID=<"%PROJECT_ROOT%\.run\frontend.pid"
    if defined FRONTEND_PID (
        echo [windows] Stopping frontend (pid=!FRONTEND_PID!)...
        taskkill /F /PID !FRONTEND_PID! 2>nul
    )
    del /f /q "%PROJECT_ROOT%\.run\frontend.pid" 2>nul
)

for /f "tokens=5" %%a in ('netstat -ano ^| findstr :%BACKEND_PORT% ^| findstr LISTENING') do (
    echo [windows] Stopping backend on port %BACKEND_PORT% (pid=%%a)...
    taskkill /F /PID %%a 2>nul
)

for /f "tokens=5" %%a in ('netstat -ano ^| findstr :%FRONTEND_PORT% ^| findstr LISTENING') do (
    echo [windows] Stopping frontend on port %FRONTEND_PORT% (pid=%%a)...
    taskkill /F /PID %%a 2>nul
)

echo [windows] All services stopped.

endlocal
