[CmdletBinding()]
param(
    [string] $DataDir = "$env:ProgramData\NikaCRM",
    [string] $ServiceName = "NikaCRM-Web",
    [int] $Port = 5000
)

$ErrorActionPreference = "Stop"

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Run this script as Administrator."
}

$envFile = Join-Path $DataDir ".env"
if (-not (Test-Path -LiteralPath $envFile)) {
    throw "Environment file not found: $envFile"
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
    catch { }
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
            $trimmed = $line.Trim()
            if (-not $trimmed -or $trimmed.StartsWith("#") -or -not $trimmed.Contains("=")) {
                continue
            }
            $name, $value = $trimmed.Split("=", 2)
            $key = $name.Trim()
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
    $lines | Set-Content -LiteralPath $Path -Encoding UTF8
}

$computerName = ($env:COMPUTERNAME -as [string])
if (-not $computerName) { $computerName = "localhost" }
$trustedHosts = "localhost,127.0.0.1,@private,$computerName,$computerName.local"

Write-Host "Updating $envFile for LAN access..."
Merge-DotEnvFile -Path $envFile -AlwaysSet @{
    "APP_HOST" = "0.0.0.0"
    "APP_PORT" = "$Port"
    "TRUSTED_HOSTS" = $trustedHosts
    "SOCKETIO_CORS_ALLOWED_ORIGINS" = "http://localhost:$Port,http://127.0.0.1:$Port,@private"
    "USE_HTTPS" = "false"
} -SetIfMissing @{}

$ruleName = "Nika CRM (HTTP $Port)"
$existingRule = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
if (-not $existingRule) {
    Write-Host "Creating firewall rule: $ruleName (Private, Domain)"
    New-NetFirewallRule `
        -DisplayName $ruleName `
        -Direction Inbound `
        -Action Allow `
        -Protocol TCP `
        -LocalPort $Port `
        -Profile Private,Domain | Out-Null
}
else {
    Write-Host "Firewall rule already present: $ruleName"
}

$service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if (-not $service) {
    throw "Windows service not found: $ServiceName"
}
Write-Host "Restarting service $ServiceName..."
Restart-Service -Name $ServiceName -Force
Start-Sleep -Seconds 2

$lanIp = Get-PrimaryLanIPv4
Write-Host ""
Write-Host "LAN access enabled."
Write-Host "Local URL:  http://127.0.0.1:$Port"
if ($lanIp) {
    Write-Host "LAN URL:    http://${lanIp}:$Port"
}
else {
    Write-Host "LAN URL:    http://<this-pc-ip>:$Port"
}
Write-Host "Change demo account passwords if other devices on the network can reach this PC."
