"""
Конфигурация приложения.
"""
import os
from datetime import timedelta

# Корень проекта (каталог, в котором лежит папка app/) — для абсолютного пути к БД
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEFAULT_DATABASE_PATH = os.path.join(_PROJECT_ROOT, 'database', 'service_center.db')


class Config:
    """Базовая конфигурация приложения."""
    
    # Секретный ключ
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Драйвер БД: sqlite или postgres
    DB_DRIVER = os.environ.get('DB_DRIVER', 'sqlite').lower()
    DATABASE_URL = os.environ.get('DATABASE_URL', '')

    # База данных SQLite: по умолчанию — абсолютный путь из корня проекта
    DATABASE_PATH = os.environ.get('DATABASE_PATH', _DEFAULT_DATABASE_PATH)
    
    # Flask-Login
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=1)
    SESSION_COOKIE_NAME = os.environ.get('SESSION_COOKIE_NAME', 'nikacrm_session')
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = 'Lax'
    REMEMBER_COOKIE_DURATION = timedelta(days=14)
    REMEMBER_COOKIE_NAME = os.environ.get('REMEMBER_COOKIE_NAME', 'nikacrm_remember')
    # Лимит размера тела запроса (защита от больших payload / DoS)
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', str(12 * 1024 * 1024)))  # 12MB
    # Допустимые Host заголовки (защита от Host Header attacks).
    # Токен @private разрешает любой private/loopback/link-local IP
    # (192.168/16, 10/8, 172.16–31/12 и т.п.) — удобно для LAN при DHCP.
    # В create_app список копируется в HOST_ALLOWLIST, а Flask TRUSTED_HOSTS
    # сбрасывается в None: Werkzeug не понимает @private и режет LAN IP с 400.
    TRUSTED_HOSTS = [
        h.strip().lower()
        for h in (os.environ.get(
            'TRUSTED_HOSTS',
            'localhost,127.0.0.1'
        ) or '').split(',')
        if h.strip()
    ]
    # Глобальный лимит state-changing API запросов на IP (в минуту)
    WRITE_API_RATE_LIMIT_PER_MIN = int(os.environ.get('WRITE_API_RATE_LIMIT_PER_MIN', '120'))
    # CSP в режиме report-only для безопасного внедрения без поломки интерфейса
    CSP_REPORT_ONLY = os.environ.get('CSP_REPORT_ONLY', 'true').strip().lower() in ('1', 'true', 'yes', 'on')
    CSP_REPORT_URI = (os.environ.get('CSP_REPORT_URI') or '').strip()
    # Enforcement на логин и API (остальные страницы — report-only, пока CSP_REPORT_ONLY=true)
    CSP_ENFORCE_PATH_PREFIXES = [
        p.strip() for p in (
            os.environ.get('CSP_ENFORCE_PATH_PREFIXES', '/login,/portal/login,/api/,/portal/api/') or ''
        ).split(',') if p.strip()
    ]
    # strict CSP with nonce: off | report | enforce
    CSP_NONCE_MODE = (os.environ.get('CSP_NONCE_MODE') or 'report').strip().lower()
    if CSP_NONCE_MODE not in ('off', 'report', 'enforce'):
        CSP_NONCE_MODE = 'report'
    # Email OTP after password (deferred release — disabled by default)
    STAFF_EMAIL_OTP_ENABLED = os.environ.get('STAFF_EMAIL_OTP_ENABLED', 'false').strip().lower() in (
        '1', 'true', 'yes', 'on',
    )
    # Lockout защита от brute-force (staff login)
    LOGIN_LOCKOUT_THRESHOLD = int(os.environ.get('LOGIN_LOCKOUT_THRESHOLD', '8'))
    LOGIN_LOCKOUT_WINDOW_SEC = int(os.environ.get('LOGIN_LOCKOUT_WINDOW_SEC', '600'))
    LOGIN_LOCKOUT_DURATION_SEC = int(os.environ.get('LOGIN_LOCKOUT_DURATION_SEC', '900'))
    # Lockout защита от brute-force (portal login)
    PORTAL_LOGIN_LOCKOUT_THRESHOLD = int(os.environ.get('PORTAL_LOGIN_LOCKOUT_THRESHOLD', '10'))
    PORTAL_LOGIN_LOCKOUT_WINDOW_SEC = int(os.environ.get('PORTAL_LOGIN_LOCKOUT_WINDOW_SEC', '600'))
    PORTAL_LOGIN_LOCKOUT_DURATION_SEC = int(os.environ.get('PORTAL_LOGIN_LOCKOUT_DURATION_SEC', '900'))
    
    # Flask-Limiter
    # Flask-Limiter 3.x использует ключ RATELIMIT_STORAGE_URI (а не *_URL)
    RATELIMIT_STORAGE_URI = os.environ.get('RATELIMIT_STORAGE_URI', 'memory://')
    # Backward-compat: если где-то в коде/доках используется *_URL
    RATELIMIT_STORAGE_URL = RATELIMIT_STORAGE_URI
    RATELIMIT_DEFAULT = "3000 per day;1000 per hour"
    
    # Пагинация
    ITEMS_PER_PAGE = 50
    MAX_ITEMS_PER_PAGE = 200
    
    # Логирование
    LOG_FILE = 'app.log'
    LOG_LEVEL = 'INFO'
    LOG_SLOW_QUERIES = os.environ.get('LOG_SLOW_QUERIES', 'True').lower() == 'true'
    SLOW_QUERY_THRESHOLD_MS = int(os.environ.get('SLOW_QUERY_THRESHOLD_MS', '150'))
    
    # Debug режим (отключить в продакшене!)
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    # Часовой пояс (смещение от UTC в часах, по умолчанию 3 для Москвы)
    # Можно переопределить через переменную окружения TIMEZONE_OFFSET
    TIMEZONE_OFFSET = int(os.environ.get('TIMEZONE_OFFSET', '3'))
    
    # Flask-Mail настройки
    # Пустой default: иначе Flask-Mail/старый код ходит на localhost → WinError 10061.
    MAIL_SERVER = os.environ.get('MAIL_SERVER', '')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'False').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
    # Пусто по умолчанию: при отправке берётся MAIL_USERNAME (демо noreply@example.com ломает Mail.ru).
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', '')
    MAIL_TIMEOUT = int(os.environ.get('MAIL_TIMEOUT', 15))
    
    # Flask-SocketIO настройки
    SOCKETIO_ASYNC_MODE = 'threading'
    # Допустимые origin для Socket.IO (CSV или '*').
    # Токен @private добавляет http://<локальный-IP>:<APP_PORT> и hostname.
    SOCKETIO_CORS_ALLOWED_ORIGINS = os.environ.get(
        'SOCKETIO_CORS_ALLOWED_ORIGINS',
        'http://localhost:5000,http://127.0.0.1:5000'
    )
    # Redis: общий кэш и message_queue Socket.IO между gunicorn-воркерами
    REDIS_URL = (os.environ.get('REDIS_URL') or '').strip() or None

    # Web Push (чат сотрудников, VAPID). Пустые ключи — функция отключена.
    STAFF_CHAT_VAPID_PUBLIC_KEY = os.environ.get("STAFF_CHAT_VAPID_PUBLIC_KEY", "").strip()
    _STAFF_CHAT_VAPID_PRIVATE_RAW = os.environ.get("STAFF_CHAT_VAPID_PRIVATE_KEY", "").strip()
    STAFF_CHAT_VAPID_PRIVATE_KEY = (
        _STAFF_CHAT_VAPID_PRIVATE_RAW.replace("\\n", "\n") if _STAFF_CHAT_VAPID_PRIVATE_RAW else ""
    )
    STAFF_CHAT_VAPID_CLAIM_EMAIL = os.environ.get(
        "STAFF_CHAT_VAPID_CLAIM_EMAIL", "mailto:noreply@localhost"
    ).strip()

    # SEO-промолендинг на анонимном «/» (только демо-VPS: PUBLIC_LANDING=1).
    # WORK / локально без флага — как раньше (редирект на /login).
    PUBLIC_LANDING = os.environ.get("PUBLIC_LANDING", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    # Канонический URL лендинга для meta/sitemap (иначе берётся request.url_root).
    PUBLIC_LANDING_CANONICAL = (os.environ.get("PUBLIC_LANDING_CANONICAL") or "").strip().rstrip("/")

    # Публичный адрес CRM для ссылок в письмах клиенту (##PORTAL_URL##).
    # Письма уходят из фонового потока без request-контекста, поэтому адрес нужен явно.
    PORTAL_PUBLIC_URL = (os.environ.get("PORTAL_PUBLIC_URL") or "").strip().rstrip("/")

    # Публичное демо: подсказка на /login (учётка, счётчики из БД, текст про железо).
    # Включать только на демо-VPS: DEMO_LOGIN_BANNER=1
    DEMO_LOGIN_BANNER = os.environ.get("DEMO_LOGIN_BANNER", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    DEMO_LOGIN_USERNAME_HINT = (os.environ.get("DEMO_LOGIN_USERNAME_HINT") or "demo_admin").strip()
    DEMO_LOGIN_PASSWORD_HINT = (os.environ.get("DEMO_LOGIN_PASSWORD_HINT") or "Demo2026!").strip()
    # Многострочный текст: в .env можно писать \n для переносов
    DEMO_SERVER_SPEC = (os.environ.get("DEMO_SERVER_SPEC") or "").strip().replace("\\n", "\n")
    # Демо-статистика заходов / баннер «онлайн» (только demo-VPS)
    DEMO_VISITOR_STATS = os.environ.get("DEMO_VISITOR_STATS", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    # Исходящая почта. На публичном демо (DEMO_LOGIN_BANNER) всегда выключена.
    # Для self-hosted можно выключить явно: MAIL_SENDING_ENABLED=false
    MAIL_SENDING_ENABLED = os.environ.get("MAIL_SENDING_ENABLED", "true").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )

    # Реферальная ссылка на VPS (панель демо-входа; можно переопределить в .env)
    REFERRAL_VPS_PROVIDER_LABEL = (os.environ.get("REFERRAL_VPS_PROVIDER_LABEL") or "FirstVDS").strip()
    REFERRAL_VPS_URL = (
        os.environ.get("REFERRAL_VPS_URL") or "https://firstvds.ru/?from=528402"
    ).strip()
    REFERRAL_VPS_PROMO_CODE = (os.environ.get("REFERRAL_VPS_PROMO_CODE") or "648528402").strip()


class DevelopmentConfig(Config):
    """Конфигурация для разработки."""
    DEBUG = True
    LOG_LEVEL = 'DEBUG'


class ProductionConfig(Config):
    """Конфигурация для продакшена."""
    DEBUG = False
    LOG_LEVEL = 'WARNING'
    
    # В продакшене SECRET_KEY должен быть установлен через переменную окружения
    # Проверка будет выполнена в create_app при инициализации
    
    # USE_HTTPS=true — для работы только по HTTPS (куки Secure, схема https)
    # USE_HTTPS=false — для работы по HTTP (пока не настроен SSL)
    _use_https = os.environ.get('USE_HTTPS', 'false').lower() == 'true'
    
    SESSION_COOKIE_SECURE = _use_https
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    REMEMBER_COOKIE_SECURE = _use_https
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = 'Lax'
    
    PREFERRED_URL_SCHEME = 'https' if _use_https else 'http'
    
    # Защита от clickjacking
    SEND_FILE_MAX_AGE_DEFAULT = timedelta(hours=1)


class TestingConfig(Config):
    """Конфигурация для тестирования."""
    TESTING = True
    DEBUG = True
    LOG_LEVEL = 'DEBUG'
    
    # Используем тестовую БД (будет переопределена в conftest.py)
    DATABASE_PATH = ':memory:'  # In-memory база для быстрых тестов
    
    # Отключаем CSRF для тестов
    WTF_CSRF_ENABLED = False
    
    # Отключаем rate limiting для тестов
    RATELIMIT_ENABLED = False


# Словарь конфигураций
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

