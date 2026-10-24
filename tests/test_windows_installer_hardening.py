"""Windows offline installer: secrets stay out of logs and of the public bundle."""
from pathlib import Path

ISS = Path("packaging/windows/NikaCRM.iss")
BOOTSTRAP = Path("packaging/windows/bootstrap.ps1")
CLEANUP = Path("packaging/windows/uninstall-cleanup.ps1")
BACKUP = Path("packaging/windows/backup-database.ps1")
FULL_UNINSTALL = Path("packaging/windows/uninstall-full.ps1")


def test_packed_powershell_scripts_have_utf8_bom():
    # Windows PowerShell 5.1 -File without a BOM decodes as the ANSI code page.
    # UTF-8 bytes of Cyrillic Д (D0 94) become a smart quote and the script
    # never starts — ResultCode=1, no setup.log. Sandbox is typically CP1252.
    paths = list(Path("packaging/windows").glob("*.ps1"))
    paths.append(Path("scripts/Grant-LocalPostgresAppPrivileges.ps1"))
    missing = []
    for path in paths:
        text = path.read_text(encoding="utf-8-sig")
        if not any("\u0400" <= ch <= "\u04FF" for ch in text):
            continue
        if not path.read_bytes().startswith(b"\xef\xbb\xbf"):
            missing.append(str(path))
    assert missing == []


def test_installer_does_not_pack_private_docs():
    src = ISS.read_text(encoding="utf-8-sig")
    docs_line = next(line for line in src.splitlines() if '\\docs\\*"' in line)
    assert "private,private\\*,*\\private\\*" in docs_line
    assert "SERVICE_NIKA_CRM_HOST.md" in docs_line


def test_program_data_is_not_readable_by_local_users():
    iss = ISS.read_text(encoding="utf-8-sig")
    assert "users-readexec" not in iss
    bootstrap = BOOTSTRAP.read_text(encoding="utf-8-sig")
    assert "/inheritance:r" in bootstrap
    assert "*S-1-5-32-545" in bootstrap


def test_setup_log_masks_generated_passwords():
    bootstrap = BOOTSTRAP.read_text(encoding="utf-8-sig")
    assert "$MaskValues" in bootstrap
    assert "-MaskValues @($postgresSuperPassword)" in bootstrap


def test_error_report_never_carries_database_passwords():
    # setup-error.txt and the psql streams are copied to the public desktop.
    # A run leaked the app password because psql echoed the failing statement.
    bootstrap = BOOTSTRAP.read_text(encoding="utf-8-sig")
    assert "function Protect-Secrets" in bootstrap
    assert "$safe = Protect-Secrets $Text" in bootstrap
    assert "$script:SecretValues.Add($postgresSuperPassword)" in bootstrap
    assert "$script:SecretValues.Add($appDbPassword)" in bootstrap
    # Raw psql stdout/stderr and the generated .sql must not survive the call.
    invoke_psql = bootstrap.split("function Invoke-Psql")[1].split("\nfunction ")[0]
    assert "finally" in invoke_psql
    assert "Remove-Item -LiteralPath $scratch" in invoke_psql


def test_psql_arguments_are_quoted_and_exit_code_is_readable():
    bootstrap = BOOTSTRAP.read_text(encoding="utf-8-sig")
    # Start-Process joins -ArgumentList with spaces and quotes nothing, so a
    # multi-line DO block reached psql as one argument per word.
    assert "function Format-NativeArgument" in bootstrap
    invoke_psql = bootstrap.split("function Invoke-Psql")[1].split("\nfunction ")[0]
    assert "Format-NativeArgument" in invoke_psql
    assert "-ArgumentList $argString" in invoke_psql
    # Without touching Handle, ExitCode stays $null and every call throws.
    assert "$null = $process.Handle" in invoke_psql
    # SQL with newlines goes through a file, not -c.
    assert '"-f", $tempSql' in invoke_psql
    assert '"-c"' not in invoke_psql
    # Redirected psql output is in the console code page, not ANSI.
    assert 'Encoding = "Oem"' in bootstrap


def test_postgres_tools_never_wait_for_a_password_prompt():
    # The Grant helper runs in the same process and used to delete PGPASSWORD,
    # so the next psql prompted on a hidden console and the wizard froze at 84%.
    bootstrap = BOOTSTRAP.read_text(encoding="utf-8-sig")
    grant = Path("scripts/Grant-LocalPostgresAppPrivileges.ps1").read_text(encoding="utf-8-sig")
    backup = BACKUP.read_text(encoding="utf-8-sig")

    assert "$previousPgPassword = $env:PGPASSWORD" in grant
    assert "$env:PGPASSWORD = $previousPgPassword" in grant

    invoke_psql = bootstrap.split("function Invoke-Psql")[1].split("\nfunction ")[0]
    assert '"-X", "-w"' in invoke_psql
    assert "$env:PGPASSWORD = $postgresSuperPassword" in invoke_psql
    assert "-X -w -P pager=off" in grant
    assert "-w `" in backup
    assert "-U postgres -w -O nikacrm" in bootstrap


def test_upgrade_stops_services_before_copying_files():
    iss = ISS.read_text(encoding="utf-8-sig")
    assert "function PrepareToInstall" in iss
    assert "StopNikaService('NikaCRM-Web')" in iss
    assert "StopNikaService('NikaCRM-PostgreSQL')" in iss


def test_shortcuts_are_removed_by_wildcard():
    # Icons are created with an em dash; a hardcoded hyphen left them on the
    # desktop after uninstall.
    iss = ISS.read_text(encoding="utf-8-sig")
    assert '"{commondesktop}\\Nika CRM*"' in iss
    cleanup = CLEANUP.read_text(encoding="utf-8-sig")
    assert "Nika CRM*" in cleanup
    assert "Nika CRM - " not in cleanup


def test_uninstall_backs_up_database_before_wiping_data():
    assert BACKUP.exists()
    assert FULL_UNINSTALL.exists()
    iss = ISS.read_text(encoding="utf-8-sig")
    assert "backup-database.ps1" in iss
    assert "KeepDataDir := True" in iss
    assert "DelTree(DataDir, True, True, True)" in iss
    backup = BACKUP.read_text(encoding="utf-8-sig")
    assert "pg_dump.exe" in backup
    assert "NikaCRM-backup" in backup


def test_reinstall_handles_previous_install_leftovers():
    bootstrap = BOOTSTRAP.read_text(encoding="utf-8-sig")
    # Stale service registration, leftover cluster and leftover service account
    # each break the unattended PostgreSQL installer.
    assert "Removing stale $postgresServiceName service registration" in bootstrap
    assert "PG_VERSION" in bootstrap
    assert 'Get-LocalUser -Name "postgres"' in bootstrap
    # A reinstall must restore real data instead of the demo database.
    assert 'Filter "nikacrm-*.sql"' in bootstrap


def test_upgrade_fixes_ownership_before_migrations():
    bootstrap = BOOTSTRAP.read_text(encoding="utf-8-sig")
    owner_at = bootstrap.index("ALTER %s %I.%I OWNER TO nikacrm")
    migrate_at = bootstrap.index("scripts\\run_migrations.py")
    # Dumps are loaded by the postgres superuser; migrations run as nikacrm and
    # ALTER TABLE needs ownership. 1.0.6 -> 1.0.7 died here.
    assert owner_at < migrate_at
    # And the failure has to be readable in Windows\Temp after Inno rollback.
    assert "-CaptureOutput" in bootstrap
    assert "RedirectStandardError" in bootstrap
    assert "setup-error.txt" in bootstrap
    assert "native-$stamp.err.log" in bootstrap
    # A serial sequence rejects ALTER OWNER on its own ("linked to table") and
    # took the whole DO block down with exit code 3.
    owner_block = bootstrap[bootstrap.index("$ownerSql = @") : owner_at]
    assert "d.deptype IN ('a', 'i')" in owner_block
    assert "c.relkind = 'S'" in owner_block


def test_migration_prebackup_can_be_delegated():
    bootstrap = BOOTSTRAP.read_text(encoding="utf-8-sig")
    assert 'SKIP_PRE_MIGRATION_BACKUP = "1"' in bootstrap
    runner = Path("scripts/run_migrations.py").read_text(encoding="utf-8")
    assert "SKIP_PRE_MIGRATION_BACKUP" in runner


def test_installer_version_is_in_sync():
    version = Path("VERSION").read_text(encoding="utf-8").splitlines()[0].strip()
    iss = ISS.read_text(encoding="utf-8-sig")
    bootstrap = BOOTSTRAP.read_text(encoding="utf-8-sig")
    from app.version import APP_VERSION

    assert APP_VERSION == version
    assert "FileRead(VersionFileHandle)" in iss
    assert "VersionInfoVersion={#MyAppVersion}.0" in iss
    assert 'Join-Path $appRoot "VERSION"' in bootstrap
    assert "app_version" in bootstrap
    assert "version_history" in bootstrap


def test_upgrade_snapshots_app_files_for_rollback():
    iss = ISS.read_text(encoding="utf-8-sig")
    assert "robocopy.exe" in iss
    assert "NikaCRM\\rollback" in iss or r"NikaCRM\rollback" in iss
    assert "Select-Object -Skip 2" in iss


def test_bundled_python_does_not_touch_an_existing_install():
    bootstrap = BOOTSTRAP.read_text(encoding="utf-8-sig")
    iss = ISS.read_text(encoding="utf-8-sig")
    helper = Path("packaging/windows/remove-nika-python.ps1").read_text(encoding="utf-8-sig")
    build = Path("scripts/windows/build-offline-bundle.ps1").read_text(encoding="utf-8-sig")
    verify = Path("scripts/windows/verify-bundle.ps1").read_text(encoding="utf-8-sig")
    service = Path("packaging/windows/service_entry.py").read_text(encoding="utf-8")

    assert "python-installer.exe" not in bootstrap
    assert "python-installer.exe" not in iss
    assert "python-installer.exe" not in verify
    assert "InstallAllUsers" not in bootstrap
    assert "PrependPath" not in bootstrap
    assert "python-3.12.10-embed-amd64.zip" in bootstrap
    assert "python-3.12.10-embed-amd64.zip" in iss
    assert "python-3.12.10-embed-amd64.zip" in build
    assert "import site" not in bootstrap
    assert "Lib\\site-packages" in bootstrap
    assert "--target" in bootstrap
    assert "PYTHONNOUSERSITE" in bootstrap
    assert "PYTHONNOUSERSITE" in service
    assert 'os.environ.pop("PYTHONPATH", None)' in service
    assert "sys.path.insert(0, str(APP_ROOT))" in service
    assert service.index("sys.path.insert(0, str(APP_ROOT))") < service.index("from wsgi import app")
    assert "Remove-NikaBundledPython" in bootstrap
    assert "Remove-NikaBundledPython" in CLEANUP.read_text(encoding="utf-8-sig")
    assert "Remove-NikaBundledPython" in FULL_UNINSTALL.read_text(encoding="utf-8-sig")
    assert "function Test-NikaOwnedPath" in helper
    assert "Leaving separately installed Python" in helper
    assert "Uninstall-Package" not in helper
    assert '"pip" "setuptools" "wheel"' in build
    assert "UserWantsDataRemoved" in iss
    assert "не удаляются" in iss

    probe = (
        ". ./packaging/windows/remove-nika-python.ps1; "
        "$app = 'C:\\Program Files\\NikaCRM'; "
        "$own = Test-NikaOwnedPath -Candidate '\"C:\\Program Files\\NikaCRM\\runtime\\python\\python.exe\" \"%1\"' -AppDir $app; "
        "$sibling = Test-NikaOwnedPath -Candidate 'C:\\Program Files\\NikaCRM-extra\\python.exe' -AppDir $app; "
        "$foreign = Test-NikaOwnedPath -Candidate 'C:\\Users\\Client\\AppData\\Local\\Programs\\Python\\Python312\\python.exe' -AppDir $app; "
        "if (-not $own -or $sibling -or $foreign) { exit 1 }"
    )
    import subprocess

    completed = subprocess.run(
        ["powershell", "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", probe],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_bootstrap_reports_progress_for_the_wizard():
    bootstrap = BOOTSTRAP.read_text(encoding="utf-8-sig")
    assert "function Set-SetupProgress" in bootstrap
    assert "setup-progress.txt" in bootstrap
    assert "setup-progress.done" in bootstrap
    assert "function Test-LocalHttpOk" in bootstrap
    assert "function Write-InstallerFile" in bootstrap
    assert "ProgressDir" in bootstrap
    assert "Invoke-WebRequest -Uri" not in bootstrap
    assert "Get-NetIPAddress -AddressFamily" not in bootstrap
    assert "GetEmptyWebProxy" in bootstrap
    iss = ISS.read_text(encoding="utf-8-sig")
    assert "RunBootstrapWithProgress" in iss
    assert "Exec(ExpandConstant('{cmd}'), Params, ProgressDir, SW_HIDE, ewNoWait, ResultCode)" in iss
    assert "Exec(PowerShell, Params, '', SW_HIDE, ewWaitUntilTerminated, ResultCode)" not in iss
    assert "Wait=setup-progress.done" in iss
    assert "while not FileExists(ProgressDir + '\\setup-progress.done')" in iss
    assert "PeekMessageW@user32.dll" in iss
    assert "function Invoke-Psql" in bootstrap
    assert 'pager=off' in bootstrap
    assert "Get-NetFirewallRule" not in bootstrap
    assert "[string]::IsNullOrWhiteSpace" in bootstrap
    assert r"{win}\Temp\NikaCRM-setup" in iss or "{win}\\Temp\\NikaCRM-setup" in iss
    assert "installer-launch.log" in iss
    assert "NikaCRM-setup-log" in iss
    assert "'-NonInteractive" not in iss
    assert '"-NonInteractive' not in iss
    assert "run-bootstrap.cmd" not in iss
    for icon in (
        r'{commondesktop}\Nika CRM — Открыть',
        r'{commondesktop}\Nika CRM — Перезапустить сервис',
        r'{commondesktop}\Ника Сервис — Сайт',
    ):
        assert icon in iss, icon
    assert "create-desktop-icons" not in iss
    assert "Не закрывайте окно" in iss
    assert "[Parameter(Mandatory = $true)]" not in bootstrap.split("function Write-InstallerFile")[0]
    assert 'Join-Path $env:SystemRoot "Temp\\NikaCRM-setup"' in bootstrap or "Temp\\NikaCRM-setup" in bootstrap
    assert "setup-error.txt" in iss
    assert "ReadSetupErrorHint" in iss
    assert "launch-bootstrap.cmd" in iss
    assert "type \"" in iss or 'type "' in iss
    assert "LanguageMode=" in bootstrap
    assert "RestrictedLanguage" in bootstrap


def test_bundle_ships_the_timezone_database():
    """Embeddable Python has no tz database: without tzdata every dated page is a 500."""
    requirements = Path("packaging/windows/requirements-windows.txt").read_text(encoding="utf-8")
    assert "tzdata" in requirements
    utils = Path("app/utils/datetime_utils.py").read_text(encoding="utf-8")
    assert 'ZoneInfo("Europe/Moscow")' in utils
    # ZoneInfoNotFoundError is a KeyError subclass, so the fallback must catch it.
    assert "except (ImportError, KeyError, ValueError)" in utils

