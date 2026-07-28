@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

set "PYEXE=%~dp0python\python.exe"
set "LOGFILE=%~dp0run.log"
if not exist "%PYEXE%" set "PYEXE=python"

if not exist "%PYEXE%" (
    echo Python not found. Please keep the bundled python folder next to run.bat, or install Python and add it to PATH.
    echo Python not found. Please keep the bundled python folder next to run.bat, or install Python and add it to PATH.>>"%LOGFILE%"
    pause
    exit /b 1
)

set "PORT=3011"
set "APP_URL=http://127.0.0.1:%PORT%/?v=20260727a"
echo Starting Infinite Canvas on port %PORT%...
echo Open: %APP_URL%
echo Press Ctrl+C to stop.
echo.

echo Starting Infinite Canvas on port %PORT%...>>"%LOGFILE%"
echo Open: %APP_URL%>>"%LOGFILE%"
start "" /b cmd /c "timeout /t 3 /nobreak >nul && start %APP_URL%"
"%PYEXE%" -m uvicorn launcher:app --host 0.0.0.0 --port %PORT% >>"%LOGFILE%" 2>&1

echo.
echo Server stopped.
echo Server stopped.>>"%LOGFILE%"
pause
endlocal


