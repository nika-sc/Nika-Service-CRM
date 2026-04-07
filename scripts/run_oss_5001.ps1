param(
    [string]$DatabaseUrl = "postgresql://nikacrm:change-me@localhost:5432/nikacrm",
    [string]$AppHost = "127.0.0.1",
    [int]$Port = 5001
)

$env:DB_DRIVER = "postgres"
$env:DATABASE_URL = $DatabaseUrl
$env:APP_HOST = $AppHost
$env:APP_PORT = "$Port"
$env:FLASK_ENV = "development"
$env:FLASK_DEBUG = "True"

Write-Host "DB_DRIVER=$env:DB_DRIVER"
Write-Host "DATABASE_URL=$env:DATABASE_URL"
Write-Host "APP_HOST=$env:APP_HOST"
Write-Host "APP_PORT=$env:APP_PORT"

python scripts/run_migrations.py
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

python run.py
