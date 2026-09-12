[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string] $AppDir
)

# Created after bootstrap succeeds so the desktop is not a false "install done" signal.
$ErrorActionPreference = "Stop"
$desktop = [Environment]::GetFolderPath("CommonDesktopDirectory")
if (-not $desktop) {
    $desktop = Join-Path $env:PUBLIC "Desktop"
}

$openUrl = Join-Path $desktop "Nika CRM — Открыть.url"
@(
    "[InternetShortcut]"
    "URL=http://127.0.0.1:5000"
) | Set-Content -LiteralPath $openUrl -Encoding ASCII

$ws = New-Object -ComObject WScript.Shell
$restart = $ws.CreateShortcut((Join-Path $desktop "Nika CRM — Перезапустить сервис.lnk"))
$restart.TargetPath = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
$restart.Arguments = "-NoLogo -NoProfile -ExecutionPolicy Bypass -File `"$AppDir\app\packaging\windows\restart-service.ps1`""
$restart.WorkingDirectory = Join-Path $AppDir "app"
$restart.WindowStyle = 1
$restart.Description = "Перезапустить локальный сервер Nika CRM"
$restart.Save()
