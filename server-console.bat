@echo off
setlocal
cd /d "%~dp0"
title XiaoQi AI Canvas Server
if not defined APP_PORT set "APP_PORT=3011"
echo ========================================
echo XiaoQi AI Canvas Server
echo ========================================
echo.
echo Folder: %CD%
echo URL: http://127.0.0.1:%APP_PORT%/
echo.

if not exist "%~dp0python\python.exe" (
  echo [ERROR] Embedded Python was not found.
  echo Extract the complete package before running it.
  echo Do not run run.bat inside the ZIP preview window.
  echo.
  pause
  exit /b 1
)

echo Starting service. Keep this window open while using the app.
echo.
"%~dp0python\python.exe" main.py
set "EXIT_CODE=%ERRORLEVEL%"
echo.
echo [INFO] The service stopped with code %EXIT_CODE%.
echo Read the error above, fix it, and run run.bat again.
pause
exit /b %EXIT_CODE%
