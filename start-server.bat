@echo off
setlocal
cd /d "%~dp0"

set "APP_URL=http://127.0.0.1:3011/"
set "PYEXE=%~dp0python\python.exe"
set "LOG_FILE=%~dp0start-error.log"

title XiaoQi AI Canvas Server
echo ========================================
echo XiaoQi AI Canvas Server
echo ========================================
echo.
echo Current folder:
echo %CD%
echo.

if not exist "%PYEXE%" (
  echo [ERROR] Embedded Python was not found.
  echo Path: %PYEXE%
  echo.
  echo Please extract the zip package completely first.
  echo Do NOT run run.bat from inside the zip preview window.
  echo.
  pause
  exit /b 1
)

echo Checking runtime...
"%PYEXE%" -c "import encodings, fastapi, uvicorn, pydantic, httpx, PIL" >nul 2>"%LOG_FILE%"
if errorlevel 1 (
  echo [ERROR] Runtime check failed.
  echo.
  echo Please send this file to the maintainer:
  echo %LOG_FILE%
  echo.
  type "%LOG_FILE%"
  echo.
  pause
  exit /b 1
)

echo Runtime OK.
echo Starting local server...
echo Browser URL: %APP_URL%
echo.
echo Keep this window open while using the app.
echo Close this window to stop the app.
echo.

start "" cmd /c "timeout /t 6 /nobreak >nul & start %APP_URL%"
"%PYEXE%" main.py

echo.
echo [INFO] Server process ended.
echo If this was unexpected, check the messages above or start-error.log.
echo.
pause
