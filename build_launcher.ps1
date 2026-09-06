$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$pyinstaller = 'C:\Users\27159\AppData\Local\Programs\Python\Python312\Scripts\pyinstaller.exe'
$source = Join-Path $root 'xiaoqi_launcher.py'
$dist = Join-Path $root '_launcher_dist'
$build = Join-Path $root '_launcher_build'
$spec = Join-Path $root 'xiaoqi-ai-canvas.spec'
$target = Join-Path $root 'xiaoqi-ai-canvas.exe'

if (-not (Test-Path -LiteralPath $pyinstaller)) {
  $command = Get-Command pyinstaller -ErrorAction SilentlyContinue
  if ($command) { $pyinstaller = $command.Source }
}
if (-not (Test-Path -LiteralPath $pyinstaller)) {
  throw 'PyInstaller was not found.'
}
if (-not (Test-Path -LiteralPath $source)) {
  throw "Launcher source was not found: $source"
}

foreach ($path in @($dist, $build, $spec)) {
  if (Test-Path -LiteralPath $path) {
    Remove-Item -LiteralPath $path -Recurse -Force
  }
}

$pyinstallerArgs = @(
  '--noconfirm', '--clean', '--onefile', '--windowed',
  '--name', 'xiaoqi-ai-canvas',
  '--distpath', $dist,
  '--workpath', $build,
  '--specpath', $root,
  $source
)
& $pyinstaller @pyinstallerArgs
if ($LASTEXITCODE -ne 0) {
  throw "PyInstaller failed with exit code $LASTEXITCODE."
}

Copy-Item -LiteralPath (Join-Path $dist 'xiaoqi-ai-canvas.exe') -Destination $target -Force
Remove-Item -LiteralPath $dist -Recurse -Force
Remove-Item -LiteralPath $build -Recurse -Force
Remove-Item -LiteralPath $spec -Force

Get-Item -LiteralPath $target | Select-Object FullName, Length, LastWriteTime
