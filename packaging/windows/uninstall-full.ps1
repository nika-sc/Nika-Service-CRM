<#
.SYNOPSIS
    Полное удаление Nika CRM с Windows: службы, файлы, ярлыки, правило брандмауэра.

.DESCRIPTION
    Аварийный сценарий для случаев, когда обычное удаление недоступно или
    установка повреждена (например, после установки новой версии поверх старой).
    Запускать от имени администратора:

        powershell -ExecutionPolicy Bypass -File uninstall-full.ps1
        powershell -ExecutionPolicy Bypass -File uninstall-full.ps1 -RemoveData

    Без -RemoveData база данных и настройки в %ProgramData%\NikaCRM остаются,
    и повторная установка подхватит их. С -RemoveData удаляется всё.
#>
[CmdletBinding()]
param(
    [string] $AppDir = "$env:ProgramFiles\NikaCRM",
    [string] $DataDir = "$env:ProgramData\NikaCRM",
    [switch] $RemoveData,
    [switch] $Force
)

$ErrorActionPreference = "Continue"
$ProgressPreference = "SilentlyContinue"

$identity = [Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $identity.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Error "Запустите PowerShell от имени администратора."
    exit 1
}

function Write-Step([string] $Message) {
    Write-Host ("[{0}] {1}" -f (Get-Date -Format "HH:mm:ss"), $Message)
}

function Remove-NikaService([string] $Name) {
    $service = Get-Service -Name $Name -ErrorAction SilentlyContinue
    if (-not $service) {
        Write-Step "Служба $Name не найдена"
        return
    }
    Write-Step "Останавливаю службу $Name"
    & net.exe stop $Name /y | Out-Null
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        $service = Get-Service -Name $Name -ErrorAction SilentlyContinue
        if (-not $service -or $service.Status -eq "Stopped") { break }
        Start-Sleep -Seconds 1
    }
    $nssm = Join-Path $AppDir "runtime\nssm.exe"
    if ($Name -eq "NikaCRM-Web" -and (Test-Path -LiteralPath $nssm)) {
        & $nssm remove $Name confirm | Out-Null
    }
    & sc.exe delete $Name | Out-Null
    Write-Step "Служба $Name удалена"
}

if (-not $Force -and -not $PSBoundParameters.ContainsKey("Confirm")) {
    $target = if ($RemoveData) { "вместе с базой данных и настройками" } else { "с сохранением базы в $DataDir" }
    Write-Host ""
    Write-Host "Будет удалена Nika CRM ($target)." -ForegroundColor Yellow
    $answer = Read-Host "Продолжить? (y/N)"
    if ($answer -notmatch '^(y|Y|д|Д)') {
        Write-Host "Отменено."
        exit 0
    }
}

$backupScript = Join-Path $AppDir "app\packaging\windows\backup-database.ps1"
$backupDir = "$env:ProgramData\NikaCRM-backup"
if ((Test-Path -LiteralPath $backupScript) -and (Test-Path -LiteralPath $DataDir)) {
    Write-Step "Резервная копия базы в $backupDir"
    & powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File $backupScript `
        -AppDir $AppDir -DataDir $DataDir -BackupDir $backupDir
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Резервная копия не создана."
        if ($RemoveData -and -not $Force) {
            $answer = Read-Host "Всё равно удалить базу без копии? (y/N)"
            if ($answer -notmatch '^(y|Y|д|Д)') {
                Write-Host "Отменено."
                exit 1
            }
        }
    }
}

Remove-NikaService "NikaCRM-Web"
Remove-NikaService "NikaCRM-PostgreSQL"

# EDB-инсталлятор PostgreSQL держит свою запись в реестре и локальную учётную
# запись службы; штатный деинсталлятор убирает их корректно.
$pgUninstaller = Join-Path $AppDir "runtime\postgresql\uninstall-postgresql.exe"
if (Test-Path -LiteralPath $pgUninstaller) {
    Write-Step "Запускаю деинсталлятор PostgreSQL"
    Start-Process -FilePath $pgUninstaller -ArgumentList @("--mode", "unattended") -Wait -NoNewWindow
}

Write-Step "Удаляю правило брандмауэра"
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

Write-Step "Удаляю ярлыки"
$desktop = [Environment]::GetFolderPath("CommonDesktopDirectory")
$programs = [Environment]::GetFolderPath("CommonPrograms")
Get-ChildItem -LiteralPath $desktop -File -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -like "Nika CRM*" } |
    Remove-Item -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath (Join-Path $programs "Nika CRM") -Recurse -Force -ErrorAction SilentlyContinue

# Запись в "Программы и компоненты" от Inno Setup.
Write-Step "Удаляю запись в списке программ"
$appId = "{D606AA35-BA7B-46F0-96E4-72EB1CCCE693}_is1"
foreach ($hive in @("HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
                    "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall")) {
    $key = Join-Path $hive $appId
    if (Test-Path -LiteralPath $key) {
        Remove-Item -LiteralPath $key -Recurse -Force -ErrorAction SilentlyContinue
    }
}

if (Test-Path -LiteralPath $AppDir) {
    Write-Step "Удаляю $AppDir"
    Remove-Item -LiteralPath $AppDir -Recurse -Force -ErrorAction SilentlyContinue
    if (Test-Path -LiteralPath $AppDir) {
        Write-Warning "Часть файлов занята. Перезагрузите ПК и удалите папку вручную: $AppDir"
    }
}

if ($RemoveData) {
    if (Test-Path -LiteralPath $DataDir) {
        Write-Step "Удаляю $DataDir (база данных и настройки)"
        Remove-Item -LiteralPath $DataDir -Recurse -Force -ErrorAction SilentlyContinue
        if (Test-Path -LiteralPath $DataDir) {
            Write-Warning "Не удалось удалить полностью: $DataDir. Перезагрузите ПК и повторите."
        }
    }
}
else {
    Write-Step "База данных и настройки сохранены: $DataDir"
}

Write-Host ""
Write-Host "Готово. Можно устанавливать Nika CRM заново." -ForegroundColor Green
exit 0
