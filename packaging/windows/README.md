# Offline Windows installer

`NikaCRM.iss` builds a single x64 installer that works without internet access.
It contains Python 3.12, PostgreSQL 18, NSSM, the sanitized demo database and
all Windows Python wheels required by the application.

**Published download links:**

- [NikaCRM-Offline-Setup-1.0.4-x64.exe (GitHub)](https://github.com/nika-sc/Nika-Service-CRM/releases/download/windows-setup-1.0.4/NikaCRM-Offline-Setup-1.0.4-x64.exe)
- [Release page](https://github.com/nika-sc/Nika-Service-CRM/releases/tag/windows-setup-1.0.4)
- [Demo mirror](https://demo.nika-sc.ru/downloads/NikaCRM-Offline-Setup-1.0.4-x64.exe)

## User installation

1. Download `NikaCRM-Offline-Setup-1.0.4-x64.exe` (links above).
2. Run it as an administrator and complete the short setup wizard.
3. Open **Nika CRM - Открыть** on the desktop.
4. Sign in with a demo account from `database/bootstrap/README.md` and change
   the password immediately if the computer is accessible to other people.

No separate Python or PostgreSQL installation is needed. The installer:

- installs the application under `%ProgramFiles%\NikaCRM`;
- keeps the database, environment and logs under `%ProgramData%\NikaCRM`;
- chooses PostgreSQL port `5432`, `55432` or `55433`, whichever is free;
- imports `nikacrm_public_sanitized.sql` and applies pending migrations;
- registers auto-start services `NikaCRM-PostgreSQL` and `NikaCRM-Web`;
- creates Open, Restart service and Logs shortcuts.

Uninstall removes the services, application runtime and shortcuts. Database
files remain in `%ProgramData%\NikaCRM` to prevent accidental data loss.

## Build

Requirements for the build computer:

- Windows 10/11 x64;
- Python 3.12 available as `python`;
- Inno Setup 6 in its default installation directory;
- internet access only while creating/updating the offline bundle.

From an ordinary PowerShell window in the repository root:

```powershell
.\scripts\windows\build-offline-bundle.ps1
```

The script downloads version-pinned official installers, verifies SHA256,
resolves a CPython 3.12 Windows wheelhouse, writes an integrity manifest and
builds:

`packaging\windows\output\NikaCRM-Offline-Setup-1.0.4-x64.exe`

Downloaded assets and build output are deliberately excluded from Git. To
rebuild using already downloaded files:

```powershell
.\scripts\windows\build-offline-bundle.ps1 -SkipDownload
```

Verify only:

```powershell
.\scripts\windows\verify-bundle.ps1
```

Run the installer in a clean Windows Sandbox and collect JSON/log results:

```powershell
.\scripts\windows\Start-WindowsSandboxSmoke.ps1
```

## Diagnostics

- Setup log: `%ProgramData%\NikaCRM\logs\setup.log`
- Web stdout: `%ProgramData%\NikaCRM\logs\web-stdout.log`
- Web stderr: `%ProgramData%\NikaCRM\logs\web-stderr.log`
- Inno Setup log: pass `/LOG="C:\path\setup.log"` to the installer
- Service status: `Get-Service NikaCRM-Web,NikaCRM-PostgreSQL`

### Port is occupied

The database installer automatically tries `5432`, `55432` and `55433`.
The web interface requires `127.0.0.1:5000`; stop the program using that port
before installation:

```powershell
Get-NetTCPConnection -LocalPort 5000 | Select-Object OwningProcess
```

### PostgreSQL does not start

Check `Get-Service NikaCRM-PostgreSQL`, the setup log, and PostgreSQL logs in
`%ProgramData%\NikaCRM\PostgreSQL\data\log`. Do not delete the data directory
before making a backup.

### Web service does not start

Check both web logs and restart:

```powershell
Restart-Service NikaCRM-Web
Invoke-WebRequest http://127.0.0.1:5000/login -UseBasicParsing
```

### Windows warns about an unknown publisher

Local development builds are not Authenticode-signed. Public releases should
be signed with the project's code-signing certificate before distribution.
