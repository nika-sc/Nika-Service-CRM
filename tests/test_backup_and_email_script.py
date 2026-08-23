"""Guards: nightly snapshot packs data + files, not junk or ops secrets."""
from pathlib import Path


def test_backup_and_email_full_snapshot_two_archives():
    src = (Path(__file__).resolve().parents[1] / "scripts" / "backup_and_email.sh").read_text(
        encoding="utf-8"
    )
    assert 'STAGE="$TMP_DIR/payload"' in src
    assert "data/uploads" in src
    assert "RESTORE.sh" in src
    assert "RESTORE.txt" in src
    assert "crm_data_backup_" in src
    assert "crm_files_backup_" in src
    assert "--exclude='.git'" in src
    assert "--exclude='venv'" in src
    assert "--exclude='data/database/backups'" in src
    assert "--exclude='data/uploads'" in src
    assert 'tar -I "xz $BACKUP_XZ_OPTS" -cf "$DATA_TAR" -C "$TMP_DIR" payload' in src
    assert 'tar -I "xz $BACKUP_XZ_OPTS" -cf "$FILES_TAR" -C "$TMP_DIR" files' in src
    assert "BACKUP_ARCHIVE_PASSWORD" in src
    assert "p7zip" in src or "SEVENZ_BIN" in src
    assert "-mhe=on" in src
    assert "-t7z" in src
    assert "openssl enc -aes-256-cbc" not in src
    assert "backup_push_work_restore.sh" in src
    assert "BACKUP_PUSH_PRIVATE" in src
    assert "split_7z_mail_parts" in src
    assert 'VOLUME_BYTES="${BACKUP_7Z_VOLUME_BYTES:-25000000}"' in src
    assert 'ATTACH_MAX="${BACKUP_ATTACH_MAX_BYTES:-28000000}"' in src
    assert "_mail.7z" in src
    assert 'send_mail_parts' in src
    assert "smelkov2008" not in src
    assert ".".join(("86", "110", "194", "218")) not in src
    assert ".".join(("155", "212", "167", "2")) not in src
    assert "crm.nika-sc.ru" not in src
    assert "BACKUP_EMAIL_TO" in src
    assert "you@example.com" in src
    assert "PGDMP" in src
    assert "flock" in src
    assert "BACKUP_FORCE" in src
    assert "без исходников с GitHub" not in src
