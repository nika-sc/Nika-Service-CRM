[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string] $AppDir,
    [Parameter(Mandatory = $true)]
    [string] $DataDir,
    [Parameter(Mandatory = $true)]
    [string] $AssetsDir
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$appRoot = Join-Path $AppDir "app"
$runtimeRoot = Join-Path $AppDir "runtime"
$pythonRoot = Join-Path $runtimeRoot "python"
$pythonExe = Join-Path $pythonRoot "python.exe"
$pgRoot = Join-Path $runtimeRoot "postgresql"
$pgBin = Join-Path $pgRoot "bin"
$pgData = Join-Path $DataDir "PostgreSQL\data"
$logsDir = Join-Path $DataDir "logs"
$installerDir = Join-Path $DataDir "installer"
$envFile = Join-Path $DataDir ".env"
$stateFile = Join-Path $installerDir "install-state.json"
$bootstrapLog = Join-Path $logsDir "setup.log"
$pythonInstaller = Join-Path $AssetsDir "python-installer.exe"
$postgresInstaller = Join-Path $AssetsDir "postgresql-installer.exe"
$wheelhouse = Join-Path $AssetsDir "wheelhouse"
$nssmSource = Join-Path $AssetsDir "nssm.exe"
$nssm = Join-Path $runtimeRoot "nssm.exe"
$serviceName = "NikaCRM-Web"
$postgresServiceName = "NikaCRM-PostgreSQL"

New-Item -ItemType Directory -Force -Path $runtimeRoot, $logsDir, $installerDir, $pgData | Out-Null
Start-Transcript -LiteralPath $bootstrapLog -Append | Out-Null
Write-Host "[Nika CRM Setup] Bootstrap version 1.0.5 (2026-08-08)"

function Write-Step([string] $Message) {
    Write-Host ("[{0}] {1}" -f (Get-Date -Format "HH:mm:ss"), $Message)
}

function Invoke-Native {
    param(
        [Parameter(Mandatory = $true)]
        [string] $FilePath,
        [string[]] $Arguments = @(),
        [int[]] $SuccessCodes = @(0)
    )
    Write-Host ("RUN: {0} {1}" -f $FilePath, ($Arguments -join " "))
    $process = Start-Process -FilePath $FilePath -ArgumentList $Arguments -Wait -PassThru -NoNewWindow
    if ($process.ExitCode -notin $SuccessCodes) {
        throw "Command failed with exit code $($process.ExitCode): $FilePath"
    }
}

function Invoke-Nssm {
    param(
        [Parameter(Mandatory = $true)]
        [string[]] $Arguments,
        [int[]] $SuccessCodes = @(0)
    )
    # Windows PowerShell 5.1 converts native stderr into ErrorRecord objects.
    # NSSM uses stderr for some informational messages, so temporarily avoid
    # turning those messages into terminating PowerShell errors and rely on
    # the native process exit code instead.
    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & $nssm @Arguments
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousPreference
    }
    if ($exitCode -notin $SuccessCodes) {
        throw "NSSM failed with exit code $exitCode`: $($Arguments -join ' ')"
    }
}

function New-SafePassword([string] $Prefix) {
    $bytes = New-Object byte[] 18
    $rng = [Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $rng.GetBytes($bytes)
    }
    finally {
        $rng.Dispose()
    }
    $hex = ([BitConverter]::ToString($bytes)).Replace("-", "").ToLowerInvariant()
    return $Prefix + $hex
}

function Test-PortAvailable([int] $Port) {
    try {
        $listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, $Port)
        $listener.Start()
        $listener.Stop()
        return $true
    }
    catch {
        return $false
    }
}

function Import-DotEnv([string] $Path) {
    foreach ($line in Get-Content -LiteralPath $Path -Encoding UTF8) {
        $trimmed = $line.Trim().TrimStart([char]0xFEFF)
        if (-not $trimmed -or $trimmed.StartsWith("#") -or -not $trimmed.Contains("=")) {
            continue
        }
        $name, $value = $trimmed.Split("=", 2)
        [Environment]::SetEnvironmentVariable($name.Trim().TrimStart([char]0xFEFF), $value.Trim(), "Process")
    }
}

function Write-DotEnvUtf8NoBom {
    param(
        [Parameter(Mandatory = $true)][string] $Path,
        [Parameter(Mandatory = $true)][string[]] $Lines
    )
    # Windows PowerShell 5.1 Set-Content -Encoding UTF8 writes BOM; python-dotenv
    # then sees the first key as "`uFEFFTRUSTED_HOSTS" and LAN @private is ignored.
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllLines($Path, $Lines, $utf8NoBom)
}

function Get-PrimaryLanIPv4 {
    try {
        $candidates = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction Stop |
            Where-Object {
                $_.IPAddress -and
                $_.IPAddress -notlike "127.*" -and
                $_.IPAddress -notlike "169.254.*" -and
                $_.PrefixOrigin -ne "WellKnown"
            } |
            Sort-Object -Property InterfaceMetric, PrefixLength
        if ($candidates) {
            return [string] $candidates[0].IPAddress
        }
    }
    catch {
        # Fall through to empty string.
    }
    return ""
}

function Merge-DotEnvFile {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Path,
        [Parameter(Mandatory = $true)]
        [hashtable] $AlwaysSet,
        [Parameter(Mandatory = $true)]
        [hashtable] $SetIfMissing
    )

    $existing = @{}
    $order = New-Object System.Collections.Generic.List[string]
    if (Test-Path -LiteralPath $Path) {
        foreach ($line in Get-Content -LiteralPath $Path -Encoding UTF8) {
            $trimmed = $line.Trim().TrimStart([char]0xFEFF)
            if (-not $trimmed -or $trimmed.StartsWith("#") -or -not $trimmed.Contains("=")) {
                continue
            }
            $name, $value = $trimmed.Split("=", 2)
            $key = $name.Trim().TrimStart([char]0xFEFF)
            if (-not $existing.ContainsKey($key)) {
                $order.Add($key) | Out-Null
            }
            $existing[$key] = $value.Trim()
        }
    }

    foreach ($key in $AlwaysSet.Keys) {
        if (-not $existing.ContainsKey($key)) {
            $order.Add($key) | Out-Null
        }
        $existing[$key] = [string] $AlwaysSet[$key]
    }
    foreach ($key in $SetIfMissing.Keys) {
        if (-not $existing.ContainsKey($key)) {
            $order.Add($key) | Out-Null
            $existing[$key] = [string] $SetIfMissing[$key]
        }
    }

    $lines = foreach ($key in $order) {
        "{0}={1}" -f $key, $existing[$key]
    }
    Write-DotEnvUtf8NoBom -Path $Path -Lines $lines
}

function Ensure-NikaCrmFirewallRule {
    param(
        [int] $Port = 5000
    )
    $ruleName = "Nika CRM (HTTP $Port)"

    # Always recreate with Profile Any so upgrades replace older Private/Domain-only rules
    # (Windows Sandbox / some Wi-Fi adapters use Public).
    try {
        Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue |
            Remove-NetFirewallRule -ErrorAction SilentlyContinue
        New-NetFirewallRule `
            -DisplayName $ruleName `
            -Direction Inbound `
            -Action Allow `
            -Protocol TCP `
            -LocalPort $Port `
            -Profile Any `
            -ErrorAction Stop | Out-Null
        Write-Step "Ensured firewall rule: $ruleName (Any profile)"
        return
    }
    catch {
        Write-Step "NetFirewallRule unavailable ($($_.Exception.Message)); trying netsh fallback"
    }

    # Sandbox / some SKUs lack Firewall CIM classes ("Invalid class"). netsh is enough.
    try {
        & netsh.exe advfirewall firewall delete rule name="$ruleName" | Out-Null
        & netsh.exe advfirewall firewall add rule `
            name="$ruleName" `
            dir=in action=allow protocol=TCP localport=$Port `
            profile=any | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Step "Ensured firewall rule via netsh: $ruleName (Any profile)"
            return
        }
        Write-Step "WARN: could not create firewall rule (netsh exit $LASTEXITCODE). Open TCP $Port manually for LAN access."
    }
    catch {
        Write-Step "WARN: firewall rule skipped ($($_.Exception.Message)). Open TCP $Port manually for LAN access."
    }
}

try {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw "Setup must run with administrator privileges."
    }

    foreach ($required in @($pythonInstaller, $postgresInstaller, $wheelhouse, $nssmSource)) {
        if (-not (Test-Path -LiteralPath $required)) {
            throw "Offline bundle component is missing: $required"
        }
    }

    $state = $null
    if (Test-Path -LiteralPath $stateFile) {
        $state = Get-Content -LiteralPath $stateFile -Raw -Encoding UTF8 | ConvertFrom-Json
    }
    if (-not $state) {
        $postgresPort = @(5432, 55432, 55433) | Where-Object { Test-PortAvailable $_ } | Select-Object -First 1
        if (-not $postgresPort) {
            throw "No free PostgreSQL port found (checked 5432, 55432, 55433)."
        }
        $state = [ordered]@{
            postgres_port = [int] $postgresPort
            postgres_super_password = New-SafePassword "NikaPgA1"
            app_db_password = New-SafePassword "NikaAppA1"
            installed_at = (Get-Date).ToString("o")
        }
        $state | ConvertTo-Json | Set-Content -LiteralPath $stateFile -Encoding UTF8
        & icacls.exe $stateFile /inheritance:r /grant:r "*S-1-5-18:(F)" "*S-1-5-32-544:(F)" | Out-Null
    }

    $postgresPort = [int] $state.postgres_port
    $postgresSuperPassword = [string] $state.postgres_super_password
    $appDbPassword = [string] $state.app_db_password

    if (-not (Test-Path -LiteralPath $pythonExe)) {
        Write-Step "Installing bundled Python runtime"
        Invoke-Native $pythonInstaller @(
            "/quiet",
            "InstallAllUsers=1",
            "TargetDir=`"$pythonRoot`"",
            "Include_pip=1",
            "Include_launcher=0",
            "Include_test=0",
            "Shortcuts=0",
            "PrependPath=0",
            "CompileAll=0"
        ) @(0)
    }
    if (-not (Test-Path -LiteralPath $pythonExe)) {
        throw "Python installation did not create $pythonExe"
    }

    Write-Step "Installing application dependencies from offline wheelhouse"
    Invoke-Native $pythonExe @(
        "-m", "pip", "install",
        "--disable-pip-version-check",
        "--no-index",
        "--find-links", "`"$wheelhouse`"",
        "-r", "`"$(Join-Path $appRoot 'packaging\windows\requirements-windows.txt')`""
    ) @(0)

    if (-not (Test-Path -LiteralPath (Join-Path $pgBin "psql.exe"))) {
        Write-Step "Installing bundled PostgreSQL 18"
        Invoke-Native $postgresInstaller @(
            "--mode", "unattended",
            "--unattendedmodeui", "none",
            "--prefix", "`"$pgRoot`"",
            "--datadir", "`"$pgData`"",
            "--serverport", "$postgresPort",
            "--superpassword", "`"$postgresSuperPassword`"",
            "--servicepassword", "`"$postgresSuperPassword`"",
            "--servicename", $postgresServiceName,
            "--enable-components", "server,commandlinetools",
            "--disable-components", "pgAdmin,stackbuilder",
            "--create_shortcuts", "0"
        ) @(0)
    }

    $psql = Join-Path $pgBin "psql.exe"
    if (-not (Test-Path -LiteralPath $psql)) {
        throw "PostgreSQL installation did not create $psql"
    }
    $env:PATH = "$pgBin;$env:PATH"
    $env:PGPASSWORD = $postgresSuperPassword

    Write-Step "Waiting for PostgreSQL service"
    & sc.exe start $postgresServiceName | Out-Null
    $ready = $false
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        & (Join-Path $pgBin "pg_isready.exe") -h 127.0.0.1 -p $postgresPort -U postgres | Out-Null
        if ($LASTEXITCODE -eq 0) {
            $ready = $true
            break
        }
        Start-Sleep -Seconds 1
    }
    if (-not $ready) {
        throw "PostgreSQL did not become ready on port $postgresPort."
    }

    Write-Step "Creating application role and database"
    $roleSql = @"
DO `$do`$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'nikacrm') THEN
        CREATE ROLE nikacrm LOGIN PASSWORD '$appDbPassword';
    ELSE
        ALTER ROLE nikacrm WITH LOGIN PASSWORD '$appDbPassword';
    END IF;
END
`$do`$;
"@
    & $psql -h 127.0.0.1 -p $postgresPort -U postgres -d postgres -v ON_ERROR_STOP=1 -c $roleSql
    if ($LASTEXITCODE -ne 0) { throw "Failed to create PostgreSQL role." }

    # SELECT EXISTS always emits t/f. This is intentionally used instead of a
    # query that returns zero rows: Windows PowerShell 5.1 represents empty
    # native stdout as $null and calling Trim() on it aborts a clean install.
    $dbExistsOutput = @(& $psql -h 127.0.0.1 -p $postgresPort -U postgres -d postgres -tAc "SELECT EXISTS (SELECT 1 FROM pg_database WHERE datname='nikacrm')")
    if ($LASTEXITCODE -ne 0) { throw "Failed to check whether the PostgreSQL database exists." }
    $dbExists = (($dbExistsOutput | ForEach-Object { [string] $_ }) -join "").Trim()
    if ($dbExists -ne "t") {
        & (Join-Path $pgBin "createdb.exe") -h 127.0.0.1 -p $postgresPort -U postgres -O nikacrm nikacrm
        if ($LASTEXITCODE -ne 0) { throw "Failed to create PostgreSQL database." }
    }

    $usersTableOutput = @(& $psql -h 127.0.0.1 -p $postgresPort -U postgres -d nikacrm -tAc "SELECT to_regclass('public.users') IS NOT NULL")
    if ($LASTEXITCODE -ne 0) { throw "Failed to inspect the demo database." }
    $usersTable = (($usersTableOutput | ForEach-Object { [string] $_ }) -join "").Trim()
    if ($usersTable -ne "t") {
        Write-Step "Importing sanitized demo database"
        $dump = Join-Path $appRoot "database\bootstrap\nikacrm_public_sanitized.sql"
        & $psql -h 127.0.0.1 -p $postgresPort -U postgres -d nikacrm -v ON_ERROR_STOP=1 -f $dump
        if ($LASTEXITCODE -ne 0) { throw "Demo database import failed." }
    }

    $grantSql = @"
GRANT ALL ON SCHEMA public TO nikacrm;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO nikacrm;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO nikacrm;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO nikacrm;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO nikacrm;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO nikacrm;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT EXECUTE ON FUNCTIONS TO nikacrm;
"@
    & $psql -h 127.0.0.1 -p $postgresPort -U postgres -d nikacrm -v ON_ERROR_STOP=1 -c $grantSql
    if ($LASTEXITCODE -ne 0) { throw "Failed to grant database privileges." }

    Write-Step "Writing application environment"
    $computerName = ($env:COMPUTERNAME -as [string])
    if (-not $computerName) { $computerName = "localhost" }
    $trustedHosts = "localhost,127.0.0.1,@private,$computerName,$computerName.local"
    # LAN defaults always applied on install/repair so an old ProgramData\.env
    # without @private cannot block http://<lan-ip>:5000 after upgrade.
    $alwaysSet = @{
        "FLASK_ENV" = "production"
        "DB_DRIVER" = "postgres"
        "DATABASE_URL" = "postgresql://nikacrm:$appDbPassword@127.0.0.1:$postgresPort/nikacrm"
        "APP_HOST" = "0.0.0.0"
        "APP_PORT" = "5000"
        "TRUSTED_HOSTS" = $trustedHosts
        "SOCKETIO_CORS_ALLOWED_ORIGINS" = "http://localhost:5000,http://127.0.0.1:5000,@private"
        "SESSION_COOKIE_SECURE" = "0"
        "USE_HTTPS" = "false"
    }
    $setIfMissing = @{
        "SECRET_KEY" = (New-SafePassword "NikaSecretA1")
        "RATELIMIT_STORAGE_URI" = "memory://"
        "TIMEZONE_OFFSET" = "3"
        "PUBLIC_LANDING" = "0"
        "DEMO_LOGIN_BANNER" = "0"
        # Пустой SMTP-блок: заполняется в CRM Настройки → Почта (синхронизируется обратно в .env)
        "MAIL_SERVER" = ""
        "MAIL_PORT" = "587"
        "MAIL_USE_TLS" = "True"
        "MAIL_USE_SSL" = "False"
        "MAIL_USERNAME" = ""
        "MAIL_PASSWORD" = ""
        "MAIL_DEFAULT_SENDER" = ""
        "MAIL_TIMEOUT" = "15"
    }
    if (-not (Test-Path -LiteralPath $envFile)) {
        $alwaysSet["SECRET_KEY"] = $setIfMissing["SECRET_KEY"]
        $alwaysSet["RATELIMIT_STORAGE_URI"] = "memory://"
        $alwaysSet["TIMEZONE_OFFSET"] = "3"
        $alwaysSet["PUBLIC_LANDING"] = "0"
        $alwaysSet["DEMO_LOGIN_BANNER"] = "0"
    }
    Merge-DotEnvFile -Path $envFile -AlwaysSet $alwaysSet -SetIfMissing $setIfMissing
    # Комментарий-подсказка SMTP один раз (ключи уже в файле через SetIfMissing)
    $envText = [System.IO.File]::ReadAllText($envFile)
    if ($envText -notmatch "отправки писем клиентам \(SMTP\)") {
        $mailComment = @"

# =============================================================================
# Настройки для отправки писем клиентам (SMTP)
# Заполните в CRM: Настройки → Общие → Почта (SMTP) — ключи ниже обновятся автоматически.
# Или пропишите вручную (пароль приложения, не обычный пароль почты).
# =============================================================================
"@
        $utf8NoBom = New-Object System.Text.UTF8Encoding $false
        [System.IO.File]::AppendAllText($envFile, $mailComment.Replace("`n", "`r`n"), $utf8NoBom)
    }
    Import-DotEnv $envFile

    Write-Step "Opening Windows Firewall for local network access"
    Ensure-NikaCrmFirewallRule -Port 5000

    Write-Step "Verifying application role privileges"
    & (Join-Path $appRoot "scripts\Grant-LocalPostgresAppPrivileges.ps1") `
        -PostgresSuperUserPassword $postgresSuperPassword `
        -HostDb "127.0.0.1" `
        -Port $postgresPort `
        -SuperUser "postgres" `
        -EnvFile $envFile `
        -PsqlPath $psql

    Write-Step "Applying pending PostgreSQL migrations"
    Set-Location -LiteralPath $appRoot
    Invoke-Native $pythonExe @("scripts\run_migrations.py") @(0)

    Write-Step "Installing Windows service"
    # On a repair install, a failed older service may still be running from
    # runtime\nssm.exe and therefore lock that file. Use the temporary NSSM
    # bundled with Setup to stop/remove the old service before overwriting it.
    $nssm = $nssmSource
    $existingWebService = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
    if ($existingWebService) {
        Invoke-Nssm @("stop", $serviceName, "confirm") @(0, 1, 3)
        for ($attempt = 0; $attempt -lt 20; $attempt++) {
            $serviceState = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
            if ((-not $serviceState) -or ($serviceState.Status -eq "Stopped")) {
                break
            }
            Start-Sleep -Milliseconds 500
        }
        $serviceState = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
        if ($serviceState -and $serviceState.Status -ne "Stopped") {
            $serviceProcess = Get-CimInstance Win32_Service -Filter "Name='$serviceName'" -ErrorAction SilentlyContinue
            if ($serviceProcess -and [int] $serviceProcess.ProcessId -gt 0) {
                Stop-Process -Id ([int] $serviceProcess.ProcessId) -Force -ErrorAction SilentlyContinue
                Start-Sleep -Seconds 1
            }
        }
        Invoke-Nssm @("remove", $serviceName, "confirm") @(0, 1)
        for ($attempt = 0; $attempt -lt 30; $attempt++) {
            if (-not (Get-Service -Name $serviceName -ErrorAction SilentlyContinue)) {
                break
            }
            Start-Sleep -Milliseconds 500
        }
        if (Get-Service -Name $serviceName -ErrorAction SilentlyContinue) {
            throw "Existing $serviceName service could not be removed."
        }
    }
    $nssm = Join-Path $runtimeRoot "nssm.exe"
    $nssmCopied = $false
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        try {
            Copy-Item -LiteralPath $nssmSource -Destination $nssm -Force
            $nssmCopied = $true
            break
        }
        catch [System.IO.IOException] {
            Start-Sleep -Milliseconds 500
        }
    }
    if (-not $nssmCopied) {
        throw "NSSM runtime file remained locked after removing the old service: $nssm"
    }
    $serviceEntry = Join-Path $appRoot "nikacrm_service.py"
    if (-not (Test-Path -LiteralPath $serviceEntry)) {
        throw "Service entry point not found: $serviceEntry"
    }
    Invoke-Nssm @("install", $serviceName, $pythonExe)
    Invoke-Nssm @("set", $serviceName, "AppParameters", "nikacrm_service.py")
    Invoke-Nssm @("set", $serviceName, "AppDirectory", $appRoot)
    Invoke-Nssm @("set", $serviceName, "DisplayName", "Nika CRM Web Server")
    Invoke-Nssm @("set", $serviceName, "Description", "Nika CRM web server (LAN-ready on port 5000)")
    Invoke-Nssm @("set", $serviceName, "Start", "SERVICE_AUTO_START")
    Invoke-Nssm @("set", $serviceName, "AppExit", "Default", "Restart")
    Invoke-Nssm @("set", $serviceName, "AppRestartDelay", "5000")
    Invoke-Nssm @("set", $serviceName, "AppNoConsole", "1")
    Invoke-Nssm @("set", $serviceName, "AppStdout", (Join-Path $logsDir "web-stdout.log"))
    Invoke-Nssm @("set", $serviceName, "AppStderr", (Join-Path $logsDir "web-stderr.log"))
    Invoke-Nssm @("set", $serviceName, "AppRotateFiles", "1")
    Invoke-Nssm @("set", $serviceName, "AppRotateBytes", "5242880")
    & sc.exe failure $serviceName reset= 86400 actions= restart/5000/restart/10000/restart/30000 | Out-Null
    Invoke-Nssm @("start", $serviceName)

    Write-Step "Waiting for Nika CRM"
    $healthy = $false
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        try {
            $response = Invoke-WebRequest -Uri "http://127.0.0.1:5000/login" -UseBasicParsing -TimeoutSec 2
            if ($response.StatusCode -eq 200) {
                $healthy = $true
                break
            }
        }
        catch {
            Start-Sleep -Seconds 1
        }
    }
    if (-not $healthy) {
        throw "Nika CRM service did not pass the HTTP health check."
    }

    $lanIp = Get-PrimaryLanIPv4
    Write-Step "Installation completed successfully"
    Write-Host "Local URL:  http://127.0.0.1:5000"
    if ($lanIp) {
        Write-Host "LAN URL:    http://${lanIp}:5000"
        Write-Host "Change demo passwords if other devices on the network can reach this PC."
    }
    else {
        Write-Host "LAN URL:    (no private IPv4 detected; open http://<this-pc-ip>:5000 from another device)"
    }
}
catch {
    Write-Error ("Automatic setup failed: {0}`n{1}" -f $_.Exception.Message, $_.ScriptStackTrace)
    throw
}
finally {
    Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
    Stop-Transcript | Out-Null
}
