"""Windows offline installer: secrets stay out of logs and of the public bundle."""
from pathlib import Path

ISS = Path("packaging/windows/NikaCRM.iss")
BOOTSTRAP = Path("packaging/windows/bootstrap.ps1")


def test_installer_does_not_pack_private_docs():
    src = ISS.read_text(encoding="utf-8-sig")
    docs_line = next(line for line in src.splitlines() if '\\docs\\*"' in line)
    assert 'Excludes: "private\\*,*\\private\\*"' in docs_line


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


def test_installer_version_is_in_sync():
    iss = ISS.read_text(encoding="utf-8-sig")
    bootstrap = BOOTSTRAP.read_text(encoding="utf-8-sig")
    version = next(
        line.split('"')[1] for line in iss.splitlines() if line.startswith("#define MyAppVersion")
    )
    assert f"VersionInfoVersion={version}.0" in iss
    assert f"Bootstrap version {version}" in bootstrap
