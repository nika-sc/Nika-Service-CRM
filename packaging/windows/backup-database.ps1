<#
.SYNOPSIS
    Резервная копия базы Nika CRM в папку, которая переживает удаление программы.

.DESCRIPTION
    Делает SQL-дамп базы nikacrm и копию файла настроек .env в
    %ProgramData%\NikaCRM-backup. Эту папку деинсталлятор не удаляет, поэтому
    после переустановки данные подхватываются автоматически.

    Запускать от имени администратора:
        powershell -ExecutionPolicy Bypass -File backup-database.ps1
#>
[CmdletBinding()]
param(
    [string] $AppDir = "$env:ProgramFiles\NikaCRM",
    [string] $DataDir = "$env:ProgramData\NikaCRM",
    [string] $BackupDir = "$env:ProgramData\NikaCRM-backup",
    [switch] $Quiet
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

function Write-Step([string] $Message) {
    if (-not $Quiet) {
        Write-Host ("[{0}] {1}" -f (Get-Date -Format "HH:mm:ss"), $Message)
    }
}

try {
    $pgDump = Join-Path $AppDir "runtime\postgresql\bin\pg_dump.exe"
    $stateFile = Join-Path $DataDir "installer\install-state.json"
    $envFile = Join-Path $DataDir ".env"

    if (-not (Test-Path -LiteralPath $pgDump)) {
        throw "pg_dump.exe не найден: $pgDump"
    }
    if (-not (Test-Path -LiteralPath $stateFile)) {
        throw "Не найден $stateFile — пароль базы неизвестен."
    }

    $state = Get-Content -LiteralPath $stateFile -Raw | ConvertFrom-Json
    $port = [int] $state.postgres_port

    $service = Get-Service -Name "NikaCRM-PostgreSQL" -ErrorAction SilentlyContinue
    if ($service -and $service.Status -ne "Running") {
        Write-Step "Запускаю службу PostgreSQL для резервной копии"
        & net.exe start "NikaCRM-PostgreSQL" | Out-Null
        Start-Sleep -Seconds 3
    }

    New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null
    # Дамп содержит все данные CRM: каталог только для администраторов.
    & icacls.exe $BackupDir /inheritance:r /grant:r "*S-1-5-18:(OI)(CI)(F)" "*S-1-5-32-544:(OI)(CI)(F)" | Out-Null

    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $dumpFile = Join-Path $BackupDir "nikacrm-$stamp.sql"

    Write-Step "Сохраняю базу в $dumpFile"
    $env:PGPASSWORD = [string] $state.postgres_super_password
    try {
        # -w: установщик работает без окна, ждать ввод пароля здесь нельзя.
        & $pgDump `
            -h "127.0.0.1" `
            -p $port `
            -U "postgres" `
            -d "nikacrm" `
            -w `
            --no-owner `
            --no-privileges `
            --encoding "UTF8" `
            -f $dumpFile
        $dumpExit = $LASTEXITCODE
    }
    finally {
        Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
    }

    if ($dumpExit -ne 0) {
        throw "pg_dump завершился с кодом $dumpExit."
    }
    $dumpInfo = Get-Item -LiteralPath $dumpFile -ErrorAction SilentlyContinue
    if (-not $dumpInfo -or $dumpInfo.Length -lt 1024) {
        throw "Дамп пустой или не создан: $dumpFile"
    }

    if (Test-Path -LiteralPath $envFile) {
        Copy-Item -LiteralPath $envFile -Destination (Join-Path $BackupDir "env-$stamp.txt") -Force
    }

    # Оставляем последние 10 копий, чтобы папка не росла бесконечно.
    Get-ChildItem -LiteralPath $BackupDir -Filter "nikacrm-*.sql" -File |
        Sort-Object LastWriteTime -Descending |
        Select-Object -Skip 10 |
        Remove-Item -Force -ErrorAction SilentlyContinue

    Write-Step ("Готово: {0:N1} МБ" -f ($dumpInfo.Length / 1MB))
    exit 0
}
catch {
    Write-Host "[Nika CRM] Резервная копия не создана: $($_.Exception.Message)"
    exit 1
}
