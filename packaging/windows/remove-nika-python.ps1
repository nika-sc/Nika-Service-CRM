# Remove only the Python registration that belongs to Nika CRM.
# A Python the customer installed themselves stays on disk, in PATH and in
# "Programs and Features". The official python.org installer cannot tell those
# two apart (same 3.12 product), so this script keys off the install path.

function Test-NikaOwnedPath {
    param(
        [string] $Candidate,
        [Parameter(Mandatory = $true)]
        [string] $AppDir
    )
    if ([string]::IsNullOrWhiteSpace($Candidate) -or [string]::IsNullOrWhiteSpace($AppDir)) {
        return $false
    }
    # Commands look like: "C:\...\python.exe" "%1" or DisplayIcon "C:\...\python.exe,0".
    $match = [regex]::Match($Candidate, '[A-Za-z]:\\[^",]+')
    if (-not $match.Success) {
        return $false
    }
    $raw = $match.Value.Trim().TrimEnd('\')
    try {
        $full = [System.IO.Path]::GetFullPath($raw)
        $root = [System.IO.Path]::GetFullPath($AppDir.TrimEnd('\'))
    }
    catch {
        return $false
    }
    $prefix = $root.TrimEnd('\') + '\'
    return $full.Equals($root, [System.StringComparison]::OrdinalIgnoreCase) -or
        $full.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)
}

function Write-NikaPythonLog {
    param([string] $Message)
    if ($script:NikaPythonLog) {
        & $script:NikaPythonLog $Message
    }
    else {
        Write-Host $Message
    }
}

function Invoke-QuietCommand {
    param([string] $Command)
    if ([string]::IsNullOrWhiteSpace($Command)) { return }
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = Join-Path $env:SystemRoot "System32\cmd.exe"
    $psi.Arguments = "/d /c $Command"
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $psi
    [void] $process.Start()
    if (-not $process.WaitForExit(180000)) {
        try { $process.Kill() } catch { }
        Write-NikaPythonLog "Quiet uninstall timed out and was stopped."
    }
}

function Remove-NikaPathEntries {
    param([string] $AppDir)
    foreach ($scope in @("Machine", "User")) {
        try {
            $current = [Environment]::GetEnvironmentVariable("Path", $scope)
        }
        catch {
            continue
        }
        if ([string]::IsNullOrEmpty($current)) { continue }
        $kept = New-Object System.Collections.Generic.List[string]
        $changed = $false
        foreach ($part in $current.Split(';')) {
            if ([string]::IsNullOrWhiteSpace($part)) { continue }
            if (Test-NikaOwnedPath -Candidate $part -AppDir $AppDir) {
                $changed = $true
                Write-NikaPythonLog "Removing Nika CRM from $scope PATH: $($part.Trim())"
                continue
            }
            [void] $kept.Add($part.Trim())
        }
        if ($changed) {
            [Environment]::SetEnvironmentVariable("Path", ($kept -join ";"), $scope)
        }
    }
}

function Remove-NikaBundledPython {
    param(
        [Parameter(Mandatory = $true)]
        [string] $AppDir,
        [scriptblock] $Log
    )
    $script:NikaPythonLog = $Log
    try {
        $pythonRoots = @(
            "HKLM:\SOFTWARE\Python\PythonCore",
            "HKLM:\SOFTWARE\WOW6432Node\Python\PythonCore",
            "HKCU:\SOFTWARE\Python\PythonCore"
        )
        foreach ($root in $pythonRoots) {
            if (-not (Test-Path -LiteralPath $root)) { continue }
            foreach ($versionKey in @(Get-ChildItem -LiteralPath $root -ErrorAction SilentlyContinue)) {
                $installKey = Join-Path $versionKey.PSPath "InstallPath"
                $item = Get-Item -LiteralPath $installKey -ErrorAction SilentlyContinue
                if (-not $item) { continue }
                $location = [string] $item.GetValue("")
                $executable = [string] $item.GetValue("ExecutablePath")
                $owned = (Test-NikaOwnedPath -Candidate $location -AppDir $AppDir) -or
                    (Test-NikaOwnedPath -Candidate $executable -AppDir $AppDir)
                if ($owned) {
                    Write-NikaPythonLog "Removing Nika CRM Python registration $($versionKey.PSChildName): $location"
                    Remove-Item -LiteralPath $versionKey.PSPath -Recurse -Force -ErrorAction SilentlyContinue
                }
                elseif (-not [string]::IsNullOrWhiteSpace($location)) {
                    Write-NikaPythonLog "Leaving separately installed Python $($versionKey.PSChildName): $location"
                }
            }
        }

        $uninstallRoots = @(
            "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
            "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
            "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
        )
        foreach ($root in $uninstallRoots) {
            if (-not (Test-Path -LiteralPath $root)) { continue }
            foreach ($entry in @(Get-ChildItem -LiteralPath $root -ErrorAction SilentlyContinue)) {
                $item = Get-Item -LiteralPath $entry.PSPath -ErrorAction SilentlyContinue
                if (-not $item) { continue }
                $displayName = [string] $item.GetValue("DisplayName")
                if ($displayName -notmatch "Python") { continue }
                $location = [string] $item.GetValue("InstallLocation")
                $icon = [string] $item.GetValue("DisplayIcon")
                $owned = (Test-NikaOwnedPath -Candidate $location -AppDir $AppDir) -or
                    (Test-NikaOwnedPath -Candidate $icon -AppDir $AppDir)
                if (-not $owned) { continue }
                Write-NikaPythonLog "Uninstalling Nika CRM entry from Programs and Features: $displayName"
                $quiet = [string] $item.GetValue("QuietUninstallString")
                if ([string]::IsNullOrWhiteSpace($quiet)) {
                    $quiet = [string] $item.GetValue("UninstallString")
                }
                if ($quiet -match "msiexec" -and $quiet -notmatch "/qn") {
                    $quiet = "$quiet /qn /norestart"
                }
                elseif ($quiet -match "uninstall" -and $quiet -notmatch "/quiet") {
                    $quiet = "$quiet /quiet"
                }
                try {
                    Invoke-QuietCommand -Command $quiet
                }
                catch {
                    Write-NikaPythonLog "Python uninstall command failed: $($_.Exception.Message)"
                }
                Remove-Item -LiteralPath $entry.PSPath -Recurse -Force -ErrorAction SilentlyContinue
            }
        }

        $classCommands = @(
            "HKLM:\SOFTWARE\Classes\Python.File\shell\open\command",
            "HKLM:\SOFTWARE\Classes\Python.NoConFile\shell\open\command",
            "HKLM:\SOFTWARE\Classes\Python.CompiledFile\shell\open\command",
            "HKCU:\SOFTWARE\Classes\Python.File\shell\open\command",
            "HKCU:\SOFTWARE\Classes\Python.NoConFile\shell\open\command",
            "HKLM:\SOFTWARE\Classes\.py\shell\open\command",
            "HKCU:\SOFTWARE\Classes\.py\shell\open\command",
            "HKLM:\SOFTWARE\Classes\.pyw\shell\open\command",
            "HKCU:\SOFTWARE\Classes\.pyw\shell\open\command"
        )
        foreach ($commandKey in $classCommands) {
            $item = Get-Item -LiteralPath $commandKey -ErrorAction SilentlyContinue
            if (-not $item) { continue }
            $command = [string] $item.GetValue("")
            if (Test-NikaOwnedPath -Candidate $command -AppDir $AppDir) {
                Write-NikaPythonLog "Removing file association that points at Nika CRM Python."
                Remove-Item -LiteralPath $commandKey -Recurse -Force -ErrorAction SilentlyContinue
            }
        }

        foreach ($hive in @("HKLM:", "HKCU:")) {
            $appPaths = "$hive\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"
            foreach ($name in @("python.exe", "pythonw.exe", "python3.exe")) {
                $key = Join-Path $appPaths $name
                $item = Get-Item -LiteralPath $key -ErrorAction SilentlyContinue
                if (-not $item) { continue }
                $exe = [string] $item.GetValue("")
                $dir = [string] $item.GetValue("Path")
                if ((Test-NikaOwnedPath -Candidate $exe -AppDir $AppDir) -or (Test-NikaOwnedPath -Candidate $dir -AppDir $AppDir)) {
                    Write-NikaPythonLog "Removing App Paths entry that points at Nika CRM: $name"
                    Remove-Item -LiteralPath $key -Recurse -Force -ErrorAction SilentlyContinue
                }
            }
        }

        Remove-NikaPathEntries -AppDir $AppDir
    }
    catch {
        Write-NikaPythonLog "Could not fully clear Nika CRM Python registration: $($_.Exception.Message)"
    }
    finally {
        $script:NikaPythonLog = $null
    }
}
