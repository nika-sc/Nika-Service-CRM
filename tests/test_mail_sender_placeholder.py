"""Отправитель: демо noreply@example.com не должен побеждать реальный MAIL_USERNAME."""


class _App:
    def __init__(self, **cfg):
        self.config = cfg


def test_placeholder_sender_falls_back_to_username():
    from app.services.notification_service import _resolve_sender_email

    app = _App(
        MAIL_DEFAULT_SENDER='Nika CRM Demo <noreply@example.com>',
        MAIL_USERNAME='nika-sc@bk.ru',
    )
    assert _resolve_sender_email(app) == 'nika-sc@bk.ru'


def test_real_sender_kept():
    from app.services.notification_service import _resolve_sender_email

    app = _App(
        MAIL_DEFAULT_SENDER='SC <sales@bk.ru>',
        MAIL_USERNAME='nika-sc@bk.ru',
    )
    assert _resolve_sender_email(app) == 'sales@bk.ru'


def test_apply_replaces_demo_sender(monkeypatch):
    from app.services import notification_service as ns
    import app.services.settings_service as ss

    monkeypatch.setattr(
        ss.SettingsService,
        'get_general_settings',
        staticmethod(lambda: {
            'mail_server': 'smtp.mail.ru',
            'mail_port': 587,
            'mail_use_tls': True,
            'mail_use_ssl': False,
            'mail_username': 'nika-sc@bk.ru',
            'mail_password': 'x',
            'mail_default_sender': 'Nika CRM Demo <noreply@example.com>',
            'mail_timeout': 3,
        }),
    )
    app = _App(
        MAIL_SERVER='localhost',
        MAIL_DEFAULT_SENDER='noreply@service-center.local',
        MAIL_USERNAME='',
        MAIL_PASSWORD='',
        MAIL_PORT=587,
        MAIL_TIMEOUT=3,
    )
    ns._apply_mail_config_from_settings(app)
    assert app.config['MAIL_DEFAULT_SENDER'] == 'nika-sc@bk.ru'
    assert ns._resolve_sender_email(app) == 'nika-sc@bk.ru'
