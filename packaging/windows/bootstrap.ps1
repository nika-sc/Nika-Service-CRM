[CmdletBinding()]
param(
    [string] $AppDir = "",
    [string] $DataDir = "",
    [string] $AssetsDir = "",
    [string] $ProgressDir = ""
)

# Do not use Mandatory params: a hidden installer window would sit forever
# waiting for AppDir instead of writing a log.
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
# Python writes redirected output in the locale code page; force UTF-8 so a
# traceback from pip or run_migrations.py stays readable in setup.log.
$env:PYTHONIOENCODING = "utf-8"

# Handshake + setup log MUST live outside ProgramData and Inno {tmp}.
# A failed install rolls back [Dirs] (so ProgramData\NikaCRM\logs vanishes)
# and deletes {tmp}. Windows\Temp and the desktop copy survive.
$stableDir = Join-Path $env:SystemRoot "Temp\NikaCRM-setup"
New-Item -ItemType Directory -Force -Path $stableDir | Out-Null
if ([string]::IsNullOrWhiteSpace($ProgressDir)) {
    $ProgressDir = $stableDir
}
# Inno polls this PID with a message pump. Write it before any other work so
# the wizard unfreezes even if a later command hangs.
[System.IO.File]::WriteAllText(
    (Join-Path $ProgressDir "setup-progress.pid"),
    "$PID",
    [System.Text.Encoding]::Default
)
$bootstrapLog = Join-Path $stableDir "setup.log"
@(
    "[{0}] bootstrap pid {1}" -f (Get-Date -Format "o"), $PID
    "AppDir=$AppDir"
    "DataDir=$DataDir"
    "AssetsDir=$AssetsDir"
    "ProgressDir=$ProgressDir"
    "PSVersion=$($PSVersionTable.PSVersion)"
    "CommandLine=$($MyInvocation.Line)"
) | Set-Content -LiteralPath $bootstrapLog -Encoding UTF8

$script:SecretValues = New-Object System.Collections.Generic.List[string]

function Protect-Secrets([string] $Text) {
    if ([string]::IsNullOrEmpty($Text)) { return $Text }
    $result = $Text
    foreach ($secret in $script:SecretValues) {
        if ($secret) { $result = $result.Replace($secret, "***") }
    }
    return $result
}

function Write-SetupError([string] $Text) {
    # setup-error.txt is copied to the public desktop, so it must never carry
    # the generated PostgreSQL passwords.
    $safe = Protect-Secrets $Text
    $errorFile = Join-Path $ProgressDir "setup-error.txt"
    try {
        [System.IO.File]::WriteAllText($errorFile, $safe, [System.Text.Encoding]::Default)
    }
    catch {
    }
    try {
        Add-Content -LiteralPath $bootstrapLog -Value $safe -Encoding UTF8
    }
    catch {
    }
}

if ([string]::IsNullOrWhiteSpace($AppDir) -or [string]::IsNullOrWhiteSpace($DataDir) -or [string]::IsNullOrWhiteSpace($AssetsDir)) {
    Write-SetupError "ERROR: missing AppDir/DataDir/AssetsDir (script started, parameters did not bind)."
    [System.IO.File]::WriteAllText((Join-Path $ProgressDir "setup-progress.done"), "1", [System.Text.Encoding]::Default)
    throw "Missing installer parameters. See $bootstrapLog"
}

$appRoot = Join-Path $AppDir "app"
$runtimeRoot = Join-Path $AppDir "runtime"
$pythonRoot = Join-Path $runtimeRoot "python"
$pythonExe = Join-Path $pythonRoot "python.exe"
$pgRoot = Join-Path $runtimeRoot "postgresql"
$pgBin = Join-Path $pgRoot "bin"
$pgData = Join-Path $DataDir "PostgreSQL\data"
$logsDir = Join-Path $DataDir "logs"
# Survives uninstall on purpose: holds the pg_dump taken before a full removal.
$backupDir = Join-Path (Split-Path -Parent $DataDir) "NikaCRM-backup"
$installerDir = Join-Path $DataDir "installer"
$envFile = Join-Path $DataDir ".env"
$stateFile = Join-Path $installerDir "install-state.json"
$pythonInstaller = Join-Path $AssetsDir "python-installer.exe"
$postgresInstaller = Join-Path $AssetsDir "postgresql-installer.exe"
$wheelhouse = Join-Path $AssetsDir "wheelhouse"
$nssmSource = Join-Path $AssetsDir "nssm.exe"
$nssm = Join-Path $runtimeRoot "nssm.exe"
$serviceName = "NikaCRM-Web"
$postgresServiceName = "NikaCRM-PostgreSQL"
$progressFile = Join-Path $ProgressDir "setup-progress.txt"
$progressDoneFile = Join-Path $ProgressDir "setup-progress.done"
$progressPidFile = Join-Path $ProgressDir "setup-progress.pid"

trap {
    try {
        Write-SetupError ($_ | Out-String)
        $_ | Out-File -LiteralPath $bootstrapLog -Append -Encoding UTF8
        [System.IO.File]::WriteAllText($progressDoneFile, "1", [System.Text.Encoding]::Default)
    }
    catch {
    }
    break
}

[System.IO.File]::WriteAllText($progressPidFile, "$PID", [System.Text.Encoding]::Default)
[System.IO.File]::WriteAllText(
    $progressFile,
    "5`r`nЗапуск настройки`r`nСкрипт стартовал. Дальше: права на папку данных, Python, PostgreSQL.",
    [System.Text.Encoding]::Default
)

New-Item -ItemType Directory -Force -Path $runtimeRoot, $logsDir, $installerDir, $pgData | Out-Null
[System.IO.File]::WriteAllText(
    $progressFile,
    "6`r`nПрава на папку данных`r`nОграничиваем доступ к %ProgramData%\NikaCRM.",
    [System.Text.Encoding]::Default
)

# Inno's Permissions parameter only adds ACEs, so the inherited "Users: read" from
# C:\ProgramData keeps .env (SECRET_KEY, DATABASE_URL) and the setup log readable by
# every local account. Drop inheritance before anything is written. Explicit ACEs that
# PostgreSQL sets on its data directory later are not affected.
& icacls.exe $DataDir /inheritance:r /grant:r "*S-1-5-18:(OI)(CI)(F)" "*S-1-5-32-544:(OI)(CI)(F)" | Out-Null
foreach ($legacyPath in @($logsDir, $installerDir, $envFile)) {
    if (Test-Path -LiteralPath $legacyPath) {
        & icacls.exe $legacyPath /remove:g "*S-1-5-32-545" | Out-Null
    }
}

try {
    Start-Transcript -LiteralPath $bootstrapLog -Append | Out-Null
}
catch {
    Write-SetupError ("WARN: Start-Transcript failed: {0}" -f $_.Exception.Message)
}

$appVersion = "0.0.0"
$versionPath = Join-Path $appRoot "VERSION"
if (Test-Path -LiteralPath $versionPath) {
    $appVersion = ([string](Get-Content -LiteralPath $versionPath -TotalCount 1)).Trim()
}
Write-Host ("[Nika CRM Setup] Bootstrap version {0}" -f $appVersion)

Remove-Item -LiteralPath $progressDoneFile -Force -ErrorAction SilentlyContinue

function Write-Step([string] $Message) {
    Write-Host ("[{0}] {1}" -f (Get-Date -Format "HH:mm:ss"), $Message)
}

function Write-InstallerFile {
    param(
        [Parameter(Mandatory = $true)][string] $Path,
        [Parameter(Mandatory = $true)][string] $Content
    )
    $bytes = [System.Text.Encoding]::Default.GetBytes($Content)
    for ($i = 0; $i -lt 25; $i++) {
        try {
            $fs = New-Object System.IO.FileStream(
                $Path,
                [System.IO.FileMode]::Create,
                [System.IO.FileAccess]::Write,
                [System.IO.FileShare]::ReadWrite
            )
            try {
                $fs.Write($bytes, 0, $bytes.Length)
                $fs.Flush()
            }
            finally {
                $fs.Dispose()
            }
            return
        }
        catch {
            Start-Sleep -Milliseconds 80
        }
    }
    try {
        Set-Content -LiteralPath $Path -Value $Content -Encoding Default -Force -ErrorAction Stop
    }
    catch {
        Write-Host ("WARN: could not write {0}: {1}" -f $Path, $_.Exception.Message)
    }
}

function Set-SetupProgress {
    param(
        [Parameter(Mandatory = $true)]
        [int] $Percent,
        [Parameter(Mandatory = $true)]
        [string] $Title,
        [string] $Hint = ""
    )
    if ($Percent -lt 0) { $Percent = 0 }
    if ($Percent -gt 100) { $Percent = 100 }
    $text = "{0}`r`n{1}`r`n{2}" -f $Percent, $Title, $Hint
    Write-InstallerFile -Path $progressFile -Content $text
    Write-Step $Title
}

function Complete-SetupProgress {
    param(
        [Parameter(Mandatory = $true)][int] $ExitCode,
        [string] $ErrorHint = ""
    )
    # Inno waits on this file. Write it before any other I/O so a later hang
    # (LAN IP lookup, transcript, progress file lock) cannot freeze the wizard.
    Write-InstallerFile -Path $progressDoneFile -Content ([string]$ExitCode)
    if ($ExitCode -eq 0) {
        Set-SetupProgress 100 "Установка завершена" "Можно открывать Nika CRM."
    }
    elseif ($ErrorHint) {
        Set-SetupProgress 0 "Ошибка настройки" $ErrorHint
    }
}

function Test-LocalHttpOk {
    param(
        [Parameter(Mandatory = $true)][string] $Url,
        [int] $TimeoutMs = 2500
    )
    $uri = [Uri]$Url
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $async = $client.BeginConnect($uri.Host, $uri.Port, $null, $null)
        if (-not $async.AsyncWaitHandle.WaitOne($TimeoutMs, $false)) {
            return $false
        }
        $client.EndConnect($async) | Out-Null
    }
    catch {
        return $false
    }
    finally {
        $client.Close()
    }

    $request = [System.Net.HttpWebRequest]::Create($Url)
    $request.Method = "GET"
    $request.Timeout = $TimeoutMs
    $request.ReadWriteTimeout = $TimeoutMs
    $request.AllowAutoRedirect = $true
    $request.KeepAlive = $false
    $request.UserAgent = "NikaCRM-Setup"
    $request.Proxy = [System.Net.GlobalProxySelection]::GetEmptyWebProxy()
    try {
        $response = $request.GetResponse()
        try {
            $code = [int]$response.StatusCode
            return ($code -ge 200 -and $code -lt 400)
        }
        finally {
            $response.Close()
        }
    }
    catch [System.Net.WebException] {
        $webResponse = $_.Exception.Response
        if ($webResponse) {
            try {
                $code = [int]$webResponse.StatusCode
                return ($code -ge 200 -and $code -lt 500)
            }
            finally {
                $webResponse.Close()
            }
        }
        return $false
    }
    catch {
        return $false
    }
}

function Invoke-Native {
    param(
        [Parameter(Mandatory = $true)]
        [string] $FilePath,
        [string[]] $Arguments = @(),
        [int[]] $SuccessCodes = @(0),
        [string[]] $MaskValues = @(),
        [switch] $CaptureOutput
    )
    # Setup transcript lands in ProgramData; never echo generated passwords there.
    $printable = $Arguments -join " "
    foreach ($secret in $MaskValues) {
        if ($secret) { $printable = $printable.Replace($secret, "***") }
    }
    Write-Host ("RUN: {0} {1}" -f $FilePath, (Protect-Secrets $printable))
    $outFile = $null
    $errFile = $null
    try {
        if ($CaptureOutput) {
            # Keep native stdout/stderr in Windows\Temp: ProgramData logs vanish when
            # Inno rolls back a failed install, and a hidden window has no console.
            $stamp = Get-Date -Format "HHmmssfff"
            $outFile = Join-Path $ProgressDir "native-$stamp.out.log"
            $errFile = Join-Path $ProgressDir "native-$stamp.err.log"
            $process = Start-Process -FilePath $FilePath -ArgumentList $Arguments -Wait -PassThru -NoNewWindow `
                -RedirectStandardOutput $outFile -RedirectStandardError $errFile
            foreach ($streamFile in @($outFile, $errFile)) {
                if (Test-Path -LiteralPath $streamFile) {
                    # PYTHONIOENCODING=utf-8 is set before pip and the migrations run.
                    $streamText = Read-TextFileOrEmpty -Path $streamFile -Encoding "UTF8"
                    if (-not [string]::IsNullOrWhiteSpace($streamText)) {
                        Write-Host (Protect-Secrets $streamText.TrimEnd())
                    }
                }
            }
        }
        else {
            $process = Start-Process -FilePath $FilePath -ArgumentList $Arguments -Wait -PassThru -NoNewWindow
        }
        if ($process.ExitCode -notin $SuccessCodes) {
            $tail = New-Object System.Collections.Generic.List[string]
            $tail.Add("Command failed with exit code $($process.ExitCode): $FilePath") | Out-Null
            $tail.Add("RUN: $FilePath $printable") | Out-Null
            foreach ($streamFile in @($outFile, $errFile)) {
                if ($streamFile -and (Test-Path -LiteralPath $streamFile)) {
                    $tail.Add("---- $(Split-Path -Leaf $streamFile) ----") | Out-Null
                    Get-Content -LiteralPath $streamFile -Tail 80 -Encoding UTF8 -ErrorAction SilentlyContinue |
                        ForEach-Object { $tail.Add([string] $_) | Out-Null }
                }
            }
            Write-SetupError ($tail -join [Environment]::NewLine)
            throw "Command failed with exit code $($process.ExitCode): $FilePath"
        }
    }
    finally {
        # The raw streams may quote a connection string; the masked copy is
        # already in setup.log and only that folder leaves the machine.
        foreach ($streamFile in @($outFile, $errFile)) {
            if ($streamFile) {
                Remove-Item -LiteralPath $streamFile -Force -ErrorAction SilentlyContinue
            }
        }
    }
}

function Format-NativeArgument([string] $Value) {
    # Start-Process -ArgumentList joins array items with spaces and quotes
    # nothing, so "SELECT 1 FROM x" reached psql as separate arguments.
    if ($Value -eq "") { return '""' }
    if ($Value -notmatch '[\s"]') { return $Value }
    $escaped = $Value -replace '(\\*)"', '$1$1\"'
    $escaped = $escaped -replace '(\\+)$', '$1$1'
    return '"' + $escaped + '"'
}

function Read-TextFileOrEmpty {
    param(
        [Parameter(Mandatory = $true)][string] $Path,
        # Redirected native output is written in the console code page, so a
        # Russian psql error read as ANSI turns into unreadable characters.
        [string] $Encoding = "Oem"
    )
    if (-not (Test-Path -LiteralPath $Path)) { return "" }
    $raw = Get-Content -LiteralPath $Path -Raw -Encoding $Encoding -ErrorAction SilentlyContinue
    if ($null -eq $raw) { return "" }
    return [string] $raw
}

function Invoke-Psql {
    param(
        [Parameter(Mandatory = $true)][string] $Database,
        [string] $SqlText = "",
        [string] $SqlFile = "",
        [string] $Query = "",
        [int[]] $SuccessCodes = @(0),
        [switch] $PassThru,
        [int] $TimeoutMs = 180000
    )
    # Hidden installer windows look like a console to psql, so the default
    # pager (more.com) waits for a key that never comes. -X -P pager=off plus
    # redirected streams keep it non-interactive.
    $stamp = Get-Date -Format "HHmmssfff"
    $tempSql = ""
    # A helper script that cleared PGPASSWORD in this same process left the next
    # call without a password: psql then prompted on the hidden console and the
    # wizard sat at 84% until the timeout. Re-assert it and pass -w so psql
    # never waits for input.
    if ($postgresSuperPassword) {
        $env:PGPASSWORD = $postgresSuperPassword
    }
    $argList = @(
        "-X", "-w", "-P", "pager=off",
        "-h", "127.0.0.1",
        "-p", "$postgresPort",
        "-U", "postgres",
        "-d", $Database
    )
    if ($SqlText) {
        # Multi-line SQL goes through a file: a newline inside argv is fragile,
        # and the role statement carries the generated password.
        $tempSql = Join-Path $installerDir "psql-$stamp.sql"
        $utf8NoBom = New-Object System.Text.UTF8Encoding $false
        [System.IO.File]::WriteAllText($tempSql, $SqlText, $utf8NoBom)
        $argList += @("-v", "ON_ERROR_STOP=1", "-q", "-f", $tempSql)
    }
    elseif ($SqlFile) {
        $argList += @("-v", "ON_ERROR_STOP=1", "-q", "-f", $SqlFile)
    }
    elseif ($Query) {
        $argList += @("-tAc", $Query)
    }
    else {
        throw "Invoke-Psql needs SqlText, SqlFile or Query."
    }

    $argString = ($argList | ForEach-Object { Format-NativeArgument $_ }) -join " "
    Write-Host ("RUN: {0} {1}" -f $psql, (Protect-Secrets $argString))
    $outFile = Join-Path $ProgressDir "psql-$stamp.out.log"
    $errFile = Join-Path $ProgressDir "psql-$stamp.err.log"
    try {
        $process = Start-Process -FilePath $psql -ArgumentList $argString -PassThru -NoNewWindow `
            -RedirectStandardOutput $outFile -RedirectStandardError $errFile
        # Touching Handle caches the process handle; without it ExitCode stays
        # $null after WaitForExit and every call looks like a failure.
        $null = $process.Handle
        if (-not $process.WaitForExit($TimeoutMs)) {
            try { Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue } catch { }
            Write-SetupError "psql timed out after $TimeoutMs ms: $(Protect-Secrets $argString)"
            throw "psql timed out after $TimeoutMs ms"
        }
        $exitCode = -1
        if ($null -ne $process.ExitCode) { $exitCode = [int] $process.ExitCode }
        $stdout = Read-TextFileOrEmpty $outFile
        $stderr = Read-TextFileOrEmpty $errFile
        if (-not [string]::IsNullOrWhiteSpace($stderr)) {
            Write-Host (Protect-Secrets $stderr.TrimEnd())
        }
        if (-not [string]::IsNullOrWhiteSpace($stdout)) {
            Write-Host (Protect-Secrets $stdout.TrimEnd())
        }
        if ($exitCode -notin $SuccessCodes) {
            Write-SetupError ("psql exit {0}`r`n{1}`r`n{2}" -f $exitCode, $stderr, $stdout)
            throw "psql failed with exit code $exitCode"
        }
        if ($PassThru) {
            return [string] $stdout
        }
    }
    finally {
        # These files can echo a failing statement, so they must not survive
        # into the log folder that is copied to the public desktop.
        foreach ($scratch in @($outFile, $errFile, $tempSql)) {
            if ($scratch) {
                Remove-Item -LiteralPath $scratch -Force -ErrorAction SilentlyContinue
            }
        }
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
    # Dns.GetHostAddresses is local and bounded. Get-NetIPAddress talks to CIM
    # and can hang indefinitely inside Windows Sandbox.
    try {
        foreach ($addr in [System.Net.Dns]::GetHostAddresses([System.Net.Dns]::GetHostName())) {
            if ($addr.AddressFamily -ne [System.Net.Sockets.AddressFamily]::InterNetwork) {
                continue
            }
            $ip = $addr.ToString()
            if ($ip -like "127.*" -or $ip -like "169.254.*") {
                continue
            }
            return $ip
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

    # Do not use Firewall CIM cmdlets here: they can hang forever inside
    # Windows Sandbox. netsh is enough.
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

    Set-SetupProgress 5 "Проверка прав и файлов установки" "Окно можно свернуть, но не закрывать. Обычно 5–10 минут."

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
    $script:SecretValues.Add($postgresSuperPassword) | Out-Null
    $script:SecretValues.Add($appDbPassword) | Out-Null

    if (-not (Test-Path -LiteralPath $pythonExe)) {
        Set-SetupProgress 12 "Установка Python 3.12" "Один раз, занимает около минуты."
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

    Set-SetupProgress 25 "Установка библиотек приложения" "Ставятся из локальной папки, интернет не нужен."
    Invoke-Native $pythonExe @(
        "-m", "pip", "install",
        "--disable-pip-version-check",
        "--no-index",
        "--find-links", "`"$wheelhouse`"",
        "-r", "`"$(Join-Path $appRoot 'packaging\windows\requirements-windows.txt')`""
    ) @(0) -CaptureOutput

    if (-not (Test-Path -LiteralPath (Join-Path $pgBin "psql.exe"))) {
        # Binaries are missing, so PostgreSQL has to be installed again. Three
        # leftovers from a previous install make the unattended installer fail,
        # and every one of them ends as "Setup failed with error 1" for the user.

        # 1. A registered service with the same name.
        $staleService = Get-Service -Name $postgresServiceName -ErrorAction SilentlyContinue
        if ($staleService) {
            Write-Step "Removing stale $postgresServiceName service registration"
            & net.exe stop $postgresServiceName /y | Out-Null
            & sc.exe delete $postgresServiceName | Out-Null
            for ($attempt = 0; $attempt -lt 30; $attempt++) {
                if (-not (Get-Service -Name $postgresServiceName -ErrorAction SilentlyContinue)) { break }
                Start-Sleep -Milliseconds 500
            }
        }

        # 2. A non-empty data directory: the installer refuses to initdb into it.
        if (Test-Path -LiteralPath (Join-Path $pgData "PG_VERSION")) {
            $legacyCluster = "{0}-legacy-{1}" -f $pgData, (Get-Date -Format "yyyyMMdd-HHmmss")
            Write-Step "Moving leftover PostgreSQL cluster aside: $legacyCluster"
            Move-Item -LiteralPath $pgData -Destination $legacyCluster -Force
            New-Item -ItemType Directory -Force -Path $pgData | Out-Null
        }

        # 3. A local service account kept from the previous install: the
        # installer validates the password we pass against the existing account.
        $serviceAccount = $null
        try {
            $serviceAccount = Get-LocalUser -Name "postgres" -ErrorAction SilentlyContinue
        }
        catch {
            Write-Step "Skipping leftover postgres account check ($($_.Exception.Message))"
        }
        if ($serviceAccount) {
            $otherUsers = @(
                Get-CimInstance Win32_Service -ErrorAction SilentlyContinue |
                    Where-Object { $_.StartName -and $_.StartName -match '(^|\\)postgres$' -and $_.Name -ne $postgresServiceName }
            )
            if ($otherUsers.Count -gt 0) {
                Write-Step "Local 'postgres' account is used by another service; leaving its password untouched"
            }
            else {
                Write-Step "Resetting password of the leftover local 'postgres' service account"
                & net.exe user postgres $postgresSuperPassword | Out-Null
            }
        }

        Set-SetupProgress 38 "Установка PostgreSQL 18" "Самый долгий шаг, обычно 1–3 минуты. Шкала может подождать — это нормально."
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
        ) @(0) -MaskValues @($postgresSuperPassword)
    }

    $psql = Join-Path $pgBin "psql.exe"
    if (-not (Test-Path -LiteralPath $psql)) {
        throw "PostgreSQL installation did not create $psql"
    }
    $env:PATH = "$pgBin;$env:PATH"
    $env:PGPASSWORD = $postgresSuperPassword
    $env:TERM = "dumb"
    Remove-Item Env:PAGER -ErrorAction SilentlyContinue
    Remove-Item Env:PSQL_PAGER -ErrorAction SilentlyContinue

    Set-SetupProgress 55 "Ожидание запуска базы данных" "PostgreSQL поднимается как служба Windows."
    & sc.exe start $postgresServiceName | Out-Null
    $ready = $false
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        Set-SetupProgress 55 "Ожидание запуска базы данных" (
            "Попытка {0} из 60. Служба PostgreSQL поднимается." -f ($attempt + 1)
        )
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

    Set-SetupProgress 62 "Создание роли и базы данных" "Данные прежней установки не затираются."
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
    Invoke-Psql -Database "postgres" -SqlText $roleSql

    # SELECT EXISTS always emits t/f. This is intentionally used instead of a
    # query that returns zero rows: Windows PowerShell 5.1 represents empty
    # native stdout as $null and calling Trim() on it aborts a clean install.
    $dbExistsOutput = Invoke-Psql -Database "postgres" -PassThru `
        -Query "SELECT EXISTS (SELECT 1 FROM pg_database WHERE datname='nikacrm')"
    $dbExists = ([string]$dbExistsOutput).Trim()
    if ($dbExists -ne "t") {
        & (Join-Path $pgBin "createdb.exe") -h 127.0.0.1 -p $postgresPort -U postgres -w -O nikacrm nikacrm
        if ($LASTEXITCODE -ne 0) { throw "Failed to create PostgreSQL database." }
    }

    $usersTableOutput = Invoke-Psql -Database "nikacrm" -PassThru `
        -Query "SELECT to_regclass('public.users') IS NOT NULL"
    $usersTable = ([string]$usersTableOutput).Trim()
    if ($usersTable -ne "t") {
        # Uninstall saves a pg_dump next to ProgramData and does not delete it, so a
        # reinstall must restore the real data instead of the demo database.
        $restoreDump = Get-ChildItem -LiteralPath $backupDir -Filter "nikacrm-*.sql" -File -ErrorAction SilentlyContinue |
            Sort-Object LastWriteTime -Descending |
            Select-Object -First 1
        if ($restoreDump) {
            Set-SetupProgress 70 "Восстановление базы из резервной копии" "Берётся свежий дамп из NikaCRM-backup."
            Invoke-Psql -Database "nikacrm" -SqlFile $restoreDump.FullName -TimeoutMs 600000
        }
        else {
            Set-SetupProgress 70 "Загрузка демо-базы" "Первая установка: справочники и учебные заявки."
            $dump = Join-Path $appRoot "database\bootstrap\nikacrm_public_sanitized.sql"
            Invoke-Psql -Database "nikacrm" -SqlFile $dump -TimeoutMs 600000
        }
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
    Invoke-Psql -Database "nikacrm" -SqlText $grantSql

    Set-SetupProgress 78 "Запись настроек и правило брандмауэра" "База и пароли остаются в ProgramData."
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
        "NIKACRM_DATA_DIR" = $DataDir
    }
    $setIfMissing = @{
        "SECRET_KEY" = (New-SafePassword "NikaSecretA1")
        "RATELIMIT_STORAGE_URI" = "memory://"
        "TIMEZONE_OFFSET" = "3"
        "PUBLIC_LANDING" = "0"
        "DEMO_LOGIN_BANNER" = "0"
        "UPDATE_CHECK_ENABLED" = "1"
        "UPDATE_MANIFEST_URL" = "https://service.nika-crm.ru/api/windows-setup/latest"
        "UPDATE_CHECK_TTL_HOURS" = "24"
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

    Set-SetupProgress 84 "Права базы и снимок перед миграциями" "На всякий случай сохраняется копия данных."
    & (Join-Path $appRoot "scripts\Grant-LocalPostgresAppPrivileges.ps1") `
        -PostgresSuperUserPassword $postgresSuperPassword `
        -HostDb "127.0.0.1" `
        -Port $postgresPort `
        -SuperUser "postgres" `
        -EnvFile $envFile `
        -PsqlPath $psql

    # Both the demo dump and a restored pg_dump are loaded by the postgres
    # superuser, so every table belongs to postgres. Migrations run as nikacrm
    # and ALTER TABLE requires ownership, not just privileges: without this an
    # upgrade over an older database fails on the first pending migration.
    Write-Step "Normalizing object ownership to the nikacrm role"
    $ownerSql = @"
DO `$do`$
DECLARE rel record;
BEGIN
    FOR rel IN
        SELECT c.relkind, n.nspname, c.relname
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public'
          AND c.relkind IN ('r', 'p', 'S', 'v', 'm')
          AND pg_get_userbyid(c.relowner) <> 'nikacrm'
          -- A serial or identity sequence cannot be reassigned on its own
          -- ("Sequence is linked to table"); it follows its table's owner.
          AND NOT (
              c.relkind = 'S'
              AND EXISTS (
                  SELECT 1
                  FROM pg_depend d
                  WHERE d.classid = 'pg_class'::regclass
                    AND d.objid = c.oid
                    AND d.deptype IN ('a', 'i')
              )
          )
        ORDER BY CASE WHEN c.relkind IN ('r', 'p') THEN 0 ELSE 1 END
    LOOP
        EXECUTE format(
            'ALTER %s %I.%I OWNER TO nikacrm',
            CASE rel.relkind
                WHEN 'S' THEN 'SEQUENCE'
                WHEN 'v' THEN 'VIEW'
                WHEN 'm' THEN 'MATERIALIZED VIEW'
                ELSE 'TABLE'
            END,
            rel.nspname, rel.relname
        );
    END LOOP;
END
`$do`$;
"@
    Invoke-Psql -Database "nikacrm" -SqlText $ownerSql

    # Rollback point for an upgrade, and it also spares run_migrations.py its own
    # pg_dump into Program Files.
    Write-Step "Backing up the database before migrations"
    $env:SKIP_PRE_MIGRATION_BACKUP = "0"
    & powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass `
        -File (Join-Path $appRoot "packaging\windows\backup-database.ps1") `
        -AppDir $AppDir -DataDir $DataDir -BackupDir $backupDir -Quiet
    if ($LASTEXITCODE -eq 0) {
        $env:SKIP_PRE_MIGRATION_BACKUP = "1"
    }
    else {
        Write-Step "WARNING: pre-migration backup failed, run_migrations.py will make its own"
    }

    Set-SetupProgress 90 "Применение обновлений базы" "Добавляются новые таблицы и поля, заявки не удаляются."
    Set-Location -LiteralPath $appRoot
    Invoke-Native $pythonExe @("scripts\run_migrations.py") @(0) -CaptureOutput

    Set-SetupProgress 94 "Регистрация службы Nika CRM" "Служба запускается вместе с Windows."
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
    $nssmStart = Start-Process -FilePath $nssm -ArgumentList @("start", $serviceName) -PassThru -NoNewWindow
    if (-not $nssmStart.WaitForExit(180000)) {
        Write-Step "NSSM start is still running after 3 minutes; continuing with HTTP check."
    }
    elseif ($nssmStart.ExitCode -notin @(0, 3)) {
        Write-Step ("NSSM start exit code {0}; continuing with HTTP check." -f $nssmStart.ExitCode)
    }

    Set-SetupProgress 97 "Проверка, что сайт открывается" "Ждём ответ http://127.0.0.1:5000/login"
    $healthy = $false
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        Set-SetupProgress 97 "Проверка, что сайт открывается" (
            "Попытка {0} из 60. Ждём http://127.0.0.1:5000/login" -f ($attempt + 1)
        )
        if (Test-LocalHttpOk -Url "http://127.0.0.1:5000/login" -TimeoutMs 2500) {
            $healthy = $true
            break
        }
        Start-Sleep -Seconds 1
    }
    if (-not $healthy) {
        throw "Nika CRM service did not pass the HTTP health check."
    }

    $nowIso = (Get-Date).ToString("o")
    $fromVersion = $null
    if ($state.PSObject.Properties.Name -contains "app_version") {
        $fromVersion = [string] $state.app_version
    }
    $history = @()
    if ($state.PSObject.Properties.Name -contains "version_history" -and $state.version_history) {
        $history = @($state.version_history)
    }
    $history += [ordered]@{ from = $fromVersion; to = $appVersion; at = $nowIso }
    $state | Add-Member -NotePropertyName app_version -NotePropertyValue $appVersion -Force
    $state | Add-Member -NotePropertyName updated_at -NotePropertyValue $nowIso -Force
    $state | Add-Member -NotePropertyName version_history -NotePropertyValue @($history) -Force
    $state | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $stateFile -Encoding UTF8

    Write-Step "Installation completed successfully"
    Complete-SetupProgress 0
    try {
        Copy-Item -LiteralPath $bootstrapLog -Destination (Join-Path $logsDir "setup.log") -Force
    }
    catch {
    }
    try {
        $lanIp = Get-PrimaryLanIPv4
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
        Write-Host ("WARN: could not detect LAN URL: {0}" -f $_.Exception.Message)
    }
}
catch {
    Write-SetupError ("Automatic setup failed: {0}`r`n{1}" -f $_.Exception.Message, $_.ScriptStackTrace)
    Write-Error ("Automatic setup failed: {0}`n{1}" -f $_.Exception.Message, $_.ScriptStackTrace)
    if (-not (Test-Path -LiteralPath $progressDoneFile)) {
        Complete-SetupProgress 1 $_.Exception.Message
    }
    throw
}
finally {
    if (-not (Test-Path -LiteralPath $progressDoneFile)) {
        Complete-SetupProgress 1 "Установка прервалась без кода возврата."
    }
    Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
    try {
        Stop-Transcript | Out-Null
    }
    catch {
        # Transcript stop must not hide a completed install from the wizard.
    }
}
