<#
.SYNOPSIS
    OWASP ZAP: baseline или automation-framework против локального/докерного CRM.

.DESCRIPTION
    Требуется Docker. CRM должен быть доступен с контейнера ZAP:
    - Windows Docker Desktop: по умолчанию http://host.docker.internal:5000/
    - Linux: передайте -Target http://172.17.0.1:5000/ или IP хоста.

    Роли и сессии ZAP baseline не обходит — для этого после baseline запустите:
      .\.venv-win\Scripts\python.exe scripts\zap\role_security_scan.py

.PARAMETER Target
    Базовый URL для zap-baseline.py (паук + правила baseline).

.PARAMETER Mode
    baseline — zap-baseline.py (HTML+JSON в reports/zap).
    automation — файл automation-baseline.yaml (контекст + паук + passive wait).

.EXAMPLE
    .\scripts\zap\Run-ZapBaseline.ps1
    .\scripts\zap\Run-ZapBaseline.ps1 -Target "http://host.docker.internal:5000/" -Mode full
#>
[CmdletBinding()]
param(
    [string] $Target = "http://host.docker.internal:5000/",
    [ValidateSet("baseline", "full", "automation")]
    [string] $Mode = "baseline"
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$reportsDir = Join-Path $repoRoot "reports\zap"
New-Item -ItemType Directory -Force -Path $reportsDir | Out-Null

$docker = Get-Command docker -ErrorAction SilentlyContinue
if (-not $docker) {
    Write-Host "Docker не найден в PATH. Установите Docker Desktop или используйте:" -ForegroundColor Yellow
    Write-Host "  python scripts\zap\role_security_scan.py --base-url http://127.0.0.1:5000" -ForegroundColor Yellow
    exit 1
}

$image = "ghcr.io/zaproxy/zaproxy:stable"
Write-Host "Pull $image ..." -ForegroundColor Cyan
docker pull $image | Out-Host

$vol = "${reportsDir}:/zap/wrk"

if ($Mode -eq "automation") {
    $yaml = Join-Path $PSScriptRoot "automation-baseline.yaml"
    if (-not (Test-Path -LiteralPath $yaml)) { throw "Не найден $yaml" }
    Copy-Item -Force $yaml (Join-Path $reportsDir "automation-baseline.yaml")
    Write-Host "Запуск Automation Framework (пассив + паук)..." -ForegroundColor Cyan
    docker run --rm -v $vol -t $image zap.sh -cmd -autorun /zap/wrk/automation-baseline.yaml
    exit $LASTEXITCODE
}

if ($Mode -eq "full") {
    Write-Host "ZAP full scan (долго, активные проверки)..." -ForegroundColor Cyan
    docker run --rm -v $vol -t $image zap-full-scan.py -t $Target -r report-full.html -J report-full.json
    exit $LASTEXITCODE
}

Write-Host "ZAP baseline -> $Target" -ForegroundColor Cyan
docker run --rm -v $vol -t $image zap-baseline.py -t $Target -r report-baseline.html -J report-baseline.json
exit $LASTEXITCODE
