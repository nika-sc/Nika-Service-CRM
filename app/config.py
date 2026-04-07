"""
Конфигурация приложения.
"""
import os
from datetime import timedelta

# Корень проекта (каталог, в котором лежит папка app/) — для абсолютного пути к fallback SQLite
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEFAULT_DATABASE_PATH = os.path.join(_PROJECT_ROOT, 'database', 'service_center.db')


class Config:
    """Базовая конфигурация приложения."""
    
    # Секретный ключ
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Драйвер БД: postgres (по умолчанию) или sqlite (только локальный fallback)
    DB_DRIVER = os.environ.get('DB_DRIVER', 'postgres').lower()
    DATABASE_URL = os.environ.get('DATABASE_URL', '')

    # База данных SQLite: по умолчанию — абсолютный путь из корня проекта
    DATABASE_PATH = os.environ.get('DATABASE_PATH', _DEFAULT_DATABASE_PATH)
    
    # Flask-Login
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=1)
    
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
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'localhost')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'False').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@service-center.local')
    MAIL_TIMEOUT = int(os.environ.get('MAIL_TIMEOUT', 3))
    
    # Flask-SocketIO настройки
    SOCKETIO_ASYNC_MODE = 'threading'
    # Допустимые origin для Socket.IO (CSV или '*')
    SOCKETIO_CORS_ALLOWED_ORIGINS = os.environ.get(
        'SOCKETIO_CORS_ALLOWED_ORIGINS',
        'https://crm.nika-sc.ru,http://crm.nika-sc.ru,http://localhost:5000,http://127.0.0.1:5000'
    )


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

