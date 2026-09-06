@echo off
setlocal
cd /d "%~dp0"

set "DEFAULT_PORT=3011"
set "PORT_SCAN_END=3099"
set "SELECTED_PORT="
set "PYEXE=%~dp0python\python.exe"
set "LOG_FILE=%~dp0start-error.log"
set "LOCAL_VERSION="
if exist "%~dp0VERSION" set /p LOCAL_VERSION=<"%~dp0VERSION"

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
echo Checking whether this project is already running on the default port...
set "APP_PORT=%DEFAULT_PORT%"
set "APP_URL=http://127.0.0.1:%APP_PORT%/"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0wait-for-server.ps1" -HealthUrl "%APP_URL%api/app-info" -BrowserUrl "%APP_URL%" -ExpectedRepoUrl "https://github.com/cqiqi271/xiaoqi-ai-canvas" -ExpectedVersion "%LOCAL_VERSION%" -CheckOnly
if not errorlevel 1 (
  echo.
  start "" "%APP_URL%"
  echo This project is already running. The browser has been opened.
  echo.
  pause
  exit /b 0
)

echo Selecting an available local port...
for /f "usebackq delims=" %%P in (`powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0find-free-port.ps1" -StartPort %DEFAULT_PORT% -EndPort %PORT_SCAN_END%`) do if not defined SELECTED_PORT set "SELECTED_PORT=%%P"
if not defined SELECTED_PORT (
  echo [ERROR] No available local port was found between %DEFAULT_PORT% and %PORT_SCAN_END%.
  echo Close an unused local project and run run.bat again.
  echo.
  pause
  exit /b 2
)
set "APP_PORT=%SELECTED_PORT%"
set "APP_URL=http://127.0.0.1:%APP_PORT%/"
echo Selected port: %APP_PORT%

echo Starting local server...
echo Browser will open only after the service passes its health check.
echo.
start "XiaoQi AI Canvas Server" /D "%~dp0" cmd /k call "%~dp0server-console.bat"

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0wait-for-server.ps1" -HealthUrl "%APP_URL%api/app-info" -BrowserUrl "%APP_URL%" -ExpectedRepoUrl "https://github.com/cqiqi271/xiaoqi-ai-canvas" -ExpectedVersion "%LOCAL_VERSION%" -TimeoutSeconds 60
if errorlevel 2 (
  echo.
  echo [ERROR] Port %APP_PORT% is serving another project.
  echo The browser was not opened to avoid opening the wrong project.
  echo.
  pause
  exit /b 2
)
if errorlevel 1 (
  echo.
  echo [ERROR] The service did not start successfully.
  echo Check the separate server window for the exact error.
  echo.
  pause
  exit /b 1
)

echo.
echo The project is ready. Keep the server window open while using it.
echo.
pause
