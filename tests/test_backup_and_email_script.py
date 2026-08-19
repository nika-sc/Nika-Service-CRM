"""Guards: nightly email backup packs restore data, not the git tree."""
from pathlib import Path


def test_backup_and_email_packs_payload_not_full_tree():
    src = (Path(__file__).resolve().parents[1] / "scripts" / "backup_and_email.sh").read_text(
        encoding="utf-8"
    )
    assert 'STAGE="$TMP_DIR/payload"' in src
    assert "data/uploads" in src
    assert "GIT_HEAD" in src
    assert "/var/www/nikacrm-downloads" not in src
    assert "/var/www/html" not in src
    assert "crm_data_backup_" in src
    assert 'tar -I "xz $BACKUP_XZ_OPTS" -cf "$ARCHIVE_FILE" -C "$TMP_DIR" payload' in src
    assert "BACKUP_ARCHIVE_PASSWORD" in src
    assert "p7zip" in src or "SEVENZ_BIN" in src
    assert "-mhe=on" in src
    assert "-t7z" in src
    assert "openssl enc -aes-256-cbc" not in src
    assert "backup_push_work_restore.sh" in src
    assert "BACKUP_PUSH_PRIVATE" in src
    assert "--exclude='./.git'" not in src
    assert "smelkov2008" not in src
    assert ".".join(("86", "110", "194", "218")) not in src
    assert ".".join(("155", "212", "167", "2")) not in src
    assert "crm.nika-sc.ru" not in src
    assert "BACKUP_EMAIL_TO" in src
    assert "you@example.com" in src
