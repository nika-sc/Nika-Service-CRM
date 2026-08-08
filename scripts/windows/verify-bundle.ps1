[CmdletBinding()]
param(
    [string] $AssetsDir = ""
)

$ErrorActionPreference = "Stop"
if (-not $AssetsDir) {
    $repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
    $AssetsDir = Join-Path $repoRoot "packaging\windows\assets"
}
$manifestPath = Join-Path $AssetsDir "manifest.json"

if (-not (Test-Path -LiteralPath $manifestPath)) {
    throw "Bundle manifest not found: $manifestPath"
}

$manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
$failures = @()

foreach ($entry in $manifest.files) {
    $path = Join-Path $AssetsDir ($entry.path.Replace("/", "\"))
    if (-not (Test-Path -LiteralPath $path)) {
        $failures += "MISSING: $($entry.path)"
        continue
    }
    $file = Get-Item -LiteralPath $path
    if ([long] $file.Length -ne [long] $entry.size) {
        $failures += "SIZE: $($entry.path)"
        continue
    }
    $actual = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash
    if ($actual -ne $entry.sha256) {
        $failures += "SHA256: $($entry.path)"
    }
}

foreach ($required in @(
    "python-installer.exe",
    "postgresql-installer.exe",
    "nssm.exe",
    "wheelhouse"
)) {
    if (-not (Test-Path -LiteralPath (Join-Path $AssetsDir $required))) {
        $failures += "REQUIRED: $required"
    }
}

if ($failures.Count -gt 0) {
    $failures | ForEach-Object { Write-Error $_ }
    exit 1
}

Write-Host ("[OK] Offline bundle verified: {0} files" -f $manifest.files.Count)
exit 0
