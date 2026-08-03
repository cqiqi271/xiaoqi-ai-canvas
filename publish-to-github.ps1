$ErrorActionPreference = 'Stop'

$repo = 'cqiqi271/xiaoqi-ai-canvas'
$local = Split-Path -Parent $MyInvocation.MyCommand.Path
$headCommit = (git -C $local rev-parse HEAD).Trim()
$baseRef = gh api "repos/$repo/git/ref/heads/main" --jq '.object.sha'
$baseCommit = gh api "repos/$repo/git/commits/$baseRef" | ConvertFrom-Json
$baseTree = $baseCommit.tree.sha

function Write-JsonTempFile($json) {
    $tmp = [IO.Path]::GetTempFileName()
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [IO.File]::WriteAllText($tmp, $json, $utf8NoBom)
    return $tmp
}

function Invoke-GhJson($arguments, $inputFile) {
    $output = if($inputFile) { gh api @arguments --input $inputFile } else { gh api @arguments }
    if($LASTEXITCODE -ne 0) { throw "gh api failed: $($arguments -join ' ')" }
    return $output | ConvertFrom-Json
}

# Use git ls-files instead of ls-tree to avoid quoted output and path parsing issues
# with files that contain spaces, Unicode, or shell-escaped characters.
$tracked = git -C $local -c core.quotepath=false ls-files | Where-Object { $_ -and $_ -ne 'publish-to-github.ps1' }
$entries = @()
foreach($path in $tracked) {
    $filePath = Join-Path $local ($path -replace '/', [IO.Path]::DirectorySeparatorChar)
    if(-not (Test-Path -LiteralPath $filePath)) { continue }
    $bytes = [IO.File]::ReadAllBytes($filePath)
    $blobBody = @{ content = [Convert]::ToBase64String($bytes); encoding = 'base64' } | ConvertTo-Json -Depth 4
    $blobTmp = Write-JsonTempFile $blobBody
    try {
        $blob = Invoke-GhJson @('-X','POST',"repos/$repo/git/blobs") $blobTmp
    } finally {
        Remove-Item -LiteralPath $blobTmp -Force -ErrorAction SilentlyContinue
    }
    $entries += [ordered]@{ path = $path; mode = '100644'; type = 'blob'; sha = $blob.sha }
}

$treeBody = @{ base_tree = $baseTree; tree = $entries } | ConvertTo-Json -Depth 8
$treeTmp = Write-JsonTempFile $treeBody
try {
    $newTree = Invoke-GhJson @('-X','POST',"repos/$repo/git/trees") $treeTmp
} finally {
    Remove-Item -LiteralPath $treeTmp -Force -ErrorAction SilentlyContinue
}

$commitBody = @{ message = 'Publish xiaoqi canvas update 2026.08.04'; tree = $newTree.sha; parents = @($baseRef) } | ConvertTo-Json -Depth 6
$commitTmp = Write-JsonTempFile $commitBody
try {
    $newCommit = Invoke-GhJson @('-X','POST',"repos/$repo/git/commits") $commitTmp
} finally {
    Remove-Item -LiteralPath $commitTmp -Force -ErrorAction SilentlyContinue
}

$refBody = @{ sha = $newCommit.sha; force = $false } | ConvertTo-Json -Depth 4
$refTmp = Write-JsonTempFile $refBody
try {
    Invoke-GhJson @('-X','PATCH',"repos/$repo/git/refs/heads/main") $refTmp | Out-Null
} finally {
    Remove-Item -LiteralPath $refTmp -Force -ErrorAction SilentlyContinue
}

Write-Output $newCommit.sha
