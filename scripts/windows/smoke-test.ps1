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
    desktop = @()
    success = $false
}

New-Item -ItemType Directory -Force -Path $ResultDir | Out-Null
$setupLog = "C:\NikaCRM-Inno-Setup.log"
$resultFile = Join-Path $ResultDir "smoke-result.json"

# Record every check instead of aborting on the first failure: one sandbox run
# then shows all broken steps, not only the first one.
function Add-Check([string] $Name, [bool] $Passed, [string] $Details = "") {
    $result.checks[$Name] = [ordered]@{ passed = $Passed; details = $Details }
    Write-Host ("[{0}] {1}: {2}" -f $(if ($Passed) { "OK" } else { "FAIL" }), $Name, $Details)
}

function Wait-Http([string] $Uri, [int] $Seconds = 60) {
    $deadline = (Get-Date).AddSeconds($Seconds)
    $lastError = $null
    while ((Get-Date) -lt $deadline) {
        try {
            return Invoke-WebRequest -Uri $Uri -UseBasicParsing -TimeoutSec 10
        }
        catch {
            $lastError = $_
            Start-Sleep -Seconds 2
        }
    }
    throw $lastError
}

try {
    # Older builds left nine shortcuts on the desktop; 1.0.11 keeps only three
    # and must delete the rest on upgrade. Seed old names first.
    $desktopSeed = [Environment]::GetFolderPath("CommonDesktopDirectory")
    if (Test-Path -LiteralPath $desktopSeed) {
        foreach ($name in @(
            "Nika CRM — Открыть.url",
            "Nika CRM — Доступ по сети (LAN).lnk",
            "Nika CRM — Журналы.lnk",
            "Ника Сервис — Сайт.url"
        )) {
            Set-Content -LiteralPath (Join-Path $desktopSeed $name) `
                -Value "[InternetShortcut]`r`nURL=http://127.0.0.1:5000" -Encoding ASCII
        }
    }

    $install = Start-Process -FilePath $InstallerPath -ArgumentList @(
        "/VERYSILENT",
        "/SUPPRESSMSGBOXES",
        "/NORESTART",
        "/SP-",
        "/LOG=`"$setupLog`""
    ) -Wait -PassThru
    Add-Check "installer_exit" ($install.ExitCode -eq 0) "exit=$($install.ExitCode)"

    $desktop = [Environment]::GetFolderPath("CommonDesktopDirectory")
    if (Test-Path -LiteralPath $desktop) {
        $result.desktop = @(Get-ChildItem -LiteralPath $desktop -Force -ErrorAction SilentlyContinue |
            Select-Object -ExpandProperty Name)
    }

    $webService = Get-Service -Name "NikaCRM-Web" -ErrorAction SilentlyContinue
    $pgService = Get-Service -Name "NikaCRM-PostgreSQL" -ErrorAction SilentlyContinue
    Add-Check "web_service_running" ($webService.Status -eq "Running") ([string] $webService.Status)
    Add-Check "postgres_service_running" ($pgService.Status -eq "Running") ([string] $pgService.Status)

    try {
        $response = Wait-Http "http://127.0.0.1:5000/login" 90
        Add-Check "http_login" ($response.StatusCode -eq 200) "status=$($response.StatusCode)"
    }
    catch {
        Add-Check "http_login" $false $_.Exception.Message
    }

    # A 200 on /login only proves the login page renders. Sign in as the demo
    # admin and render the dashboard, otherwise a 500 after login ships unseen.
    $webSession = New-Object Microsoft.PowerShell.Commands.WebRequestSession
    try {
        $loginPage = Invoke-WebRequest -Uri "http://127.0.0.1:5000/login" -UseBasicParsing `
            -WebSession $webSession -TimeoutSec 30
        $csrf = [regex]::Match($loginPage.Content, 'name="csrf_token"\s+value="([^"]+)"').Groups[1].Value
        if (-not $csrf) { throw "csrf_token not found on /login" }
        $signIn = Invoke-WebRequest -Uri "http://127.0.0.1:5000/login" -Method POST -UseBasicParsing `
            -WebSession $webSession -MaximumRedirection 5 -TimeoutSec 60 -Body @{
                username = "admin"
                password = "111111"
                csrf_token = $csrf
            }
        Add-Check "login_post" ($signIn.StatusCode -eq 200) "status=$($signIn.StatusCode) url=$($signIn.BaseResponse.ResponseUri)"
    }
    catch {
        $body = ""
        try { $body = $_.ErrorDetails.Message } catch { }
        if (-not $body -and $_.Exception.Response) {
            try {
                $stream = $_.Exception.Response.GetResponseStream()
                $body = (New-Object System.IO.StreamReader($stream)).ReadToEnd()
            }
            catch { }
        }
        if ($body) {
            Set-Content -LiteralPath (Join-Path $ResultDir "login-response.html") -Value $body -Encoding UTF8
        }
        Add-Check "login_post" $false $_.Exception.Message
    }

    try {
        $dashboard = Invoke-WebRequest -Uri "http://127.0.0.1:5000/" -UseBasicParsing `
            -WebSession $webSession -TimeoutSec 60
        Add-Check "dashboard_render" ($dashboard.StatusCode -eq 200) "status=$($dashboard.StatusCode)"
    }
    catch {
        try {
            if ($_.ErrorDetails.Message) {
                Set-Content -LiteralPath (Join-Path $ResultDir "dashboard-response.html") `
                    -Value $_.ErrorDetails.Message -Encoding UTF8
            }
        }
        catch { }
        Add-Check "dashboard_render" $false $_.Exception.Message
    }

    try {
        $appDir = "$env:ProgramFiles\NikaCRM"
        $dataDir = "$env:ProgramData\NikaCRM"
        $state = Get-Content (Join-Path $dataDir "installer\install-state.json") -Raw | ConvertFrom-Json
        $psql = Join-Path $appDir "runtime\postgresql\bin\psql.exe"
        $env:PGPASSWORD = $state.postgres_super_password
        $userCount = (& $psql -h 127.0.0.1 -p $state.postgres_port -U postgres -d nikacrm -tAc "SELECT count(*) FROM users").Trim()
        Add-Check "database_users" ([int] $userCount -ge 4) "users=$userCount"
    }
    catch {
        Add-Check "database_users" $false $_.Exception.Message
    }

    # Desktop keeps exactly three icons; everything else stays in the Start menu.
    $startMenu = Join-Path $env:ProgramData "Microsoft\Windows\Start Menu\Programs\Nika CRM"
    $startLinks = @(Get-ChildItem -LiteralPath $startMenu -File -ErrorAction SilentlyContinue)
    Add-Check "start_menu_group" (Test-Path -LiteralPath $startMenu) $startMenu
    Add-Check "start_menu_links" ($startLinks.Count -ge 8) "links=$($startLinks.Count)"
    Add-Check "site_shortcut" (@($startLinks | Where-Object { $_.Name -like "*Ника Сервис*Сайт*" }).Count -ge 1)
    $desired = @(
        "Nika CRM — Открыть.url",
        "Nika CRM — Перезапустить сервис.lnk",
        "Ника Сервис — Сайт.url"
    )
    $missing = @($desired | Where-Object { -not (Test-Path -LiteralPath (Join-Path $desktop $_)) })
    Add-Check "desktop_three_icons" ($missing.Count -eq 0) ("missing=" + ($missing -join ", "))
    $desktopLinks = @($result.desktop | Where-Object { $_ -like "Nika CRM*" -or $_ -like "Ника Сервис*" })
    Add-Check "desktop_shortcut_count" ($desktopLinks.Count -eq 3) "links=$($desktopLinks.Count)"
    Add-Check "desktop_old_removed" (-not (Test-Path -LiteralPath (Join-Path $desktop "Nika CRM — Доступ по сети (LAN).lnk")))

    try {
        Restart-Service -Name "NikaCRM-Web" -Force
        $response = Wait-Http "http://127.0.0.1:5000/login" 60
        Add-Check "service_restart" ($response.StatusCode -eq 200) "status=$($response.StatusCode)"
    }
    catch {
        Add-Check "service_restart" $false $_.Exception.Message
    }

    $failed = @($result.checks.GetEnumerator() | Where-Object { -not $_.Value.passed })
    if ($failed.Count -eq 0) {
        $result.success = $true
    }
    else {
        $result.error = "Smoke checks failed: " + (($failed | ForEach-Object { $_.Key }) -join ", ")
    }
}
catch {
    $result.error = $_.Exception.ToString()
}
finally {
    Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
    $result.finished_at = (Get-Date).ToString("o")
    $result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $resultFile -Encoding UTF8
    if (Test-Path -LiteralPath $setupLog) {
        Copy-Item -LiteralPath $setupLog -Destination (Join-Path $ResultDir "inno-setup.log") -Force
    }
    $sourceLogs = "$env:ProgramData\NikaCRM\logs"
    if (Test-Path -LiteralPath $sourceLogs) {
        Copy-Item -LiteralPath $sourceLogs -Destination (Join-Path $ResultDir "application-logs") -Recurse -Force
    }
    $layoutLog = "$env:WINDIR\Temp\NikaCRM-setup\ui-layout.txt"
    if (Test-Path -LiteralPath $layoutLog) {
        Copy-Item -LiteralPath $layoutLog -Destination (Join-Path $ResultDir "ui-layout.txt") -Force
    }
    Get-Service -Name "NikaCRM-Web", "NikaCRM-PostgreSQL" -ErrorAction SilentlyContinue |
        Select-Object Name, Status, StartType |
        ConvertTo-Json |
        Set-Content -LiteralPath (Join-Path $ResultDir "services.json") -Encoding UTF8
    Get-ChildItem "$env:ProgramFiles\NikaCRM", "$env:ProgramData\NikaCRM" -Recurse -ErrorAction SilentlyContinue |
        Select-Object FullName, Length, LastWriteTime |
        ConvertTo-Json -Depth 3 |
        Set-Content -LiteralPath (Join-Path $ResultDir "installed-files.json") -Encoding UTF8

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
