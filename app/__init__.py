"""
Инициализация Flask приложения.
"""
import logging
from fnmatch import fnmatch
import time
from collections import defaultdict, deque

from flask import Flask, redirect, url_for, Response, send_from_directory, request, jsonify
from flask_login import LoginManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect

from app.config import Config
from app.database.connection import init_db
from app.middleware.auth import setup_auth

# Инициализация расширений
login_manager = LoginManager()
limiter = Limiter(key_func=get_remote_address)
csrf = CSRFProtect()

# Flask-Mail опциональный (может быть не установлен)
try:
    from flask_mail import Mail  # type: ignore
    mail = Mail()
    MAIL_AVAILABLE = True
except ImportError:
    mail = None
    MAIL_AVAILABLE = False
    import warnings
    warnings.warn("Flask-Mail не установлен. Email функциональность будет недоступна.", ImportWarning)

# Flask-SocketIO опциональный (может быть не установлен)
try:
    from flask_socketio import SocketIO  # type: ignore
    socketio = SocketIO()
    SOCKETIO_AVAILABLE = True
except ImportError:
    socketio = None
    SOCKETIO_AVAILABLE = False
    import warnings
    warnings.warn("Flask-SocketIO не установлен. Push уведомления будут недоступны.", ImportWarning)


def create_app(config_class=Config):
    """
    Фабрика приложений Flask.
    
    Args:
        config_class: Класс конфигурации
        
    Returns:
        Flask: Экземпляр приложения
    """
    import os
    # Указываем правильные пути к шаблонам и статическим файлам
    # Они находятся в корне проекта, а не в app/
    template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
    static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static')
    
    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
    app.config.from_object(config_class)
    _write_api_buckets = defaultdict(deque)  # key: remote_addr, value: timestamps

    def _host_allowed(host_header: str) -> bool:
        trusted = app.config.get('TRUSTED_HOSTS') or []
        if not trusted:
            # Если список не задан, не блокируем трафик
            return True
        host = (host_header or '').split(':', 1)[0].strip().lower()
        if not host:
            return False
        for pattern in trusted:
            p = pattern.strip().lower()
            if not p:
                continue
            if p.startswith('*.'):
                # Разрешаем поддомены для шаблона вида *.example.com
                suffix = p[1:]  # .example.com
                if host.endswith(suffix) and host != suffix.lstrip('.'):
                    return True
            if fnmatch(host, p):
                return True
        return False

    @app.before_request
    def _security_precheck():
        # Блокируем неожиданные Host headers (Host header injection)
        if not _host_allowed(request.host):
            return jsonify({'success': False, 'error': 'invalid_host'}), 400
        # Базовый anti-DoS: global throttle для state-changing API
        if request.method in ('POST', 'PUT', 'PATCH', 'DELETE') and (
            request.path.startswith('/api/') or request.path.startswith('/portal/api/')
        ):
            limit = int(app.config.get('WRITE_API_RATE_LIMIT_PER_MIN', 120) or 120)
            now = time.time()
            key = (request.headers.get('X-Forwarded-For', '') or request.remote_addr or 'unknown').split(',')[0].strip()
            bucket = _write_api_buckets[key]
            window_start = now - 60.0
            while bucket and bucket[0] < window_start:
                bucket.popleft()
            if len(bucket) >= limit:
                return jsonify({'success': False, 'error': 'too_many_requests'}), 429
            bucket.append(now)

    # За nginx/proxy — корректные URL и HTTPS
    if not app.debug:
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    # Favicon: avoid 404 spam in browser console (serve SVG via redirect)
    @app.route('/favicon.ico')
    def favicon():
        return redirect(url_for('static', filename='favicon.svg'))

    # Звук входящего сообщения для внутреннего чата (файл в корне проекта).
    @app.route('/oh-oh-icq-sound.mp3')
    def staff_chat_sound():
        project_root = os.path.dirname(os.path.dirname(__file__))
        return send_from_directory(project_root, 'oh-oh-icq-sound.mp3')

    # robots.txt — запрет индексации CRM поисковыми роботами
    @app.route('/robots.txt')
    def robots_txt():
        return Response(
            "User-agent: *\nDisallow: /\n",
            mimetype="text/plain",
        )

    @app.after_request
    def _set_security_headers(response):
        # Защита от clickjacking, MIME-sniffing, лишней утечки referrer и API features
        response.headers.setdefault('X-Frame-Options', 'DENY')
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        # Глобально запрещаем индексацию поисковиками для закрытой CRM.
        response.headers.setdefault('X-Robots-Tag', 'noindex, nofollow, noarchive, nosnippet, noimageindex')
        response.headers.setdefault('Permissions-Policy', 'geolocation=(), camera=(), microphone=()')
        csp_parts = [
            "default-src 'self'",
            "base-uri 'self'",
            "object-src 'none'",
            "frame-ancestors 'none'",
            "img-src 'self' data: https:",
            "font-src 'self' data:",
            "style-src 'self' 'unsafe-inline'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
            "connect-src 'self' ws: wss: https:"
        ]
        csp_report_uri = app.config.get('CSP_REPORT_URI')
        if csp_report_uri:
            csp_parts.append(f"report-uri {csp_report_uri}")
        csp_value = '; '.join(csp_parts)
        enforce_prefixes = app.config.get('CSP_ENFORCE_PATH_PREFIXES') or []
        force_enforce_on_path = any((request.path or '').startswith(prefix) for prefix in enforce_prefixes)
        if app.config.get('CSP_REPORT_ONLY', True):
            response.headers.setdefault('Content-Security-Policy-Report-Only', csp_value)
        if force_enforce_on_path or not app.config.get('CSP_REPORT_ONLY', True):
            response.headers.setdefault('Content-Security-Policy', csp_value)
        # Включаем HSTS только при HTTPS
        if app.config.get('SESSION_COOKIE_SECURE'):
            response.headers.setdefault('Strict-Transport-Security', 'max-age=31536000; includeSubDomains')
        # Чувствительные страницы/ответы не кэшируем браузером
        p = request.path or ''
        if p.startswith('/login') or p.startswith('/portal/login') or p.startswith('/api/'):
            response.headers.setdefault('Cache-Control', 'no-store')
        return response

    @app.route('/staff-chat-push-sw.js')
    def staff_chat_push_sw():
        """Service Worker для Web Push чата; scope / через Service-Worker-Allowed."""
        resp = send_from_directory(static_dir, 'js/staff_chat_push_sw.js', mimetype='application/javascript')
        resp.headers['Cache-Control'] = 'no-cache, max-age=0'
        resp.headers['Service-Worker-Allowed'] = '/'
        return resp

    # Проверка SECRET_KEY для продакшена (только для ProductionConfig)
    from app.config import ProductionConfig
    if isinstance(config_class, type) and issubclass(config_class, ProductionConfig) and config_class != ProductionConfig:
        # Это ProductionConfig или его подкласс
        secret_key = app.config.get('SECRET_KEY')
        if not secret_key or secret_key == 'dev-secret-key-change-in-production':
            raise ValueError("SECRET_KEY должен быть установлен в переменных окружения для продакшена!")
    elif config_class == ProductionConfig:
        # Это именно ProductionConfig
        secret_key = app.config.get('SECRET_KEY')
        if not secret_key or secret_key == 'dev-secret-key-change-in-production':
            raise ValueError("SECRET_KEY должен быть установлен в переменных окружения для продакшена!")
    
    # Инициализация расширений
    login_manager.init_app(app)
    limiter.init_app(app)
    csrf.init_app(app)
    if mail is not None:
        mail.init_app(app)
    if socketio is not None:
        raw_origins = str(app.config.get('SOCKETIO_CORS_ALLOWED_ORIGINS', '')).strip()
        if not raw_origins:
            cors_origins = []
        elif raw_origins == '*':
            cors_origins = '*'
        else:
            cors_origins = [item.strip() for item in raw_origins.split(',') if item.strip()]
        socketio.init_app(
            app,
            async_mode=app.config.get('SOCKETIO_ASYNC_MODE', 'threading'),
            cors_allowed_origins=cors_origins,
        )
    
    # Настройка аутентификации
    setup_auth(login_manager)

    # Helpers for templates: permissions checks (cached per request)
    @app.context_processor
    def inject_permission_helpers():
        from flask import g
        from flask_login import current_user
        from app.services.user_service import UserService

        def has_permission(permission_name: str) -> bool:
            if not getattr(current_user, "is_authenticated", False):
                return False
            cache = getattr(g, "_perm_cache", None)
            if cache is None:
                cache = {}
                g._perm_cache = cache
            if permission_name not in cache:
                cache[permission_name] = bool(UserService.check_permission(current_user.id, permission_name))
            return cache[permission_name]

        def has_any_permission(*permission_names: str) -> bool:
            for p in permission_names:
                if has_permission(p):
                    return True
            return False

        def get_user_display_name(user_id=None, username=None):
            """
            Получает отображаемое имя пользователя (display_name или username).
            
            Args:
                user_id: ID пользователя (приоритет)
                username: Имя пользователя (fallback)
            
            Returns:
                Отображаемое имя пользователя
            """
            if user_id:
                try:
                    user = UserService.get_user_by_id(user_id, include_inactive=True)
                    if user:
                        return user.get('display_name') or user.get('username', 'Неизвестный')
                except Exception as e:
                    logging.getLogger(__name__).debug("get_user_display_name by id %s: %s", user_id, e)
            
            if username:
                try:
                    user = UserService.get_user_by_username(username)
                    if user:
                        return user.get('display_name') or user.get('username', username)
                except Exception as e:
                    logging.getLogger(__name__).debug("get_user_display_name by username %s: %s", username, e)
                return username or 'Неизвестный'
            
            return 'Неизвестный'

        return {
            "has_permission": has_permission,
            "has_any_permission": has_any_permission,
            "get_user_display_name": get_user_display_name,
        }
    
    # Регистрация кастомных фильтров для шаблонов (до инициализации БД и Blueprint'ов)
    def format_date_filter(date_str, with_time=False):
        """
        Форматирует дату в формат ДД.ММ.ГГГГ или ДД.ММ.ГГГГ ЧЧ:ММ:СС.
        
        Args:
            date_str: Строка с датой в формате YYYY-MM-DD или YYYY-MM-DD HH:MM:SS
            with_time: Если True, всегда показывает время (если оно есть), иначе только если время присутствует в исходной строке
            
        Returns:
            Строка в формате ДД.ММ.ГГГГ ЧЧ:ММ:СС или ДД.ММ.ГГГГ
        """
        if not date_str:
            return '—'
        
        try:
            from datetime import datetime
            # Пробуем разные форматы с временем
            formats_with_time = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d %H:%M:%S.%f',
                '%Y-%m-%d %H:%M',
                '%Y-%m-%dT%H:%M:%S', # ISO format
                '%Y-%m-%dT%H:%M:%S.%f' # ISO format with microseconds
            ]
            
            # Сначала пробуем форматы с временем
            for fmt in formats_with_time:
                try:
                    dt = datetime.strptime(str(date_str).strip(), fmt)
                    # НОВЫЕ записи уже сохраняются в московском времени (UTC+3)
                    # НЕ конвертируем, так как время уже в правильном часовом поясе
                    # Для старых записей (до 2025-12-27) можно было бы конвертировать,
                    # но проще оставить как есть - они уже отображались неправильно
                    # и пользователи к этому привыкли, или можно добавить проверку даты
                    if with_time:
                        return dt.strftime('%d.%m.%Y %H:%M:%S')
                    else:
                        return dt.strftime('%d.%m.%Y')
                except ValueError:
                    continue
            
            # Если не удалось распарсить с временем, пробуем только дату
            try:
                dt = datetime.strptime(str(date_str).strip(), '%Y-%m-%d')
                return dt.strftime('%d.%m.%Y')
            except ValueError:
                pass
            
            # Если не удалось распарсить, пробуем взять первые 10 символов (YYYY-MM-DD)
            if len(str(date_str)) >= 10:
                date_part = str(date_str)[:10]
                try:
                    dt = datetime.strptime(date_part, '%Y-%m-%d')
                    # Проверяем, есть ли время в исходной строке
                    date_str_clean = str(date_str).strip()
                    if len(date_str_clean) > 10:
                        # Пробуем извлечь время (может быть после пробела или T)
                        time_part = None
                        if ' ' in date_str_clean:
                            time_part = date_str_clean.split(' ')[1][:8]  # Берем первые 8 символов времени
                        elif 'T' in date_str_clean:
                            time_part = date_str_clean.split('T')[1][:8]  # ISO формат
                        
                        if time_part and len(time_part) >= 5:  # Минимум HH:MM
                            try:
                                # Пробуем разные форматы времени
                                if len(time_part) == 8:  # HH:MM:SS
                                    time_dt = datetime.strptime(time_part, '%H:%M:%S')
                                    # Объединяем дату и время
                                    full_dt = datetime.combine(dt.date(), time_dt.time())
                                    # Уже в московском времени (новые записи), не конвертируем
                                    return full_dt.strftime('%d.%m.%Y %H:%M:%S')
                                elif len(time_part) == 5:  # HH:MM
                                    time_dt = datetime.strptime(time_part, '%H:%M')
                                    # Объединяем дату и время
                                    full_dt = datetime.combine(dt.date(), time_dt.time())
                                    # Уже в московском времени (новые записи), не конвертируем
                                    return full_dt.strftime('%d.%m.%Y %H:%M:%S')
                            except ValueError:
                                # Если не удалось распарсить, просто добавляем время как есть
                                return dt.strftime('%d.%m.%Y') + ' ' + time_part
                    # Если время нет в строке, но with_time=True, все равно возвращаем только дату
                    return dt.strftime('%d.%m.%Y')
                except ValueError:
                    pass
            
            return str(date_str)
        except Exception as e:
            return str(date_str) if date_str else '—'
    
    # Регистрируем фильтр двумя способами для надежности
    app.jinja_env.filters['format_date'] = format_date_filter
    app.template_filter('format_date')(format_date_filter)

    def format_payment_type_filter(pt):
        """Переводит тип оплаты (cash, card, transfer) на русский."""
        if not pt:
            return '—'
        labels = {'cash': 'Наличные', 'card': 'Карта', 'transfer': 'Перевод'}
        return labels.get((pt or '').strip().lower(), pt)

    def format_payment_row_type_filter(p):
        """Тип для строки платежа: при kind=refund возвращает 'Возврат', иначе — перевод payment_type."""
        if not p:
            return '—'
        kind = (p.get('kind') if isinstance(p, dict) else getattr(p, 'kind', None)) or ''
        if str(kind).lower() == 'refund':
            return 'Возврат'
        pt = p.get('payment_type') if isinstance(p, dict) else getattr(p, 'payment_type', None)
        return format_payment_type_filter(pt)

    def format_payment_amount_filter(p):
        """Сумма платежа: для возвратов (kind=refund) — с минусом."""
        if not p:
            return '—'
        amt = float(p.get('amount', 0) if isinstance(p, dict) else getattr(p, 'amount', 0) or 0)
        kind = (p.get('kind') if isinstance(p, dict) else getattr(p, 'kind', None)) or ''
        prefix = '−' if str(kind).lower() == 'refund' else ''
        return f'{prefix}{amt:.2f} ₽'

    app.jinja_env.filters['format_payment_type'] = format_payment_type_filter
    app.jinja_env.filters['format_payment_row_type'] = format_payment_row_type_filter
    app.jinja_env.filters['format_payment_amount'] = format_payment_amount_filter

    from app.utils.dashboard_jinja_filters import (
        format_dashboard_avg_money_change,
        format_dashboard_count_change,
        format_dashboard_money_change,
    )

    app.jinja_env.filters['dashboard_money_delta'] = format_dashboard_money_change
    app.jinja_env.filters['dashboard_count_delta'] = format_dashboard_count_change
    app.jinja_env.filters['dashboard_avg_money_delta'] = format_dashboard_avg_money_change
    
    # Инициализация БД
    init_db()
    
    # Настройка логирования
    import logging
    from logging.handlers import RotatingFileHandler
    import os
    
    if not app.debug:
        # В продакшене логируем в файл
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler(
            app.config.get('LOG_FILE', 'app.log'),
            maxBytes=10240000,  # 10MB
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(getattr(logging, app.config.get('LOG_LEVEL', 'INFO')))
        app.logger.addHandler(file_handler)
        app.logger.setLevel(getattr(logging, app.config.get('LOG_LEVEL', 'INFO')))
        app.logger.info('Application startup')
    else:
        # В режиме разработки логируем в консоль
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        console_handler.setLevel(logging.DEBUG)
        app.logger.addHandler(console_handler)
        app.logger.setLevel(logging.DEBUG)
        app.logger.info('Application startup (DEBUG mode)')
    
    # Добавляем csrf_token в контекст шаблонов
    from flask_wtf.csrf import generate_csrf
    @app.context_processor
    def inject_csrf_token():
        return dict(csrf_token=lambda: generate_csrf())
    
    # Регистрация Blueprint'ов
    from app.routes.main import bp as main_bp
    from app.routes.orders import bp as orders_bp
    from app.routes.customers import bp as customers_bp
    from app.routes.api import bp as api_bp
    from app.routes.settings import bp as settings_bp
    from app.routes.warehouse import bp as warehouse_bp
    from app.routes.reports import bp as reports_bp
    from app.routes.action_logs import bp as action_logs_bp
    from app.routes.finance import bp as finance_bp
    from app.routes.shop import bp as shop_bp
    from app.routes.statuses import bp as statuses_bp
    from app.routes.statuses import bp_page as statuses_page_bp
    from app.routes.salary import bp as salary_bp
    from app.routes.salary import bp_page as salary_page_bp
    from app.routes.salary_dashboard import bp as salary_dashboard_bp, bp_api as salary_dashboard_api_bp
    from app.routes.masters import bp as masters_bp
    from app.routes.managers import bp as managers_bp
    from app.routes.employees import bp as employees_bp
    from app.routes.notifications import bp as notifications_bp
    from app.routes.comments import bp as comments_bp
    from app.routes.templates import bp as templates_bp
    from app.routes.search import bp as search_bp
    from app.routes.customer_portal import bp as customer_portal_bp
    from app.routes.staff_chat import bp as staff_chat_bp, init_staff_chat_socketio
    
    # Инициализируем limiter для blueprints
    from app.routes.main import init_limiter as init_main_limiter
    from app.routes.api import init_limiter as init_api_limiter
    from app.routes.settings import init_limiter as init_settings_limiter
    from app.routes.customer_portal import init_limiter as init_portal_limiter
    init_main_limiter(limiter)
    init_api_limiter(limiter)
    init_settings_limiter(limiter)
    init_portal_limiter(limiter)
    
    app.register_blueprint(main_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(customers_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(settings_bp, url_prefix='/api')
    app.register_blueprint(warehouse_bp)
    app.register_blueprint(reports_bp, url_prefix='/reports')
    app.register_blueprint(action_logs_bp)
    app.register_blueprint(finance_bp)
    app.register_blueprint(shop_bp)
    app.register_blueprint(statuses_bp)
    app.register_blueprint(statuses_page_bp)
    app.register_blueprint(salary_bp)
    app.register_blueprint(salary_page_bp)
    app.register_blueprint(salary_dashboard_bp)
    app.register_blueprint(salary_dashboard_api_bp)
    app.register_blueprint(masters_bp)
    app.register_blueprint(managers_bp)
    app.register_blueprint(employees_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(comments_bp)
    app.register_blueprint(templates_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(customer_portal_bp)
    app.register_blueprint(staff_chat_bp)

    if socketio is not None:
        try:
            init_staff_chat_socketio(socketio)
        except Exception as e:
            app.logger.error("Не удалось инициализировать websocket staff chat: %s", e, exc_info=True)
    
    # CSRF включён для state-changing endpoints.
    # Для JS запросов (fetch) токен добавляется автоматически в `templates/base.html` (X-CSRFToken).
    
    # Регистрация обработчиков ошибок
    from app.utils.error_handlers import register_error_handlers
    register_error_handlers(app)
    
    # Добавляем обработчик для логирования всех запросов (только в DEBUG)
    # С фильтрацией чувствительных данных
    if app.debug:
        @app.before_request
        def log_request_info():
            try:
                from flask import request
                # Фильтруем чувствительные данные из логов
                path = request.path
                # Не логируем пароли и токены
                if 'password' in request.form:
                    app.logger.debug(f'Request: {request.method} {path} [password filtered]')
                elif 'csrf_token' in request.form:
                    app.logger.debug(f'Request: {request.method} {path} [csrf_token filtered]')
                else:
                    app.logger.debug(f'Request: {request.method} {path}')
            except Exception:
                # Игнорируем ошибки логирования, чтобы не ломать приложение
                pass
    
    # Фильтрация чувствительных данных в логах ошибок
    import logging
    class SensitiveDataFilter(logging.Filter):
        """Фильтр для удаления чувствительных данных из логов."""
        def filter(self, record):
            if hasattr(record, 'msg'):
                msg = str(record.msg)
                # Заменяем пароли
                import re
                msg = re.sub(r'password["\']?\s*[:=]\s*["\']?[^"\'\s]+', 'password=***', msg, flags=re.IGNORECASE)
                msg = re.sub(r'password_hash["\']?\s*[:=]\s*["\']?[^"\'\s]+', 'password_hash=***', msg, flags=re.IGNORECASE)
                msg = re.sub(r'secret["\']?\s*[:=]\s*["\']?[^"\'\s]+', 'secret=***', msg, flags=re.IGNORECASE)
                msg = re.sub(r'api_key["\']?\s*[:=]\s*["\']?[^"\'\s]+', 'api_key=***', msg, flags=re.IGNORECASE)
                record.msg = msg
            return True
    
    # Применяем фильтр ко всем логгерам
    for handler in app.logger.handlers:
        handler.addFilter(SensitiveDataFilter())
    
    return app

