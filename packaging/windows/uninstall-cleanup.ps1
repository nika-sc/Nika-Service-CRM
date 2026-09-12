[CmdletBinding()]
param(
    [string] $AppDir = "$env:ProgramFiles\NikaCRM"
)

$ErrorActionPreference = "SilentlyContinue"
$nssm = Join-Path $AppDir "runtime\nssm.exe"

function Stop-NikaService([string] $Name) {
    # net stop waits for the SCM to report STOPPED; sc stop returns immediately
    # and the following delete would leave the service in "marked for deletion".
    & net.exe stop $Name /y | Out-Null
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        $service = Get-Service -Name $Name -ErrorAction SilentlyContinue
        if (-not $service -or $service.Status -eq "Stopped") { break }
        Start-Sleep -Seconds 1
    }
}

if (Test-Path -LiteralPath $nssm) {
    & $nssm stop "NikaCRM-Web" confirm | Out-Null
    Stop-NikaService "NikaCRM-Web"
    & $nssm remove "NikaCRM-Web" confirm | Out-Null
}
else {
    Stop-NikaService "NikaCRM-Web"
}
& sc.exe delete "NikaCRM-Web" | Out-Null

Stop-NikaService "NikaCRM-PostgreSQL"
& sc.exe delete "NikaCRM-PostgreSQL" | Out-Null

# EDB keeps a registry entry and the local "postgres" service account. Without
# its own uninstaller they survive and the next install fails on the account
# password check.
$pgUninstaller = Join-Path $AppDir "runtime\postgresql\uninstall-postgresql.exe"
if (Test-Path -LiteralPath $pgUninstaller) {
    Start-Process -FilePath $pgUninstaller -ArgumentList @("--mode", "unattended") -Wait -NoNewWindow
}

foreach ($ruleName in @("Nika CRM (HTTP 5000)")) {
    try {
        Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue |
            Remove-NetFirewallRule -ErrorAction SilentlyContinue
    }
    catch {
        # Sandbox / locked-down hosts may lack Firewall CIM classes.
    }
    & netsh.exe advfirewall firewall delete rule name="$ruleName" | Out-Null
}

# Shortcut names use an em dash, so match by wildcard instead of exact names:
# a hardcoded hyphen left every icon on the desktop after uninstall.
$desktop = [Environment]::GetFolderPath("CommonDesktopDirectory")
$programs = [Environment]::GetFolderPath("CommonPrograms")
Get-ChildItem -LiteralPath $desktop -File -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -like "Nika CRM*" } |
    Remove-Item -Force
Remove-Item -LiteralPath (Join-Path $programs "Nika CRM") -Recurse -Force

# %ProgramData%\NikaCRM is handled by the uninstaller itself: it asks whether the
# database, .env and installer secrets should be wiped or kept for a reinstall.
exit 0
