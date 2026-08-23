"""Nightly backup healthcheck must see current .7z archives, not only legacy tar.xz."""
from pathlib import Path


def test_backup_healthcheck_accepts_7z_and_legacy_names():
    src = (Path(__file__).resolve().parents[1] / "scripts" / "backup_healthcheck.py").read_text(
        encoding="utf-8"
    )
    assert "crm_data_backup_*.7z" in src
    assert "crm_files_backup_*.7z" in src
    assert "crm_files_backup_*_mail.7z.*" in src
    assert "DONE backup job" in src
    assert "crm_data_backup_*.tar.xz" in src
    assert "smelkov2008" not in src
    assert ".".join(("86", "110", "194", "218")) not in src
