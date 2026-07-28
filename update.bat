@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

set "SRC=%~dp0"
set "TARGET="
set "LOG=%~dp0update.log"

if not exist "%SRC%run.bat" (
  echo This folder does not look like an Infinite Canvas update package.
  echo This folder does not look like an Infinite Canvas update package.>>"%LOG%"
  pause
  exit /b 1
)

echo ==================================================
echo Infinite Canvas Update Package
echo ==================================================
echo.
echo This package updates an existing installation in place.
echo Preserved folders: data, assets, output, API\.env

echo.

if not "%~1"=="" (
  set "TARGET=%~1"
) else if exist "%SRC%target-path.txt" (
  set /p TARGET=<"%SRC%target-path.txt"
) else (
  set /p TARGET=Enter the full path of the old installation folder: 
)

if "%TARGET%"=="" (
  echo No target folder provided.
  pause
  exit /b 1
)

for %%I in ("%TARGET%") do set "TARGET=%%~fI"
for %%I in ("%SRC%") do set "SRC=%%~fI"

if /I "%TARGET%"=="%SRC%" (
  echo The target folder cannot be the same as the update package folder.
  pause
  exit /b 1
)

if not exist "%TARGET%run.bat" (
  echo The selected folder does not look like an installed project folder.
  echo You chose: %TARGET%
  pause
  exit /b 1
)

if not exist "%TARGET%" (
  echo Target folder does not exist.
  pause
  exit /b 1
)

echo Updating: %TARGET%
echo Source:   %SRC%
echo.

auto-update:
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$src = [System.IO.Path]::GetFullPath('%SRC%'); ^
   $dst = [System.IO.Path]::GetFullPath('%TARGET%'); ^
   if ($src.TrimEnd('\\') -eq $dst.TrimEnd('\\')) { throw 'Source and target are the same folder.' } ^
   $preserveDirs = @('data','assets','output','.git','__pycache__'); ^
   $preserveFiles = @('run.log','update.log','target-path.txt'); ^
   $items = Get-ChildItem -LiteralPath $src -Force; ^
   foreach ($item in $items) { ^
     $name = $item.Name; ^
     if ($item.PSIsContainer) { ^
       if ($preserveDirs -contains $name) { continue } ^
       if ($name -eq 'API') { ^
         New-Item -ItemType Directory -Force -Path (Join-Path $dst 'API') | Out-Null; ^
         $envSrc = Join-Path $src 'API\.env'; ^
         $envDst = Join-Path $dst 'API\.env'; ^
         if (Test-Path -LiteralPath $envSrc) { Copy-Item -LiteralPath $envSrc -Destination $envDst -Force } ^
         continue ^
       } ^
       $destPath = Join-Path $dst $name; ^
       if (Test-Path -LiteralPath $destPath) { Remove-Item -LiteralPath $destPath -Recurse -Force } ^
       Copy-Item -LiteralPath $item.FullName -Destination $destPath -Recurse -Force; ^
     } else { ^
       if ($preserveFiles -contains $name) { continue } ^
       Copy-Item -LiteralPath $item.FullName -Destination (Join-Path $dst $name) -Force; ^
     } ^
   } ^
   Write-Host 'Update finished.'"

if errorlevel 1 (
  echo.
  echo Update failed. See update.log if available.
  echo Update failed. See update.log if available.>>"%LOG%"
  pause
  exit /b 1
)

echo.
echo Update completed.
echo Update completed.>>"%LOG%"

echo Starting the updated app...
start "" /d "%TARGET%" cmd /c run.bat
endlocal
exit /b 0
