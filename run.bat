@echo off
cd /d "%~dp0"
if not exist "%~dp0start-server.bat" (
  echo [ERROR] start-server.bat was not found.
  echo Please extract the zip package completely first.
  pause
  exit /b 1
)
call "%~dp0start-server.bat"
pause
