param(
    [string]$HealthUrl = 'http://127.0.0.1:3011/api/app-info',
    [string]$BrowserUrl = 'http://127.0.0.1:3011/',
    [string]$ExpectedProjectName = '小七AI画布',
    [string]$ExpectedRepoUrl = 'https://github.com/cqiqi271/xiaoqi-ai-canvas',
    [string]$ExpectedVersion = '',
    [int]$TimeoutSeconds = 60,
    [switch]$CheckOnly
)

$ErrorActionPreference = 'Stop'

function Get-AppInfo {
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $HealthUrl -TimeoutSec 3
        if ([int]$response.StatusCode -ne 200) {
            return $null
        }
        return ($response.Content | ConvertFrom-Json)
    } catch {
        return $null
    }
}

function Test-ExpectedApp($info) {
    if ($null -eq $info) { return $false }
    $name = [string]$info.project_name
    $repo = [string]$info.repo_url
    $version = [string]$info.version
    if ($ExpectedRepoUrl) {
        if ($repo -ne $ExpectedRepoUrl) { return $false }
        return (-not $ExpectedVersion) -or ($version -eq $ExpectedVersion)
    }
    return ($name -eq $ExpectedProjectName) -and ((-not $ExpectedVersion) -or ($version -eq $ExpectedVersion))
}

$existing = Get-AppInfo
if (Test-ExpectedApp $existing) {
    Write-Host "[OK] $ExpectedProjectName is already running."
    if (-not $CheckOnly) {
        Start-Process $BrowserUrl
    }
    exit 0
}

if ($CheckOnly) {
    exit 1
}

$deadline = (Get-Date).AddSeconds([Math]::Max(5, $TimeoutSeconds))
$lastMessage = 'Waiting for the local service...'
Write-Host "Waiting up to $TimeoutSeconds seconds for the local service..."

while ((Get-Date) -lt $deadline) {
    $info = Get-AppInfo
    if (Test-ExpectedApp $info) {
        $version = [string]$info.version
        Write-Host "[OK] $ExpectedProjectName is ready. Version: $version"
        Start-Process $BrowserUrl
        exit 0
    }

    if ($null -ne $info) {
        $actualName = [string]$info.project_name
        $actualVersion = [string]$info.version
        $actualRepo = [string]$info.repo_url
        $port = ([System.Uri]$HealthUrl).Port
        Write-Host "[ERROR] Port $port is serving another project."
        Write-Host "Detected project: $actualName  Version: $actualVersion"
        if ($ExpectedVersion) { Write-Host "Expected version: $ExpectedVersion" }
        Write-Host "Detected repository: $actualRepo"
        Write-Host 'The browser was not opened to avoid opening the wrong project.'
        Write-Host "Close the other project that uses port $port, then run run.bat again."
        exit 2
    }

    Start-Sleep -Seconds 1
}

$port = ([System.Uri]$HealthUrl).Port
$listener = @(Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)
if ($listener.Count -gt 0) {
    Write-Host "[ERROR] Port $port is occupied, but it is not serving $ExpectedProjectName."
    Write-Host 'The browser was not opened to avoid opening the wrong project.'
    Write-Host "Close the program using port $port, then run run.bat again."
} else {
    Write-Host "[ERROR] The local service did not become ready within $TimeoutSeconds seconds."
    Write-Host 'Check the XiaoQi AI Canvas Server window for the startup error.'
    Write-Host 'Common causes: incomplete extraction, missing embedded Python, or missing dependencies.'
}
exit 1
