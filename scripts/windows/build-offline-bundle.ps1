[CmdletBinding()]
param(
    [switch] $SkipDownload,
    [switch] $SkipCompile,
    [string] $IsccPath = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$packagingDir = Join-Path $repoRoot "packaging\windows"
$assetsDir = Join-Path $packagingDir "assets"
$wheelhouse = Join-Path $assetsDir "wheelhouse"
$manifestPath = Join-Path $assetsDir "manifest.json"
$requirements = Join-Path $packagingDir "requirements-windows.txt"

$artifacts = @(
    @{
        Name = "python-installer.exe"
        Url = "https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe"
        Sha256 = "67B5635E80EA51072B87941312D00EC8927C4DB9BA18938F7AD2D27B328B95FB"
    },
    @{
        Name = "postgresql-installer.exe"
        Url = "https://get.enterprisedb.com/postgresql/postgresql-18.4-1-windows-x64.exe"
        Sha256 = "44B8187D2DB7E866495952D8260A1D7252CBB5125843142E1F0BF30115D23279"
    },
    @{
        Name = "nssm-2.24.zip"
        Url = "https://nssm.cc/release/nssm-2.24.zip"
        Sha256 = "727D1E42275C605E0F04ABA98095C38A8E1E46DEF453CDFFCE42869428AA6743"
    }
)

function Test-Hash([string] $Path, [string] $Expected) {
    if (-not (Test-Path -LiteralPath $Path)) { return $false }
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash -eq $Expected
}

function Get-Artifact($Artifact) {
    $destination = Join-Path $assetsDir $Artifact.Name
    if (Test-Hash $destination $Artifact.Sha256) {
        Write-Host "[OK] $($Artifact.Name)"
        return
    }
    if ($SkipDownload) {
        throw "Missing or invalid artifact while -SkipDownload is set: $destination"
    }
    Remove-Item -LiteralPath $destination -Force -ErrorAction SilentlyContinue
    Write-Host "[DOWNLOAD] $($Artifact.Url)"
    & curl.exe -L --fail --retry 4 --retry-delay 3 --output $destination $Artifact.Url
    if ($LASTEXITCODE -ne 0) { throw "Download failed: $($Artifact.Url)" }
    if (-not (Test-Hash $destination $Artifact.Sha256)) {
        throw "SHA256 mismatch: $destination"
    }
}

New-Item -ItemType Directory -Force -Path $assetsDir, $wheelhouse | Out-Null

foreach ($artifact in $artifacts) {
    Get-Artifact $artifact
}

$nssmZip = Join-Path $assetsDir "nssm-2.24.zip"
$nssmTemp = Join-Path $assetsDir "_nssm"
Remove-Item -LiteralPath $nssmTemp -Recurse -Force -ErrorAction SilentlyContinue
Expand-Archive -LiteralPath $nssmZip -DestinationPath $nssmTemp -Force
$nssmSource = Join-Path $nssmTemp "nssm-2.24\win64\nssm.exe"
if (-not (Test-Path -LiteralPath $nssmSource)) {
    throw "win64 nssm.exe not found after archive extraction."
}
Copy-Item -LiteralPath $nssmSource -Destination (Join-Path $assetsDir "nssm.exe") -Force
Remove-Item -LiteralPath $nssmTemp -Recurse -Force

if (-not $SkipDownload) {
    Write-Host "[WHEELHOUSE] Resolving Windows x64 CPython 3.12 wheels"
    Remove-Item -LiteralPath $wheelhouse -Recurse -Force
    New-Item -ItemType Directory -Force -Path $wheelhouse | Out-Null
    # http-ece is pure Python but is currently published only as an sdist.
    # Build its universal wheel once on the connected build computer so the
    # target machine never needs a compiler or network access.
    & python -m pip wheel `
        --disable-pip-version-check `
        --no-deps `
        --wheel-dir $wheelhouse `
        "http-ece>=1.1.0"
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to build the pure-Python http-ece wheel."
    }
    & python -m pip download `
        --disable-pip-version-check `
        --only-binary=:all: `
        --find-links $wheelhouse `
        --platform win_amd64 `
        --python-version 312 `
        --implementation cp `
        --abi cp312 `
        --dest $wheelhouse `
        --requirement $requirements
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to build the Windows offline wheelhouse."
    }
}

$wheelFiles = @(Get-ChildItem -LiteralPath $wheelhouse -File)
if ($wheelFiles.Count -eq 0) {
    throw "Wheelhouse is empty: $wheelhouse"
}

$manifest = [ordered]@{
    generated_at = (Get-Date).ToUniversalTime().ToString("o")
    python = "3.12.10"
    postgresql = "18.4-1"
    nssm = "2.24"
    files = @()
}

foreach ($file in Get-ChildItem -LiteralPath $assetsDir -File -Recurse | Where-Object { $_.FullName -ne $manifestPath }) {
    $relative = $file.FullName.Substring($assetsDir.Length + 1).Replace("\", "/")
    $manifest.files += [ordered]@{
        path = $relative
        size = $file.Length
        sha256 = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash
    }
}
$manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $manifestPath -Encoding UTF8

& (Join-Path $PSScriptRoot "verify-bundle.ps1") -AssetsDir $assetsDir
if ($LASTEXITCODE -ne 0) { throw "Offline bundle verification failed." }

if (-not $SkipCompile) {
    if (-not (Test-Path -LiteralPath $IsccPath)) {
        throw "Inno Setup compiler not found: $IsccPath"
    }
    Write-Host "[BUILD] Compiling NikaCRM.iss"
    & $IsccPath (Join-Path $packagingDir "NikaCRM.iss")
    if ($LASTEXITCODE -ne 0) { throw "Inno Setup compilation failed." }
    Write-Host "[DONE] Installer: $(Join-Path $packagingDir 'output')"
}
