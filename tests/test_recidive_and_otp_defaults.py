"""fail2ban recidive template: permanent ban, not a short timeout."""
from pathlib import Path


def test_recidive_example_is_permanent():
    text = (
        Path(__file__).resolve().parents[1]
        / "deploy"
        / "hardening"
        / "fail2ban"
        / "jail.d"
        / "recidive.local.example"
    ).read_text(encoding="utf-8")
    assert "[recidive]" in text
    assert "bantime = -1" in text
    assert "backend = polling" in text
    assert "maxretry = 3" in text
    assert "nika-mail" in text


def test_staff_email_otp_stays_off_by_default():
    example = (Path(__file__).resolve().parents[1] / ".env.example").read_text(encoding="utf-8")
    assert "STAFF_EMAIL_OTP_ENABLED=false" in example
    cfg = (Path(__file__).resolve().parents[1] / "app" / "config.py").read_text(encoding="utf-8")
    assert "STAFF_EMAIL_OTP_ENABLED" in cfg
    assert "deferred release" in cfg or "false" in cfg
