$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$repo = 'https://github.com/cqiqi271/xiaoqi-ai-canvas.git'
$work = Join-Path $env:TEMP 'xiaoqi-ai-canvas-publish'

if (Test-Path -LiteralPath $work) {
  $resolved = (Resolve-Path -LiteralPath $work).Path
  $tempRoot = [System.IO.Path]::GetFullPath($env:TEMP).TrimEnd('\') + '\'
  if (-not $resolved.StartsWith($tempRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to remove unexpected path: $resolved"
  }
  Remove-Item -LiteralPath $work -Recurse -Force
}

git clone $repo $work

$copyDirs = @('static')
foreach ($dir in $copyDirs) {
  $dst = Join-Path $work $dir
  if (Test-Path -LiteralPath $dst) { Remove-Item -LiteralPath $dst -Recurse -Force }
  Copy-Item -LiteralPath (Join-Path $root $dir) -Destination $dst -Recurse -Force
}

$copyFiles = @('main.py','VERSION','project-config.json','README.md','DEPLOYMENT.md','requirements.txt','run.bat','start-server.bat','update.bat')
foreach ($file in $copyFiles) {
  $src = Join-Path $root $file
  if (Test-Path -LiteralPath $src) {
    Copy-Item -LiteralPath $src -Destination (Join-Path $work $file) -Force
  }
}

Push-Location $work
try {
  git add main.py VERSION project-config.json README.md DEPLOYMENT.md requirements.txt run.bat start-server.bat update.bat static
  if (-not (git diff --cached --quiet)) {
    $version = (Get-Content -LiteralPath (Join-Path $work 'VERSION') -Raw).Trim()
    git commit -m "Publish update $version"
    git push origin main
  } else {
    Write-Host 'No online update changes to publish.'
  }
}
finally {
  Pop-Location
}
