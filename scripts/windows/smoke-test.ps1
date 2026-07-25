[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string] $InstallerPath,
    [Parameter(Mandatory = $true)]
    [string] $ResultDir,
    [switch] $KeepInstalled,
    [switch] $ShutdownWhenDone
)

$ErrorActionPreference = "Stop"
$result = [ordered]@{
    started_at = (Get-Date).ToString("o")
    computer = $env:COMPUTERNAME
    installer = $InstallerPath
    checks = [ordered]@{}
    success = $false
}

New-Item -ItemType Directory -Force -Path $ResultDir | Out-Null
$setupLog = "C:\NikaCRM-Inno-Setup.log"
$resultFile = Join-Path $ResultDir "smoke-result.json"

function Set-Check([string] $Name, [bool] $Passed, [string] $Details = "") {
    $result.checks[$Name] = [ordered]@{ passed = $Passed; details = $Details }
    if (-not $Passed) { throw "Smoke check failed: $Name. $Details" }
}

try {
    $install = Start-Process -FilePath $InstallerPath -ArgumentList @(
        "/VERYSILENT",
        "/SUPPRESSMSGBOXES",
        "/NORESTART",
        "/SP-",
        "/LOG=`"$setupLog`""
    ) -Wait -PassThru
    Set-Check "installer_exit" ($install.ExitCode -eq 0) "exit=$($install.ExitCode)"

    $webService = Get-Service -Name "NikaCRM-Web" -ErrorAction SilentlyContinue
    $pgService = Get-Service -Name "NikaCRM-PostgreSQL" -ErrorAction SilentlyContinue
    Set-Check "web_service_running" ($webService.Status -eq "Running") ([string] $webService.Status)
    Set-Check "postgres_service_running" ($pgService.Status -eq "Running") ([string] $pgService.Status)

    $response = Invoke-WebRequest -Uri "http://127.0.0.1:5000/login" -UseBasicParsing -TimeoutSec 15
    Set-Check "http_login" ($response.StatusCode -eq 200) "status=$($response.StatusCode)"

    $appDir = "$env:ProgramFiles\NikaCRM"
    $dataDir = "$env:ProgramData\NikaCRM"
    $state = Get-Content (Join-Path $dataDir "installer\install-state.json") -Raw | ConvertFrom-Json
    $psql = Join-Path $appDir "runtime\postgresql\bin\psql.exe"
    $env:PGPASSWORD = $state.postgres_super_password
    $userCount = (& $psql -h 127.0.0.1 -p $state.postgres_port -U postgres -d nikacrm -tAc "SELECT count(*) FROM users").Trim()
    Set-Check "database_users" ([int] $userCount -ge 4) "users=$userCount"

    $desktop = [Environment]::GetFolderPath("CommonDesktopDirectory")
    Set-Check "open_shortcut" (Test-Path (Join-Path $desktop "Nika CRM - Открыть.lnk"))
    Set-Check "restart_shortcut" (Test-Path (Join-Path $desktop "Nika CRM - Перезапустить сервис.lnk"))

    Restart-Service -Name "NikaCRM-Web" -Force
    Start-Sleep -Seconds 5
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:5000/login" -UseBasicParsing -TimeoutSec 15
    Set-Check "service_restart" ($response.StatusCode -eq 200) "status=$($response.StatusCode)"

    $result.success = $true
}
catch {
    $result.error = $_.Exception.ToString()
}
finally {
    $result.finished_at = (Get-Date).ToString("o")
    $result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $resultFile -Encoding UTF8
    if (Test-Path -LiteralPath $setupLog) {
        Copy-Item -LiteralPath $setupLog -Destination (Join-Path $ResultDir "inno-setup.log") -Force
    }
    $sourceLogs = "$env:ProgramData\NikaCRM\logs"
    if (Test-Path -LiteralPath $sourceLogs) {
        Copy-Item -LiteralPath $sourceLogs -Destination (Join-Path $ResultDir "application-logs") -Recurse -Force
    }
    Get-Service -Name "NikaCRM-Web", "NikaCRM-PostgreSQL" -ErrorAction SilentlyContinue |
        Select-Object Name, Status, StartType |
        ConvertTo-Json |
        Set-Content -LiteralPath (Join-Path $ResultDir "services.json") -Encoding UTF8
    Get-ChildItem "$env:ProgramFiles\NikaCRM", "$env:ProgramData\NikaCRM" -Recurse -ErrorAction SilentlyContinue |
        Select-Object FullName, Length, LastWriteTime |
        ConvertTo-Json -Depth 3 |
        Set-Content -LiteralPath (Join-Path $ResultDir "installed-files.json") -Encoding UTF8
    Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue

    if (-not $KeepInstalled -and $result.success) {
        $uninstaller = "$env:ProgramFiles\NikaCRM\unins000.exe"
        if (Test-Path -LiteralPath $uninstaller) {
            Start-Process -FilePath $uninstaller -ArgumentList @(
                "/VERYSILENT",
                "/SUPPRESSMSGBOXES",
                "/NORESTART"
            ) -Wait
        }
    }
    if ($ShutdownWhenDone) {
        & shutdown.exe /s /t 5 | Out-Null
    }
}

if (-not $result.success) { exit 1 }
exit 0
