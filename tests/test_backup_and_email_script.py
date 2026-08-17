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
    assert "--exclude='./.git'" not in src
