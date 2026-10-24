[CmdletBinding()]
param(
    [int] $TimeoutMinutes = 30
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$packageDir = Join-Path $repoRoot "packaging\windows"
$outputDir = Join-Path $packageDir "output"
$resultDir = Join-Path $packageDir "smoke-results"
$configPath = Join-Path $packageDir "NikaCRM-Smoke.wsb"
$sandboxExe = "$env:WINDIR\System32\WindowsSandbox.exe"
$installer = Get-ChildItem -LiteralPath $outputDir -Filter "NikaCRM-Offline-Setup-*.exe" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if (-not (Test-Path -LiteralPath $sandboxExe)) {
    throw "Windows Sandbox is not installed."
}
if (-not $installer) {
    throw "Compiled installer not found in $outputDir"
}

Remove-Item -LiteralPath $resultDir -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $resultDir | Out-Null
# Windows PowerShell 5.1 in the sandbox reads a BOM-less script as ANSI and
# chokes on Cyrillic. Always hand it a copy with a UTF-8 BOM.
$smokeText = [System.IO.File]::ReadAllText(
    (Join-Path $PSScriptRoot "smoke-test.ps1"), [System.Text.Encoding]::UTF8)
[System.IO.File]::WriteAllText(
    (Join-Path $resultDir "smoke-test.ps1"), $smokeText, (New-Object System.Text.UTF8Encoding $true))
Copy-Item -LiteralPath $installer.FullName -Destination $resultDir

$escapedResults = [Security.SecurityElement]::Escape($resultDir)
$installerName = $installer.Name
# The LogonCommand runs through cmd so its console output survives in
# logon.txt even when the PowerShell script dies before writing a result.
$launcher = @"
@echo off
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File C:\NikaCRM-Smoke\smoke-test.ps1 -InstallerPath "C:\NikaCRM-Smoke\$installerName" -ResultDir C:\NikaCRM-Smoke -ShutdownWhenDone > C:\NikaCRM-Smoke\logon.txt 2>&1
"@
$launcher | Set-Content -LiteralPath (Join-Path $resultDir "run-smoke.cmd") -Encoding ASCII
$config = @"
<Configuration>
  <MappedFolders>
    <MappedFolder>
      <HostFolder>$escapedResults</HostFolder>
      <SandboxFolder>C:\NikaCRM-Smoke</SandboxFolder>
      <ReadOnly>false</ReadOnly>
    </MappedFolder>
  </MappedFolders>
  <Networking>Disable</Networking>
  <ClipboardRedirection>Disable</ClipboardRedirection>
  <LogonCommand>
    <Command>cmd.exe /c C:\NikaCRM-Smoke\run-smoke.cmd</Command>
  </LogonCommand>
</Configuration>
"@
$config | Set-Content -LiteralPath $configPath -Encoding UTF8

Write-Host "Starting clean Windows Sandbox smoke test..."
Start-Process -FilePath $sandboxExe -ArgumentList "`"$configPath`""

$resultFile = Join-Path $resultDir "smoke-result.json"
$deadline = (Get-Date).AddMinutes($TimeoutMinutes)
while ((Get-Date) -lt $deadline) {
    if (Test-Path -LiteralPath $resultFile) {
        Start-Sleep -Seconds 3
        $result = Get-Content -LiteralPath $resultFile -Raw -Encoding UTF8 | ConvertFrom-Json
        $result | ConvertTo-Json -Depth 8
        if ($result.success) { exit 0 }
        exit 1
    }
    Start-Sleep -Seconds 5
}

throw "Windows Sandbox smoke test timed out after $TimeoutMinutes minutes."
