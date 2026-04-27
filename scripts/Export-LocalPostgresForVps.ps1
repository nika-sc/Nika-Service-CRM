<#
.SYNOPSIS
    Plain SQL дамп локального PostgreSQL для восстановления на сервер с более старой major (например PG16).
.DESCRIPTION
    Читает DATABASE_URL из .env, вызывает pg_dump (PostgreSQL 18 из Program Files),
    удаляет директивы, несовместимые с PG16 (transaction_timeout, restrict/unrestrict).
    Рабочий VPS на Postgres 18: для него проще снять дамп тем же major: pg_dump -Fc клиентом 18.
    Результат: database/backups/local_nikacrm_pg16safe_<timestamp>.sql
#>
$ErrorActionPreference = "Stop"
$root = if ($PSScriptRoot) { (Resolve-Path (Join-Path $PSScriptRoot "..")).Path } else { (Get-Location).Path }
Set-Location $root

$envFile = Join-Path $root ".env"
if (-not (Test-Path $envFile)) { throw ".env не найден: $envFile" }
$line = (Get-Content $envFile -Raw) -split "`n" | Where-Object { $_ -match '^DATABASE_URL=' } | Select-Object -First 1
if (-not $line) { throw "В .env нет строки DATABASE_URL=" }
$url = ($line -replace '^DATABASE_URL=', '').Trim()
if ($url -notmatch '^postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)$') {
    throw "DATABASE_URL не распознан как postgresql://..."
}
$user = $Matches[1]
$pass = $Matches[2]
$hostDb = $Matches[3]
$port = $Matches[4]
$db = $Matches[5]

$pgDump = "C:\Program Files\PostgreSQL\18\bin\pg_dump.exe"
if (-not (Test-Path $pgDump)) {
    $pgDump = "C:\Program Files\PostgreSQL\16\bin\pg_dump.exe"
}
if (-not (Test-Path $pgDump)) { throw "Не найден pg_dump: установите PostgreSQL client 16+ или укажите путь." }

$backupDir = Join-Path $root "database\backups"
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$rawSql = Join-Path $backupDir "local_nikacrm_plain_${ts}.sql"
$safeSql = Join-Path $backupDir "local_nikacrm_pg16safe_${ts}.sql"

$env:PGPASSWORD = $pass
try {
    & $pgDump -h $hostDb -p $port -U $user -d $db --no-owner --no-privileges -Fp -f $rawSql
} finally {
    Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
}

Get-Content -LiteralPath $rawSql | Where-Object {
    $_ -notmatch '^\s*SET transaction_timeout' -and
    $_ -notmatch '^\s*\\restrict\s' -and
    $_ -notmatch '^\s*\\unrestrict\s'
} | Set-Content -LiteralPath $safeSql -Encoding utf8

Write-Host "RAW:  $rawSql ($((Get-Item $rawSql).Length) bytes)"
Write-Host "SAFE: $safeSql ($((Get-Item $safeSql).Length) bytes)"
Write-Host "Пример загрузки на VPS:"
Write-Host "  scp `"$safeSql`" user@YOUR_SERVER:/path/to/backups/"
Write-Host "  (далее DROP/CREATE БД и psql -f ... см. документацию деплоя)"
