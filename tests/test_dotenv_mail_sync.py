from pathlib import Path


def test_upsert_preserves_comments_and_other_keys(tmp_path: Path):
    from app.utils.dotenv_file import upsert_dotenv_keys

    env = tmp_path / ".env"
    env.write_text(
        "# keep me\nSECRET_KEY=abc\nMAIL_SERVER=\nOTHER=1\n",
        encoding="utf-8",
    )
    assert upsert_dotenv_keys(
        env,
        {
            "MAIL_SERVER": "smtp.mail.ru",
            "MAIL_PORT": "587",
            "MAIL_USERNAME": "a@b.ru",
        },
    )
    text = env.read_text(encoding="utf-8")
    assert "# keep me" in text
    assert "SECRET_KEY=abc" in text
    assert "OTHER=1" in text
    assert "MAIL_SERVER=smtp.mail.ru" in text
    assert "MAIL_USERNAME=a@b.ru" in text
    assert "MAIL_PORT=587" in text


def test_sync_skips_empty_password(tmp_path: Path, monkeypatch):
    from app.utils import dotenv_file as df

    env = tmp_path / ".env"
    env.write_text("MAIL_PASSWORD=keep-me\nMAIL_SERVER=\n", encoding="utf-8")
    monkeypatch.setattr(df, "resolve_dotenv_path", lambda: env)
    df.sync_mail_settings_to_dotenv(
        {
            "mail_server": "smtp.mail.ru",
            "mail_port": 587,
            "mail_use_tls": True,
            "mail_use_ssl": False,
            "mail_username": "a@b.ru",
            "mail_password": "",
            "mail_default_sender": "a@b.ru",
        }
    )
    text = env.read_text(encoding="utf-8")
    assert "MAIL_PASSWORD=keep-me" in text
    assert "MAIL_SERVER=smtp.mail.ru" in text


def test_sync_writes_ascii_mailbox_only_for_sender(tmp_path: Path, monkeypatch):
    from app.utils import dotenv_file as df

    env = tmp_path / ".env"
    env.write_text("MAIL_DEFAULT_SENDER=\n", encoding="utf-8")
    monkeypatch.setattr(df, "resolve_dotenv_path", lambda: env)
    df.sync_mail_settings_to_dotenv(
        {
            "mail_server": "smtp.mail.ru",
            "mail_port": 587,
            "mail_use_tls": True,
            "mail_use_ssl": False,
            "mail_username": "a@b.ru",
            "mail_password": "secret",
            "mail_default_sender": "Сервисный центр Ника <a@b.ru>",
        }
    )
    text = env.read_text(encoding="utf-8")
    assert "MAIL_DEFAULT_SENDER=a@b.ru" in text
    assert "Сервисный" not in text
    assert 'MAIL_DEFAULT_SENDER="' not in text
    assert "MAIL_PASSWORD=secret" in text
