[CmdletBinding()]
param(
    [string] $AppDir = "$env:ProgramFiles\NikaCRM"
)

$ErrorActionPreference = "SilentlyContinue"
$nssm = Join-Path $AppDir "runtime\nssm.exe"

if (Test-Path -LiteralPath $nssm) {
    & $nssm stop "NikaCRM-Web" confirm | Out-Null
    & $nssm remove "NikaCRM-Web" confirm | Out-Null
}
else {
    & sc.exe stop "NikaCRM-Web" | Out-Null
    & sc.exe delete "NikaCRM-Web" | Out-Null
}

& sc.exe stop "NikaCRM-PostgreSQL" | Out-Null
Start-Sleep -Seconds 2
& sc.exe delete "NikaCRM-PostgreSQL" | Out-Null

$desktop = [Environment]::GetFolderPath("CommonDesktopDirectory")
$programs = [Environment]::GetFolderPath("CommonPrograms")
Remove-Item -LiteralPath (Join-Path $desktop "Nika CRM - Открыть.lnk") -Force
Remove-Item -LiteralPath (Join-Path $desktop "Nika CRM - Перезапустить сервис.lnk") -Force
Remove-Item -LiteralPath (Join-Path $programs "Nika CRM") -Recurse -Force

# %ProgramData%\NikaCRM intentionally remains: it contains the database,
# installer secrets and logs. An administrator may remove it manually.
exit 0
