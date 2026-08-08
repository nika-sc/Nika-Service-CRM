[CmdletBinding()]
param(
    [string] $DataDir = "$env:ProgramData\NikaCRM"
)

$ErrorActionPreference = "Stop"

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Run this script as Administrator. Database passwords are stored in an admin-only file."
}

$stateFile = Join-Path $DataDir "installer\install-state.json"
$envFile = Join-Path $DataDir ".env"

if (-not (Test-Path -LiteralPath $stateFile)) {
    throw "Installer state not found: $stateFile"
}

$state = Get-Content -LiteralPath $stateFile -Raw -Encoding UTF8 | ConvertFrom-Json
$port = [int] $state.postgres_port
$superPassword = [string] $state.postgres_super_password
$appPassword = [string] $state.app_db_password

Write-Host "Nika CRM PostgreSQL credentials"
Write-Host "================================"
Write-Host "Host:                 127.0.0.1"
Write-Host "Port:                 $port"
Write-Host "Database:             nikacrm"
Write-Host ""
Write-Host "Superuser (postgres):"
Write-Host "  User:               postgres"
Write-Host "  Password:           $superPassword"
Write-Host ""
Write-Host "Application role:"
Write-Host "  User:               nikacrm"
Write-Host "  Password:           $appPassword"
Write-Host ""
Write-Host "pgAdmin connection (application role):"
Write-Host "  Host=127.0.0.1  Port=$port  Database=nikacrm  Username=nikacrm"
Write-Host ""
Write-Host "Connection URI:"
Write-Host "  postgresql://nikacrm:$appPassword@127.0.0.1:$port/nikacrm"
Write-Host ""
if (Test-Path -LiteralPath $envFile) {
    Write-Host "Also stored in DATABASE_URL inside: $envFile"
}
Write-Host "State file (admin-only): $stateFile"
Write-Host ""
Write-Host "Note: passwords are random per installation. The demo login password 111111"
Write-Host "is only for CRM web accounts (admin/manager/...), not for PostgreSQL."
