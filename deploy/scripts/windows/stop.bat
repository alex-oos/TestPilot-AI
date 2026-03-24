@echo off
setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%..\..\.."
for %%I in ("%PROJECT_ROOT%") do set "PROJECT_ROOT=%%~fI"
set "RUN_DIR=%PROJECT_ROOT%\.run"
set "BACKEND_PID_FILE=%RUN_DIR%\backend.pid"
set "FRONTEND_PID_FILE=%RUN_DIR%\frontend.pid"

set BACKEND_PORT=8001
set FRONTEND_PORT=3008

echo [windows] Stopping AI Test Platform...

if exist "%BACKEND_PID_FILE%" (
    set /p BACKEND_PID=<"%BACKEND_PID_FILE%"
    if defined BACKEND_PID if not "!BACKEND_PID!"=="0" (
        echo [windows] Stopping backend pid=!BACKEND_PID! ...
        taskkill /F /PID !BACKEND_PID! 2>nul
    )
    del /f /q "%BACKEND_PID_FILE%" 2>nul
)

if exist "%FRONTEND_PID_FILE%" (
    set /p FRONTEND_PID=<"%FRONTEND_PID_FILE%"
    if defined FRONTEND_PID if not "!FRONTEND_PID!"=="0" (
        echo [windows] Stopping frontend pid=!FRONTEND_PID! ...
        taskkill /F /PID !FRONTEND_PID! 2>nul
    )
    del /f /q "%FRONTEND_PID_FILE%" 2>nul
)

for /f "tokens=5" %%a in ('netstat -ano ^| findstr :%BACKEND_PORT% ^| findstr LISTENING') do (
    echo [windows] Stopping backend on port %BACKEND_PORT% pid=%%a ...
    taskkill /F /PID %%a 2>nul
)

for /f "tokens=5" %%a in ('netstat -ano ^| findstr :%FRONTEND_PORT% ^| findstr LISTENING') do (
    echo [windows] Stopping frontend on port %FRONTEND_PORT% pid=%%a ...
    taskkill /F /PID %%a 2>nul
)

echo [windows] All services stopped.

endlocal
