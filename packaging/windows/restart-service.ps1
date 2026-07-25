$ErrorActionPreference = "Stop"
$serviceName = "NikaCRM-Web"

if (-not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator
)) {
    Start-Process powershell.exe -Verb RunAs -ArgumentList @(
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", "`"$PSCommandPath`""
    )
    exit
}

Restart-Service -Name $serviceName -Force
Start-Sleep -Seconds 2
Start-Process "http://127.0.0.1:5000"
