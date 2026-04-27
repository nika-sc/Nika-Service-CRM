<#
.SYNOPSIS
    Выдаёт роли из DATABASE_URL права на все объекты в public (после pg_restore --no-owner).

.DESCRIPTION
    Исправляет ошибку login: psycopg2.errors.InsufficientPrivilege / «нет доступа к таблице users»,
    когда таблицы принадлежат postgres (или другой роли из дампа), а CRM подключается как пользователь из .env.

.PARAMETER PostgresSuperUserPassword
    Пароль суперпользователя (postgres). Иначе переменная окружения LOCAL_PG_SUPER_PASSWORD.

.EXAMPLE
    $env:LOCAL_PG_SUPER_PASSWORD = '***'
    .\scripts\Grant-LocalPostgresAppPrivileges.ps1
#>
[CmdletBinding()]
param(
    [string] $PostgresSuperUserPassword = $env:LOCAL_PG_SUPER_PASSWORD,
    [string] $HostDb = "localhost",
    [int] $Port = 5432,
    [string] $SuperUser = "postgres"
)

$ErrorActionPreference = "Stop"
$root = if ($PSScriptRoot) { (Resolve-Path (Join-Path $PSScriptRoot "..")).Path } else { (Get-Location).Path }
Set-Location $root

if (-not $PostgresSuperUserPassword) {
    throw "Укажите -PostgresSuperUserPassword или LOCAL_PG_SUPER_PASSWORD"
}

$envFile = Join-Path $root ".env"
if (-not (Test-Path -LiteralPath $envFile)) { throw ".env не найден: $envFile" }
$line = (Get-Content $envFile -Raw) -split "`n" | Where-Object { $_ -match '^DATABASE_URL=' } | Select-Object -First 1
if (-not $line) { throw "В .env нет строки DATABASE_URL=" }
$url = ($line -replace '^DATABASE_URL=', '').Trim()
if ($url -notmatch '^postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)$') {
    throw "DATABASE_URL не распознан как postgresql://..."
}
$appUser = $Matches[1]
$dbName = $Matches[5]

if ($appUser -notmatch '^[a-zA-Z0-9_]+$') {
    throw "DATABASE_URL user contains unsupported characters: $appUser"
}

$psql = "C:\Program Files\PostgreSQL\18\bin\psql.exe"
if (-not (Test-Path $psql)) { throw "Не найден psql: $psql" }

$env:PGPASSWORD = $PostgresSuperUserPassword
try {
    $grantSql = @"
GRANT USAGE ON SCHEMA public TO $appUser;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO $appUser;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO $appUser;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO $appUser;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $appUser;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO $appUser;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT EXECUTE ON FUNCTIONS TO $appUser;
"@
    & $psql -h $HostDb -p $Port -U $SuperUser -d $dbName -v ON_ERROR_STOP=1 -c $grantSql
}
finally {
    Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
}

Write-Host ("Done. Granted public schema privileges to {0} on database {1}." -f $appUser, $dbName)
