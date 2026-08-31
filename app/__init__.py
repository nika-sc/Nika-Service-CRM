"""
Инициализация Flask приложения.
"""
import ipaddress
import logging
import socket
from fnmatch import fnmatch
import time

from flask import Flask, redirect, url_for, Response, send_from_directory, request, jsonify, g
from flask_login import LoginManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
from datetime import datetime, timezone
import os

from app.config import Config
from app.database.connection import init_db
from app.middleware.auth import setup_auth


def _is_private_or_local_host(host: str) -> bool:
    """True if host is a private/loopback/link-local IP (IPv4 or IPv6)."""
    try:
        addr = ipaddress.ip_address(host)
    except ValueError:
        return False
    return bool(addr.is_private or addr.is_loopback or addr.is_link_local)


def _hostname_from_host_header(host_header: str) -> str:
    """
    Extract hostname from an HTTP Host header.
    Supports IPv4 (`1.2.3.4:5000`), IPv6 (`[fe80::1]:5000`), bare names.
    """
    host = (host_header or '').strip().lower()
    if not host:
        return ''
    if host.startswith('['):
        end = host.find(']')
        if end != -1:
            return host[1:end]
        return ''
    # IPv4 / hostname with optional :port (exactly one colon → port)
    if host.count(':') == 1:
        return host.split(':', 1)[0].strip()
    return host


def _socketio_origin_allowed(
    origin: str,
    *,
    static_origins: set[str],
    app_port: int,
    allow_private: bool,
) -> bool:
    """Allow listed origins, or (with @private) http(s)://<private-ip>:<app_port>."""
    if not origin:
        return False
    origin_norm = origin.strip().rstrip('/')
    if origin_norm in static_origins or origin in static_origins:
        return True
    if not allow_private:
        return False
    try:
        from urllib.parse import urlparse
        parsed = urlparse(origin)
    except Exception:
        return False
    if (parsed.scheme or '').lower() not in ('http', 'https'):
        return False
    hostname = (parsed.hostname or '').lower()
    if not hostname or not _is_private_or_local_host(hostname):
        return False
    port = parsed.port
    if port is None:
        port = 443 if parsed.scheme == 'https' else 80
    return int(port) == int(app_port)


def _local_ipv4_addresses() -> list:
    """Best-effort list of non-loopback IPv4 addresses on this machine."""
    found = set()
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET, socket.SOCK_STREAM):
            ip = info[4][0]
            if ip and not ip.startswith('127.'):
                found.add(ip)
    except OSError:
        pass
    try:
        # Connect to a public address (no packets sent) to discover the preferred LAN IP.
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(('8.8.8.8', 80))
            ip = sock.getsockname()[0]
            if ip and not ip.startswith('127.'):
                found.add(ip)
    except OSError:
        pass
    return sorted(found)


def _expand_socketio_cors_origins(raw_origins: str, app_port: int) -> list | str:
    """
    Parse SOCKETIO_CORS_ALLOWED_ORIGINS.
    If TRUSTED_HOSTS-style token '@private' appears, append http://<local-ip>:<port>
    and http://<hostname>:<port> origins (no wildcard '*').
    """
    raw = (raw_origins or '').strip()
    if not raw:
        return []
    if raw == '*':
        return '*'
    items = [item.strip() for item in raw.split(',') if item.strip()]
    allow_private = any(item.lower() == '@private' for item in items)
    origins = [item for item in items if item.lower() != '@private']
    if allow_private:
        scheme_port = int(app_port or 5000)
        for ip in _local_ipv4_addresses():
            origins.append(f'http://{ip}:{scheme_port}')
        hostname = (socket.gethostname() or '').strip()
        if hostname:
            origins.append(f'http://{hostname}:{scheme_port}')
            origins.append(f'http://{hostname}.local:{scheme_port}')
        # Deduplicate while preserving order
        seen = set()
        deduped = []
        for origin in origins:
            key = origin.lower()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(origin)
        origins = deduped
    return origins

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

    # Flask/Werkzeug валидирует Host по TRUSTED_HOSTS и не понимает токен @private.
    # Список правил держим в HOST_ALLOWLIST; встроенную проверку Flask отключаем —
    # иначе LAN IP (Sandbox Hyper-V 172.x, DHCP и т.п.) получают HTML 400
    # «Host is not trusted» до нашего before_request.
    #
    # Читаем TRUSTED_HOSTS из os.environ заново: class-body Config может
    # зафиксировать дефолт, если модуль импортировали до dotenv (или ключ с BOM).
    def _parse_trusted_hosts_env() -> list:
        raw = (os.environ.get('TRUSTED_HOSTS') or os.environ.get('\ufeffTRUSTED_HOSTS') or '').strip()
        if not raw:
            return list(app.config.get('TRUSTED_HOSTS') or [])
        return [h.strip().lower() for h in raw.split(',') if h.strip()]

    _trusted_hosts = _parse_trusted_hosts_env()
    app.config['HOST_ALLOWLIST'] = _trusted_hosts
    app.config['TRUSTED_HOSTS'] = None

    from app.config import ProductionConfig
    _is_production = (
        config_class == ProductionConfig
        or (
            isinstance(config_class, type)
            and issubclass(config_class, ProductionConfig)
            and not getattr(config_class, 'TESTING', False)
        )
    )
    if _is_production and not _trusted_hosts:
        raise ValueError(
            "TRUSTED_HOSTS обязателен в production: укажите домен(ы) CRM через запятую, "
            "не оставляйте список пустым."
        )

    def _host_allowed(host_header: str) -> bool:
        trusted = app.config.get('HOST_ALLOWLIST') or []
        if not trusted:
            # Dev/test: пустой список не режет трафик. Production выше уже не стартует.
            if _is_production:
                return False
            return True
        host = _hostname_from_host_header(host_header)
        if not host:
            return False
        allow_private = any(
            (pattern or '').strip().lower() == '@private'
            for pattern in trusted
        )
        if allow_private and _is_private_or_local_host(host):
            return True
        for pattern in trusted:
            p = pattern.strip().lower()
            if not p or p == '@private':
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
            from app.utils.request_ip import client_ip
            from app.utils.write_api_limit import allow_write
            if not allow_write(client_ip(), limit):
                return jsonify({'success': False, 'error': 'too_many_requests'}), 429

    @app.before_request
    def _assign_csp_nonce():
        import secrets
        from flask import g
        g.csp_nonce = secrets.token_urlsafe(16)

    @app.before_request
    def _portal_idle_session_timeout():
        """Сброс сессии личного кабинета после PERMANENT_SESSION_LIFETIME неактивности."""
        from flask import session, redirect, url_for

        if not session.get('portal_customer_id'):
            return None
        if (request.path or '').startswith('/static/'):
            return None

        now = time.time()
        last_active = session.get('_portal_last_active')
        lifetime = app.permanent_session_lifetime.total_seconds()
        if last_active and lifetime > 0 and (now - float(last_active)) > lifetime:
            session.pop('portal_customer_id', None)
            session.pop('portal_customer_name', None)
            session.pop('_portal_last_active', None)
            path = request.path or ''
            if path.startswith('/portal/api/'):
                return jsonify({
                    'success': False,
                    'error': 'session_expired',
                    'error_type': 'auth',
                }), 401
            if path.startswith('/portal'):
                return redirect(url_for('customer_portal.portal_login'))
            return None
        session['_portal_last_active'] = now
        session.permanent = True
        return None

    @app.before_request
    def _staff_idle_session_timeout():
        """Сброс staff-сессии после PERMANENT_SESSION_LIFETIME неактивности."""
        from flask import session, redirect, url_for, flash
        from flask_login import current_user, logout_user

        if not current_user.is_authenticated:
            return None
        if session.get('portal_customer_id'):
            return None
        if (request.path or '').startswith('/static/'):
            return None

        now = time.time()
        last_active = session.get('_staff_last_active')
        lifetime = app.permanent_session_lifetime.total_seconds()
        if last_active and lifetime > 0 and (now - float(last_active)) > lifetime:
            logout_user()
            session.clear()
            path = request.path or ''
            if path.startswith('/api/') or path.startswith('/portal/api/'):
                return jsonify({
                    'success': False,
                    'error': 'session_expired',
                    'error_type': 'auth',
                }), 401
            flash('Сессия истекла из-за неактивности. Войдите снова.', 'info')
            return redirect(url_for('main.login'))
        session['_staff_last_active'] = now
        session.permanent = True
        return None

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

    # robots.txt / sitemap — при PUBLIC_LANDING разрешаем индексацию только лендинга
    @app.route('/robots.txt')
    def robots_txt():
        if app.config.get('PUBLIC_LANDING'):
            root = (app.config.get('PUBLIC_LANDING_CANONICAL') or '').rstrip('/')
            if not root:
                root = (request.url_root or '').rstrip('/')
            body = "\n".join([
                "User-agent: *",
                "Allow: /$",
                "Allow: /docs$",
                "Allow: /docs/",
                "Allow: /blog$",
                "Allow: /blog/",
                "Allow: /static/",
                "Allow: /sitemap.xml",
                "Allow: /sitemap-images.xml",
                "Allow: /favicon.ico",
                "Disallow: /new",
                "Disallow: /login",
                "Disallow: /logout",
                "Disallow: /portal",
                "Disallow: /api",
                "Disallow: /reports",
                "Disallow: /warehouse",
                "Disallow: /finance",
                "Disallow: /shop",
                "Disallow: /salary",
                "Disallow: /settings",
                "Disallow: /clients",
                "Disallow: /all_orders",
                "Disallow: /add_order",
                "Disallow: /order/",
                "Disallow: /device/",
                "Disallow: /notifications",
                "Disallow: /staff-chat",
                f"Sitemap: {root}/sitemap.xml",
                f"Sitemap: {root}/sitemap-images.xml",
                "",
            ])
            return Response(body, mimetype="text/plain")
        return Response(
            "User-agent: *\nDisallow: /\n",
            mimetype="text/plain",
        )

    @app.route('/sitemap.xml')
    def sitemap_xml():
        if not app.config.get('PUBLIC_LANDING'):
            return Response('Not Found', status=404, mimetype='text/plain')
        root = (app.config.get('PUBLIC_LANDING_CANONICAL') or '').rstrip('/')
        if not root:
            root = (request.url_root or '').rstrip('/')
        lastmod = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        image_url = f"{root}/static/marketing/og-landing.jpg"

        def url_entry(path: str, priority: str, changefreq: str = "weekly", extra: str = "") -> str:
            loc = f"{root}{path}" if path != "/" else f"{root}/"
            return (
                "  <url>\n"
                f"    <loc>{loc}</loc>\n"
                f"    <lastmod>{lastmod}</lastmod>\n"
                f"    <changefreq>{changefreq}</changefreq>\n"
                f"    <priority>{priority}</priority>\n"
                f'    <xhtml:link rel="alternate" hreflang="ru-RU" href="{loc}" />\n'
                f'    <xhtml:link rel="alternate" hreflang="ru" href="{loc}" />\n'
                f'    <xhtml:link rel="alternate" hreflang="x-default" href="{loc}" />\n'
                f"{extra}"
                "  </url>\n"
            )

        home_extra = (
            "    <image:image>\n"
            f"      <image:loc>{image_url}</image:loc>\n"
            "      <image:title>Nika CRM — бесплатная CRM для сервисных центров</image:title>\n"
            "    </image:image>\n"
        )
        blog_xml = ""
        try:
            from app.routes.public_blog import blog_sitemap_paths as _blog_paths
            for path in _blog_paths():
                pri = "0.8" if path == "/blog" else "0.65"
                cf = "weekly" if path == "/blog" else "monthly"
                blog_xml += url_entry(path, pri, changefreq=cf)
        except Exception:
            blog_xml = ""

        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n'
            '        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1"\n'
            '        xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
            f'{url_entry("/", "1.0", extra=home_extra)}'
            f'{url_entry("/docs", "0.9")}'
            f'{url_entry("/docs/walkthrough", "0.85")}'
            f'{url_entry("/docs/guide", "0.85")}'
            f'{url_entry("/docs/about", "0.7", changefreq="monthly")}'
            f'{blog_xml}'
            '</urlset>\n'
        )
        return Response(xml, mimetype='application/xml')

    @app.route('/sitemap-images.xml')
    def sitemap_images_xml():
        if not app.config.get('PUBLIC_LANDING'):
            return Response('Not Found', status=404, mimetype='text/plain')
        root = (app.config.get('PUBLIC_LANDING_CANONICAL') or '').rstrip('/')
        if not root:
            root = (request.url_root or '').rstrip('/')
        titles = [
            "Главная страница с отчетами",
            "Личный кабинет пользователя 2",
            "Личный кабинет пользователя 3",
            "Личный кабинет пользователя 4",
            "Личный кабинет пользователя 5",
            "Личный кабинет пользователя",
            "Магазин с продажами",
            "Раздел Зарплата по сотрудникам",
            "Раздел касса с операциями за день",
            "Раздел касса",
            "Раздел клиенты с поиском и сортировкой",
            "Раздел настройки",
            "Раздел отчеты",
            "Светлая тема",
            "Склад с разделами",
            "Страница с заявками: закрепление, поиск, фильтры и выставление статуса",
            "Темная тема",
        ]
        walkthrough = [
            ("01-login.png", "Вход в демо Nika CRM"),
            ("02-dashboard.png", "Дашборд после входа"),
            ("03-add-order.png", "Форма новой заявки"),
            ("04-order-detail.png", "Карточка заявки"),
            ("05-add-service.png", "Добавление услуги"),
            ("06-add-part.png", "Добавление товара"),
            ("07-order-items.png", "Товары и услуги на заявке"),
            ("08-add-payment.png", "Модал добавления оплаты"),
            ("09-order-payments.png", "Платежи на заявке"),
            ("10-change-status.png", "Смена статуса"),
            ("11-close-order.png", "Закрытие заявки"),
            ("12-print-modal.png", "Печать документов"),
            ("13-salary-dashboard.png", "Дашборд зарплаты"),
            ("14-salary-accruals.png", "Начисления сотрудника"),
            ("15-salary-payout.png", "Регистрация выплаты"),
            ("16-salary-payments-list.png", "Список выплат"),
            ("17-finance-cash.png", "Касса"),
            ("18-cash-manual.png", "Ручной приход"),
            ("19-report-day.png", "Сводка дня"),
            ("20-report-cash.png", "Отчёт кассы"),
            ("21-shop.png", "Магазин"),
            ("22-purchases.png", "Закупки"),
            ("23-staff-chat.png", "Чат сотрудников"),
        ]
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"',
            '        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">',
        ]
        for idx, title in enumerate(titles, start=1):
            image_url = f"{root}/static/marketing/screenshots/screenshot-{idx:02d}.jpg"
            lines.extend([
                "  <url>",
                f"    <loc>{root}/#screenshots</loc>",
                "    <image:image>",
                f"      <image:loc>{image_url}</image:loc>",
                f"      <image:title>{title}</image:title>",
                "    </image:image>",
                "  </url>",
            ])
        for fname, title in walkthrough:
            image_url = f"{root}/docs/assets/walkthrough/{fname}"
            lines.extend([
                "  <url>",
                f"    <loc>{root}/docs/walkthrough</loc>",
                "    <image:image>",
                f"      <image:loc>{image_url}</image:loc>",
                f"      <image:title>{title}</image:title>",
                "    </image:image>",
                "  </url>",
            ])
        lines.append("</urlset>")
        lines.append("")
        return Response("\n".join(lines), mimetype='application/xml')

    @app.after_request
    def _set_security_headers(response):
        # Защита от clickjacking, MIME-sniffing, лишней утечки referrer и API features
        response.headers.setdefault('X-Frame-Options', 'DENY')
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        # Глобально запрещаем индексацию; исключение — SEO-лендинг (g.allow_search_indexing).
        if getattr(g, 'allow_search_indexing', False):
            response.headers['X-Robots-Tag'] = 'index, follow'
        else:
            response.headers.setdefault(
                'X-Robots-Tag',
                'noindex, nofollow, noarchive, nosnippet, noimageindex',
            )
        response.headers.setdefault('Permissions-Policy', 'geolocation=(), camera=(), microphone=()')
        response.headers.setdefault('Cross-Origin-Opener-Policy', 'same-origin')
        response.headers.setdefault('Cross-Origin-Resource-Policy', 'same-site')
        response.headers.setdefault('X-Permitted-Cross-Domain-Policies', 'none')

        nonce = getattr(g, 'csp_nonce', None) or ''
        csp_report_uri = app.config.get('CSP_REPORT_URI')
        enforce_prefixes = app.config.get('CSP_ENFORCE_PATH_PREFIXES') or []
        force_enforce_on_path = any((request.path or '').startswith(prefix) for prefix in enforce_prefixes)
        strict_prefixes = app.config.get('CSP_STRICT_ENFORCE_PREFIXES') or []
        force_strict = any((request.path or '').startswith(prefix) for prefix in strict_prefixes)
        nonce_mode = (app.config.get('CSP_NONCE_MODE') or 'off').strip().lower()

        def _legacy_csp_parts():
            parts = [
                "default-src 'self'",
                "base-uri 'self'",
                "object-src 'none'",
                "frame-ancestors 'none'",
                "img-src 'self' data: https:",
                "font-src 'self' data:",
                "style-src 'self' 'unsafe-inline'",
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
                "connect-src 'self' ws: wss: https:",
            ]
            if csp_report_uri:
                parts.append(f"report-uri {csp_report_uri}")
            return parts

        def _strict_csp_parts():
            n = nonce
            parts = [
                "default-src 'self'",
                "base-uri 'self'",
                "object-src 'none'",
                "frame-ancestors 'none'",
                "frame-src 'self'",
                "worker-src 'self'",
                "img-src 'self' data: https:",
                "font-src 'self' data:",
                f"style-src 'self' 'nonce-{n}'",
                f"script-src 'self' 'nonce-{n}'",
                "script-src-attr 'none'",
                "style-src-attr 'unsafe-inline'",
                "connect-src 'self' ws: wss: https:",
            ]
            if csp_report_uri:
                parts.append(f"report-uri {csp_report_uri}")
            return parts

        legacy_value = '; '.join(_legacy_csp_parts())
        strict_value = '; '.join(_strict_csp_parts()) if nonce else legacy_value

        if nonce_mode == 'enforce':
            response.headers.setdefault('Content-Security-Policy', strict_value)
        elif nonce_mode == 'report':
            response.headers.setdefault('Content-Security-Policy-Report-Only', strict_value)
            if force_strict:
                response.headers.setdefault('Content-Security-Policy', strict_value)
            elif force_enforce_on_path or not app.config.get('CSP_REPORT_ONLY', True):
                response.headers.setdefault('Content-Security-Policy', legacy_value)
        else:
            if app.config.get('CSP_REPORT_ONLY', True):
                response.headers.setdefault('Content-Security-Policy-Report-Only', legacy_value)
            if force_strict:
                response.headers.setdefault('Content-Security-Policy', strict_value)
            elif force_enforce_on_path or not app.config.get('CSP_REPORT_ONLY', True):
                response.headers.setdefault('Content-Security-Policy', legacy_value)
        # Включаем HSTS только при HTTPS
        if app.config.get('SESSION_COOKIE_SECURE'):
            response.headers.setdefault('Strict-Transport-Security', 'max-age=31536000; includeSubDomains')
        # Чувствительные страницы/ответы не кэшируем браузером
        p = request.path or ''
        if p.startswith('/login') or p.startswith('/portal/login') or p.startswith('/portal/set-password') or p.startswith('/api/'):
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
        # Если в HOST_ALLOWLIST / TRUSTED_HOSTS есть @private — расширяем CORS локальными IP,
        # даже если SOCKETIO_CORS_ALLOWED_ORIGINS их явно не перечисляет.
        trusted_hosts = app.config.get('HOST_ALLOWLIST') or app.config.get('TRUSTED_HOSTS') or []
        allow_private_hosts = any((h or '').strip().lower() == '@private' for h in trusted_hosts)
        if allow_private_hosts:
            if raw_origins and '@private' not in raw_origins.lower():
                raw_origins = raw_origins.rstrip(',') + ',@private'
            elif not raw_origins:
                raw_origins = 'http://localhost:5000,http://127.0.0.1:5000,@private'
        app_port = int(os.environ.get('APP_PORT', '5000') or 5000)
        cors_origins = _expand_socketio_cors_origins(raw_origins, app_port)
        # @private: callable CORS so DHCP / Sandbox IP changes work without restart.
        # Static list alone only covers IPs known at process start.
        if allow_private_hosts and cors_origins != '*':
            static_origins = {
                str(item).strip().rstrip('/').lower()
                for item in (cors_origins or [])
                if str(item).strip()
            }

            def _cors_allowed_origin(origin, *args, **kwargs):
                return _socketio_origin_allowed(
                    origin or '',
                    static_origins=static_origins,
                    app_port=app_port,
                    allow_private=True,
                )

            cors_for_socketio = _cors_allowed_origin
        else:
            cors_for_socketio = cors_origins
        socketio_kwargs = {
            'async_mode': app.config.get('SOCKETIO_ASYNC_MODE', 'threading'),
            'cors_allowed_origins': cors_for_socketio,
        }
        redis_url = (app.config.get('REDIS_URL') or '').strip()
        if redis_url:
            # Общая шина событий между несколькими gunicorn workers
            socketio_kwargs['message_queue'] = redis_url
            socketio_kwargs['channel'] = 'nikacrm-socketio'
        if not _is_production:
            # Werkzeug dev server: websocket upgrade → 500 write() before start_response
            socketio_kwargs['allow_upgrades'] = False
        socketio.init_app(app, **socketio_kwargs)
    
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
            "csp_nonce": lambda: getattr(g, "csp_nonce", "") or "",
        }

    @app.context_processor
    def inject_locale():
        """Tenant money symbol and phone prefix for templates (defaults: ₽ / 7)."""
        try:
            from app.utils.locale_fmt import get_money_symbol, get_phone_prefix

            symbol = get_money_symbol() or "₽"
            prefix = get_phone_prefix() or "7"
        except Exception:
            symbol = "₽"
            prefix = "7"
        return {
            "money_symbol": symbol,
            "money_icon_char": (symbol[:1] if symbol else "₽"),
            "phone_prefix": prefix,
            "phone_prefix_plus": f"+{prefix}",
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
        try:
            from app.utils.locale_fmt import get_money_symbol
            symbol = get_money_symbol()
        except Exception:
            symbol = '₽'
        return f'{prefix}{amt:.2f} {symbol}'

    app.jinja_env.filters['format_payment_type'] = format_payment_type_filter
    app.jinja_env.filters['format_payment_row_type'] = format_payment_row_type_filter
    app.jinja_env.filters['format_payment_amount'] = format_payment_amount_filter

    def money_words_filter(amount):
        from app.utils.money_words import amount_to_words_rub
        return amount_to_words_rub(amount)

    app.jinja_env.filters['money_words'] = money_words_filter

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
            maxBytes=int(os.environ.get('LOG_MAX_BYTES', '10240000')),
            backupCount=int(os.environ.get('LOG_BACKUP_COUNT', '30'))
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

    @app.context_processor
    def inject_demo_visitor_stats():
        """Флаг и счётчик онлайн для демо-баннера/чипа (только при DEMO_VISITOR_STATS)."""
        enabled = bool(app.config.get("DEMO_VISITOR_STATS"))
        ctx = {
            "demo_visitor_stats_enabled": enabled,
            "demo_online_count": 0,
        }
        if not enabled:
            return ctx
        try:
            from flask_login import current_user
            from app.services.demo_visitor_service import DemoVisitorService
            ctx["demo_online_count"] = DemoVisitorService.online_count()
            # Админский чип в шапке
            role = (getattr(current_user, "role", None) or "").strip().lower() if getattr(current_user, "is_authenticated", False) else ""
            ctx["demo_visitor_stats_admin"] = role == "admin"
        except Exception:
            pass
        return ctx
    
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
    from app.routes.notifications import bp as notifications_bp, init_notifications_socketio
    from app.routes.comments import bp as comments_bp
    from app.routes.order_diagnostics import bp as order_diagnostics_bp
    from app.routes.templates import bp as templates_bp
    from app.routes.search import bp as search_bp
    from app.routes.customer_portal import bp as customer_portal_bp
    from app.routes.staff_chat import bp as staff_chat_bp, init_staff_chat_socketio
    from app.routes.demo_visitors import bp as demo_visitors_bp
    from app.routes.public_docs import bp as public_docs_bp
    from app.routes.public_blog import bp as public_blog_bp
    from app.routes.invoices import bp as invoices_bp, inn_bp as inn_lookup_bp, register_invoice_static_guard
    
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
    app.register_blueprint(order_diagnostics_bp)
    app.register_blueprint(templates_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(customer_portal_bp)
    app.register_blueprint(staff_chat_bp)
    app.register_blueprint(demo_visitors_bp)
    app.register_blueprint(public_docs_bp)
    app.register_blueprint(public_blog_bp)
    app.register_blueprint(invoices_bp)
    register_invoice_static_guard(app)
    app.register_blueprint(inn_lookup_bp)

    if socketio is not None:
        try:
            init_staff_chat_socketio(socketio)
        except Exception as e:
            app.logger.error("Не удалось инициализировать websocket staff chat: %s", e, exc_info=True)
        try:
            init_notifications_socketio(socketio)
        except Exception as e:
            app.logger.error("Не удалось инициализировать websocket уведомлений: %s", e, exc_info=True)
    
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

