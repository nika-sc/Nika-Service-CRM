"""
Blueprint для главных страниц и аутентификации.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from flask_login import login_user, logout_user, current_user, login_required
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from functools import wraps
import time
import threading
from app.services.reference_service import ReferenceService
from app.services.user_service import UserService
from app.services.settings_service import SettingsService
from app.services.action_log_service import ActionLogService
from app.services.dashboard_service import DashboardService
from app.middleware.auth import User
from app.utils.exceptions import ValidationError, NotFoundError, DatabaseError
from app.utils.report_period import normalize_date_range
import sqlite3
import logging
import json
from urllib.parse import urlparse, urljoin
from email.utils import parseaddr
from app.database.connection import get_db_connection


def log_main_action(action_type: str, entity_type: str, entity_id: int = None, description: str = None, details: dict = None):
    """Логирует действие."""
    try:
        user_id = current_user.id if current_user.is_authenticated else None
        username = current_user.username if current_user.is_authenticated else None
        ActionLogService.log_action(
            user_id=user_id,
            username=username,
            action_type=action_type,
            entity_type=entity_type,
            entity_id=entity_id,
            description=description,
            details=details
        )
    except Exception as e:
        logging.warning(f"Не удалось записать лог действия: {e}")

bp = Blueprint('main', __name__)
logger = logging.getLogger(__name__)



# Инициализация limiter для этого blueprint
limiter = None


def init_limiter(app_limiter):
    """Инициализирует limiter для этого blueprint."""
    global limiter
    limiter = app_limiter

def rate_limit_if_available(limit_str):
    """Декоратор для rate limiting, если limiter доступен."""
    def decorator(f):
        if limiter:
            return limiter.limit(limit_str)(f)
        return f
    return decorator


# Блокировка по IP после N неверных попыток входа (защита от подбора паролей)
_LOGIN_FAILURE_LOCK = threading.Lock()
_LOGIN_FAILURES = {}  # ip -> {"count": int, "blocked_until": float (timestamp)}
LOGIN_MAX_ATTEMPTS = 3
LOGIN_BLOCK_MINUTES = 15


def _login_failure_blocked(ip: str) -> bool:
    """Проверяет, заблокирован ли IP из-за неверных попыток входа."""
    now = time.time()
    with _LOGIN_FAILURE_LOCK:
        _prune_login_failures(now)
        entry = _LOGIN_FAILURES.get(ip)
        if not entry:
            return False
        if entry["blocked_until"] and entry["blocked_until"] > now:
            return True
        return False


def _prune_login_failures(now: float) -> None:
    """Удаляет устаревшие записи (уже разблокированные)."""
    expired = [ip for ip, e in _LOGIN_FAILURES.items() if e.get("blocked_until") and e["blocked_until"] <= now]
    for ip in expired:
        del _LOGIN_FAILURES[ip]


def _record_login_failure(ip: str) -> None:
    """Увеличивает счётчик неудачных попыток; при 3+ — блокирует IP на LOGIN_BLOCK_MINUTES."""
    with _LOGIN_FAILURE_LOCK:
        entry = _LOGIN_FAILURES.get(ip)
        if not entry:
            entry = {"count": 0, "blocked_until": None}
            _LOGIN_FAILURES[ip] = entry
        entry["count"] += 1
        if entry["count"] >= LOGIN_MAX_ATTEMPTS:
            entry["blocked_until"] = time.time() + LOGIN_BLOCK_MINUTES * 60


def _clear_login_failures(ip: str) -> None:
    """Сбрасывает счётчик после успешного входа."""
    with _LOGIN_FAILURE_LOCK:
        _LOGIN_FAILURES.pop(ip, None)


def role_required(required_role: str):
    """
    Декоратор для проверки роли пользователя.
    
    Args:
        required_role: Требуемая роль (viewer, master, manager, admin)
        
    Usage:
        @bp.route('/admin')
        @login_required
        @role_required('admin')
        def admin_page():
            ...
    """
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Пожалуйста, войдите в систему.', 'error')
                return redirect(url_for('main.login'))
            
            # Проверяем роль пользователя
            user_role = getattr(current_user, 'role', 'viewer')
            if not UserService.check_role_permission(user_role, required_role):
                flash('У вас нет прав для доступа к этой странице.', 'error')
                return redirect(url_for('main.home'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def permission_required(permission: str):
    """
    Декоратор для проверки конкретного права пользователя.
    
    Args:
        permission: Имя права (например, 'create_orders', 'manage_warehouse')
        
    Usage:
        @bp.route('/warehouse')
        @login_required
        @permission_required('view_warehouse')
        def warehouse_page():
            ...
    """
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            is_api_request = '/api/' in request.path or request.path.startswith('/api')

            if not current_user.is_authenticated:
                if is_api_request:
                    return jsonify({'success': False, 'error': 'auth_required'}), 401
                flash('Пожалуйста, войдите в систему.', 'error')
                return redirect(url_for('main.login'))
            
            # Проверяем право пользователя
            if not UserService.check_permission(current_user.id, permission):
                if is_api_request:
                    return jsonify({
                        'success': False,
                        'error': 'forbidden',
                        'required_permission': permission
                    }), 403
                flash('У вас нет прав для доступа к этой странице.', 'error')
                return redirect(url_for('main.home'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def format_phone_display(phone):
    """Форматирует телефон для отображения."""
    if not phone:
        return ''
    phone = phone.replace('+', '').replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
    if len(phone) == 11 and phone.startswith('7'):
        return f"+7 ({phone[1:4]}) {phone[4:7]}-{phone[7:9]}-{phone[9:]}"
    return phone


def _is_safe_redirect_target(target: str) -> bool:
    """Проверяет, что redirect-цель указывает на текущий хост."""
    if not target:
        return False
    try:
        ref_url = urlparse(request.host_url)
        test_url = urlparse(urljoin(request.host_url, target))
        return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc
    except Exception:
        return False


@bp.route('/login', methods=['GET', 'POST'])
@rate_limit_if_available("5 per minute")
def login():
    """Страница входа в систему с защитой от brute-force."""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Введите имя пользователя и пароль', 'error')
            return render_template('auth/login.html')
        
        user_dict = UserService.get_user_by_username(username)
        if user_dict:
            current_hash = user_dict.get('password_hash')
            if not current_hash:
                logger.warning(f"Пользователь {username} не имеет хеша пароля")
                flash('Неверное имя пользователя или пароль', 'error')
                return render_template('auth/login.html')
            
            # Логируем формат хеша для диагностики
            hash_format = "werkzeug" if (current_hash.startswith('pbkdf2:') or 
                                        current_hash.startswith('scrypt:') or
                                        current_hash.startswith('argon2:')) else "SHA-256"
            logger.debug(f"Попытка входа пользователя {username}, формат хеша: {hash_format}")
            
            # Проверяем пароль (поддерживает старые SHA-256 и новые werkzeug хеши)
            password_valid = UserService.verify_password(password, current_hash)
            logger.debug(f"Результат проверки пароля для {username}: {password_valid}")
            
            if password_valid:
                # Если использовался старый хеш, перехешируем пароль
                # Проверяем, является ли хеш старым SHA-256 (64 символа hex)
                # Werkzeug хеши начинаются с pbkdf2:, scrypt: и т.д.
                is_old_hash = not (current_hash.startswith('pbkdf2:') or 
                                  current_hash.startswith('scrypt:') or
                                  current_hash.startswith('argon2:'))
                
                if is_old_hash:
                    logger.info(f"Перехеширование пароля для пользователя {username}")
                    UserService.rehash_password_if_needed(user_dict['id'], password, current_hash)
                
                user = User(user_dict)
                remember_me = request.form.get('remember_me') in ('1', 'on', 'true', 'True')
                login_user(user, remember=remember_me)
                UserService.update_user_last_login(user.id)
                flash(f'Добро пожаловать, {username}!', 'success')
                next_page = request.args.get('next')
                if not _is_safe_redirect_target(next_page):
                    next_page = url_for('main.home')
                return redirect(next_page)
        
        # Не раскрываем, существует ли пользователь (security best practice)
        flash('Неверное имя пользователя или пароль', 'error')
    
    return render_template('auth/login.html')


@bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """Выход из системы."""
    logout_user()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('main.login'))


@bp.route('/')
@login_required
def home():
    """Главная страница — дашборд с полным функционалом Dashboard."""
    # Период: по умолчанию сегодня
    preset = request.args.get('preset', 'today')
    date_from, date_to = normalize_date_range(
        request.args.get('date_from'),
        request.args.get('date_to'),
        default="today",
    )
    if date_from and date_to:
        preset = None  # custom range wins

    # Даты текущего периода (чтобы локальные виджеты тоже были в одном периоде)
    current_from, current_to, _, _ = DashboardService.get_period_dates(preset, date_from, date_to)
    
    total_orders = 0
    new_orders_count = 0
    in_progress_count = 0
    completed_count = 0
    closed_count = 0
    try:
        with get_db_connection(row_factory=sqlite3.Row) as conn:
            cursor = conn.cursor()

            # Статистика по статусам (созданные за период, только видимые заявки)
            cursor.execute('''
                SELECT os.code, COUNT(*) AS cnt 
                FROM orders AS o
                INNER JOIN order_statuses AS os ON os.id = o.status_id
                WHERE (o.hidden = 0 OR o.hidden IS NULL)
                  AND DATE(o.created_at) >= DATE(?)
                  AND DATE(o.created_at) <= DATE(?)
                GROUP BY os.code
            ''', (current_from, current_to))
            status_counts = cursor.fetchall()
            status_dict = {row['code']: row['cnt'] for row in status_counts if row['code']}
            
            # Подсчитываем статистику по статусам
            total_orders = sum(status_dict.values()) if status_dict else 0
            new_orders_count = status_dict.get('new', 0)
            in_progress_count = status_dict.get('in_progress', 0)
            completed_count = status_dict.get('completed', 0)
            closed_count = status_dict.get('closed', 0)

            # Заявки по дням (последние 14 дней внутри выбранного периода)
            cursor.execute('''
                SELECT DATE(created_at) AS day, COUNT(*) AS cnt
                FROM orders
                WHERE (hidden = 0 OR hidden IS NULL)
                  AND DATE(created_at) >= DATE(?)
                  AND DATE(created_at) <= DATE(?)
                GROUP BY day
                ORDER BY day DESC
                LIMIT 14
            ''', (current_from, current_to))
            orders_by_day_rows = cursor.fetchall()
            orders_by_day_rows = list(reversed(orders_by_day_rows))
            orders_by_day_labels = [row['day'] for row in orders_by_day_rows]
            orders_by_day_values = [row['cnt'] for row in orders_by_day_rows]

            # Топ-5 типов устройств (за период)
            cursor.execute('''
                SELECT 
                    COALESCE(dt.name, 'Другое') AS device_type_name,
                    COUNT(*) AS cnt
                FROM orders AS o
                JOIN devices AS d ON d.id = o.device_id
                LEFT JOIN device_types AS dt ON dt.id = d.device_type_id
                WHERE (o.hidden = 0 OR o.hidden IS NULL)
                  AND DATE(o.created_at) >= DATE(?)
                  AND DATE(o.created_at) <= DATE(?)
                GROUP BY device_type_name
                ORDER BY cnt DESC
                LIMIT 5
            ''', (current_from, current_to))
            device_type_rows = cursor.fetchall()
            device_type_labels = [row['device_type_name'] for row in device_type_rows]
            device_type_values = [row['cnt'] for row in device_type_rows]

            # Топ-5 менеджеров (за период)
            cursor.execute('''
                SELECT 
                    COALESCE(mgr.name, 'Без менеджера') AS manager_name,
                    COUNT(*) AS cnt
                FROM orders AS o
                LEFT JOIN managers AS mgr ON mgr.id = o.manager_id
                WHERE (o.hidden = 0 OR o.hidden IS NULL)
                  AND DATE(o.created_at) >= DATE(?)
                  AND DATE(o.created_at) <= DATE(?)
                GROUP BY manager_name
                ORDER BY cnt DESC
                LIMIT 5
            ''', (current_from, current_to))
            manager_rows = cursor.fetchall()
            manager_labels = [row['manager_name'] for row in manager_rows]
            manager_values = [row['cnt'] for row in manager_rows]

            # Последние 10 заявок (за период)
            cursor.execute('''
                SELECT 
                    o.id,
                    o.order_id,
                    o.customer_id,
                    o.device_id,
                    o.manager_id,
                    o.master_id,
                    c.name AS client_name,
                    o.created_at,
                    o.status_id,
                    os.code AS status,
                    os.name AS status_name,
                    os.color AS status_color,
                    c.phone,
                    COALESCE(dt.name, '—') AS device_type,
                    COALESCE(db.name, '—') AS device_brand,
                    COALESCE(mgr.name, '—') AS manager,
                    COALESCE(ms.name, '—') AS master
                FROM orders AS o
                JOIN customers AS c ON c.id = o.customer_id
                LEFT JOIN devices AS d ON d.id = o.device_id
                LEFT JOIN device_types AS dt ON dt.id = d.device_type_id
                LEFT JOIN device_brands AS db ON db.id = d.device_brand_id
                LEFT JOIN managers AS mgr ON mgr.id = o.manager_id
                LEFT JOIN masters AS ms ON ms.id = o.master_id
                LEFT JOIN order_statuses AS os ON os.id = o.status_id
                WHERE (o.hidden = 0 OR o.hidden IS NULL)
                  AND DATE(o.created_at) >= DATE(?)
                  AND DATE(o.created_at) <= DATE(?)
                ORDER BY o.created_at DESC
                LIMIT 10
            ''', (current_from, current_to))
            recent_orders_rows = cursor.fetchall()
            recent_orders = []
            for row in recent_orders_rows:
                data = dict(row)
                data['phone_display'] = format_phone_display(data.get('phone', ''))
                recent_orders.append(data)

        # Получаем статусы из БД (с кэшированием)
        order_statuses = ReferenceService.get_order_statuses()
        status_map = {str(s['code']): s for s in order_statuses}

        # Получаем данные сводного отчёта владельца (с фильтрами)
        try:
            dashboard_data = DashboardService.get_full_dashboard(
                preset=preset,
                date_from=date_from,
                date_to=date_to
            )
        except Exception as e:
            logger.warning(f"Не удалось получить данные dashboard: {e}")
            dashboard_data = {}
        
        # Пресеты для выбора периода
        period_presets = [
            ('today', 'Сегодня'),
            ('yesterday', 'Вчера'),
            ('last_7_days', 'Последние 7 дней'),
            ('last_30_days', 'Последние 30 дней'),
            ('current_month', 'Текущий месяц'),
            ('last_month', 'Прошлый месяц'),
            ('year_to_date', 'С начала года'),
        ]

        return render_template(
            'dashboard.html',
            total_orders=total_orders,
            new_orders_count=new_orders_count,
            in_progress_count=in_progress_count,
            completed_count=completed_count,
            closed_count=closed_count,
            recent_orders=recent_orders,
            orders_by_day_labels=orders_by_day_labels,
            orders_by_day_values=orders_by_day_values,
            device_type_labels=device_type_labels,
            device_type_values=device_type_values,
            manager_labels=manager_labels,
            manager_values=manager_values,
            order_statuses=order_statuses,
            status_map=status_map,
            dashboard=dashboard_data,
            preset=preset,
            date_from=date_from,
            date_to=date_to,
            period_presets=period_presets,
        )
    except sqlite3.Error as e:
        logger.error(f"Ошибка базы данных на главной странице: {e}", exc_info=True)
        flash('Ошибка базы данных. Пожалуйста, попробуйте позже.', 'error')
        return render_template('errors/500.html'), 500
    except Exception as e:
        logger.error(f"Неожиданная ошибка на главной странице: {e}", exc_info=True)
        flash('Произошла ошибка. Пожалуйста, попробуйте позже.', 'error')
        return render_template('errors/500.html'), 500


@bp.route('/notifications')
@login_required
def notifications_page():
    """Страница «Все уведомления» — список уведомлений текущего пользователя."""
    return render_template('notifications.html')


@bp.route('/settings/employees')
@login_required
@permission_required('manage_users')
def employees_page():
    """Страница управления сотрудниками."""
    return render_template('settings/employees.html')


@bp.route('/settings/user-permissions')
@login_required
@role_required('admin')
def user_permissions_page():
    """Страница управления правами пользователей (только для админов)."""
    return render_template('settings/user_permissions.html')


@bp.route('/settings', methods=['GET', 'POST'])
@login_required
@role_required('manager')
def settings():
    """Страница настроек."""
    # Инициализируем переменные по умолчанию
    device_types = []
    device_brands = []
    symptoms = []
    appearance_tags = []
    statuses = []
    services = []
    order_models = []
    success = False
    director_test_result = None
    settings = {}
    payment_method_settings = {'cash_label': 'Наличные', 'card_label': 'Карта', 'transfer_label': 'Перевод'}
    
    try:
        settings = SettingsService.get_general_settings()
        payment_method_settings = SettingsService.get_payment_method_settings()
        # Используем сервис справочников с кэшированием
        refs = ReferenceService.get_all_references()
        
        # Преобразуем словари в кортежи для совместимости с шаблоном
        # Шаблон ожидает: device_types/device_brands как (id, name)
        # symptoms/appearance_tags как (id, name, sort_order)
        device_types = [(dt['id'], dt['name']) for dt in refs.get('device_types', [])]
        device_brands = [(db['id'], db['name']) for db in refs.get('device_brands', [])]
        symptoms = [(s['id'], s['name'], s.get('sort_order', 0)) for s in refs.get('symptoms', [])]
        appearance_tags = [(at['id'], at['name'], at.get('sort_order', 0)) for at in refs.get('appearance_tags', [])]
        
        statuses = refs.get('order_statuses', [])
        services = refs.get('services', [])
        order_models = [(m['id'], m['name']) for m in refs.get('order_models', [])]
        
        # Получаем usage counts для всех справочников одним запросом
        usage_counts = ReferenceService.get_all_usage_counts()
    except Exception as e:
        logger.exception(f"Ошибка при загрузке страницы настроек: {e}")
        flash('Ошибка при загрузке данных настроек', 'error')
        # Пытаемся получить хотя бы настройки
        try:
            settings = SettingsService.get_general_settings()
            payment_method_settings = SettingsService.get_payment_method_settings()
            usage_counts = {'device_types': {}, 'device_brands': {}, 'symptoms': {}, 'appearance_tags': {}, 'services': {}}
        except Exception as e2:
            logger.error(f"Не удалось получить настройки: {e2}")
            settings = {}
            payment_method_settings = {'cash_label': 'Наличные', 'card_label': 'Карта', 'transfer_label': 'Перевод'}
            usage_counts = {'device_types': {}, 'device_brands': {}, 'symptoms': {}, 'appearance_tags': {}, 'services': {}}

    currency_options = [
        ('RUB', 'Российский рубль (RUB)'),
        ('USD', 'Доллар США (USD)'),
        ('EUR', 'Евро (EUR)'),
        ('UAH', 'Украинская гривна (UAH)'),
        ('MDL', 'Молдавский лей (MDL)'),
    ]
    country_options = [
        ('Россия', 'Россия'),
        ('Украина', 'Украина'),
        ('Молдова', 'Молдова'),
        ('Казахстан', 'Казахстан'),
        ('Беларусь', 'Беларусь'),
    ]

    if request.method == 'POST':
        try:
            def _is_valid_ascii_email(value: str) -> bool:
                _, email_addr = parseaddr((value or '').strip())
                email_addr = (email_addr or '').strip()
                if not email_addr or '@' not in email_addr:
                    return False
                try:
                    email_addr.encode('ascii')
                    return True
                except UnicodeEncodeError:
                    return False

            # Обработка общих настроек
            if 'org_name' in request.form:
                current_settings = SettingsService.get_general_settings()
                payload = dict(current_settings or {})
                payload.update({
                    'org_name': request.form.get('org_name', ''),
                    'phone': request.form.get('phone', ''),
                    'address': request.form.get('address', ''),
                    'inn': request.form.get('inn', ''),
                    'ogrn': request.form.get('ogrn', ''),
                    'logo_url': request.form.get('logo_url', ''),
                    'logo_max_width': int(request.form.get('logo_max_width') or 320),
                    'logo_max_height': int(request.form.get('logo_max_height') or 120),
                    'currency': request.form.get('currency', 'RUB'),
                    'country': request.form.get('country', 'Россия'),
                    'default_warranty_days': int(request.form.get('default_warranty_days') or 30),
                    'timezone_offset': int(request.form.get('timezone_offset') or 3),
                    'mail_server': request.form.get('mail_server', ''),
                    'mail_port': request.form.get('mail_port', ''),
                    'mail_use_tls': request.form.get('mail_use_tls') == 'on',
                    'mail_use_ssl': request.form.get('mail_use_ssl') == 'on',
                    'mail_username': request.form.get('mail_username', ''),
                    'mail_password': request.form.get('mail_password', ''),
                    'mail_default_sender': request.form.get('mail_default_sender', ''),
                    'mail_timeout': request.form.get('mail_timeout', ''),
                    'print_page_size': request.form.get('print_page_size', 'A4'),
                    'print_margin_mm': int(request.form.get('print_margin_mm') or 3),
                    'close_print_mode': request.form.get('close_print_mode', 'choice'),
                    'auto_email_order_accepted': request.form.get('auto_email_order_accepted') == 'on',
                    'auto_email_status_update': request.form.get('auto_email_status_update') == 'on',
                    'auto_email_order_ready': request.form.get('auto_email_order_ready') == 'on',
                    'auto_email_order_closed': request.form.get('auto_email_order_closed') == 'on',
                    'sms_enabled': request.form.get('sms_enabled') == 'on',
                    'telegram_enabled': request.form.get('telegram_enabled') == 'on',
                    'signature_name': request.form.get('signature_name', ''),
                    'signature_position': request.form.get('signature_position', ''),
                })
                SettingsService.save_general_settings(payload)
                # Сохраняем подписи способов оплаты, если блок присутствует в форме
                if 'payment_method_cash_label' in request.form or 'payment_methods_custom_json' in request.form:
                    import json
                    custom_json = request.form.get('payment_methods_custom_json', '[]')
                    try:
                        custom_methods = json.loads(custom_json) if custom_json else []
                    except Exception:
                        custom_methods = []
                    SettingsService.save_payment_method_settings(
                        request.form.get('payment_method_cash_label', 'Наличные'),
                        request.form.get('payment_method_transfer_label', 'Перевод'),
                        custom_methods=custom_methods,
                    )
                    payment_method_settings = SettingsService.get_payment_method_settings()
                
                # Сохраняем настройки НДС
                vat_enabled = request.form.get('vat_enabled') == 'on'
                vat_rate = float(request.form.get('vat_rate') or 0)
                SettingsService.save_vat_settings(vat_enabled, vat_rate)
                
                settings = SettingsService.get_general_settings()
                success = True
                log_main_action('update', 'general_settings', None,
                    f'Изменены общие настройки организации: {payload.get("org_name", "")}', payload)
                flash('Настройки успешно сохранены!', 'success')
            elif 'automation_settings' in request.form:
                current_settings = SettingsService.get_general_settings()
                payload = dict(current_settings or {})
                payload.update({
                    'close_print_mode': request.form.get('close_print_mode', 'choice'),
                    'auto_email_order_accepted': request.form.get('auto_email_order_accepted') == 'on',
                    'auto_email_status_update': request.form.get('auto_email_status_update') == 'on',
                    'auto_email_order_ready': request.form.get('auto_email_order_ready') == 'on',
                    'auto_email_order_closed': request.form.get('auto_email_order_closed') == 'on',
                    'sms_enabled': request.form.get('sms_enabled') == 'on',
                    'telegram_enabled': request.form.get('telegram_enabled') == 'on',
                    'signature_name': request.form.get('signature_name', ''),
                    'signature_position': request.form.get('signature_position', ''),
                })
                SettingsService.save_general_settings(payload)
                settings = SettingsService.get_general_settings()
                success = True
                log_main_action(
                    'update',
                    'general_settings',
                    None,
                    'Изменены настройки автоматизаций и каналов',
                    {
                        'close_print_mode': payload.get('close_print_mode'),
                        'auto_email_order_accepted': payload.get('auto_email_order_accepted'),
                        'auto_email_status_update': payload.get('auto_email_status_update'),
                        'auto_email_order_ready': payload.get('auto_email_order_ready'),
                        'auto_email_order_closed': payload.get('auto_email_order_closed'),
                    }
                )
                flash('Автоматизации и каналы успешно сохранены!', 'success')
            elif 'director_notifications_test' in request.form:
                current_settings = SettingsService.get_general_settings()
                recipient = (request.form.get('director_email') or current_settings.get('director_email') or '').strip()
                if not _is_valid_ascii_email(recipient):
                    flash('Тест не отправлен: укажите корректный Email директора (ASCII).', 'error')
                    success = False
                    director_test_result = {'ok': False, 'message': 'Последняя проверка: email директора невалиден.'}
                else:
                    from app.services.notification_service import NotificationService
                    sent, err_msg = NotificationService.send_director_test_email(recipient)
                    success = bool(sent)
                    if sent:
                        flash(f'Тестовое письмо отправлено на {recipient}.', 'success')
                        director_test_result = {'ok': True, 'message': f'Последняя проверка: письмо отправлено на {recipient}.'}
                    else:
                        flash(f'Не удалось отправить тестовое письмо директору: {err_msg or "неизвестная ошибка"}', 'error')
                        director_test_result = {'ok': False, 'message': f'Последняя проверка: ошибка отправки на {recipient}. {err_msg or ""}'.strip()}
            elif 'client_email_test' in request.form:
                current_settings = SettingsService.get_general_settings()
                recipient = (request.form.get('director_email') or current_settings.get('director_email') or 'alex@smelkoff.ru').strip()
                if not _is_valid_ascii_email(recipient):
                    flash('Тест писем клиенту не отправлен: укажите корректный Email (ASCII).', 'error')
                    success = False
                else:
                    from app.services.notification_service import NotificationService
                    from app.database.connection import get_db_connection
                    with get_db_connection() as conn:
                        cur = conn.cursor()
                        cur.execute("SELECT id FROM orders WHERE customer_id IS NOT NULL ORDER BY id DESC LIMIT 1")
                        row = cur.fetchone()
                    if not row:
                        flash('Нет заявок с клиентом в базе. Невозможно отправить тестовые письма клиенту.', 'error')
                        success = False
                    else:
                        order_id = row[0]
                        templates = ('order_accepted', 'order_status_update', 'order_ready', 'order_closed_thanks')
                        ok = 0
                        for template_type in templates:
                            if NotificationService.send_customer_order_email(order_id, template_type, override_recipient=recipient):
                                ok += 1
                        if ok:
                            flash(f'Отправлено {ok} из {len(templates)} тестовых писем клиента (с данными заявки #{order_id}) на {recipient}.', 'success')
                        else:
                            flash(f'Не удалось отправить тестовые письма клиенту. Проверьте SMTP и логи.', 'error')
                        success = bool(ok)
            elif 'director_notifications_settings' in request.form:
                current_settings = SettingsService.get_general_settings()
                payload = dict(current_settings or {})
                director_email = (request.form.get('director_email') or '').strip()
                if director_email and not _is_valid_ascii_email(director_email):
                    flash('Email директора должен быть корректным адресом в формате user@domain.com (ASCII).', 'error')
                    success = False
                    settings = SettingsService.get_general_settings()
                else:
                    payload.update({
                        'director_email': director_email,
                        'auto_email_director_order_accepted': request.form.get('auto_email_director_order_accepted') == 'on',
                        'auto_email_director_order_closed': request.form.get('auto_email_director_order_closed') == 'on',
                    })
                    SettingsService.save_general_settings(payload)
                    settings = SettingsService.get_general_settings()
                    success = True
                    log_main_action(
                        'update',
                        'general_settings',
                        None,
                        'Изменены настройки уведомлений директору',
                        {
                            'director_email': payload.get('director_email'),
                            'auto_email_director_order_accepted': payload.get('auto_email_director_order_accepted'),
                            'auto_email_director_order_closed': payload.get('auto_email_director_order_closed'),
                        }
                    )
                    flash('Настройки уведомлений директору сохранены!', 'success')
            elif 'payment_methods_settings' in request.form:
                import json
                custom_json = request.form.get('payment_methods_custom_json', '[]')
                try:
                    custom_methods = json.loads(custom_json) if custom_json else []
                except Exception:
                    custom_methods = []
                SettingsService.save_payment_method_settings(
                    request.form.get('payment_method_cash_label', 'Наличные'),
                    request.form.get('payment_method_transfer_label', 'Перевод'),
                    custom_methods=custom_methods,
                )
                payment_method_settings = SettingsService.get_payment_method_settings()
                success = True
                flash('Названия способов оплаты сохранены!', 'success')
            # Обработка шаблонов печати
            elif 'print_template_type' in request.form:
                template_type = request.form.get('print_template_type')
                html_content = request.form.get('print_template_html', '')
                if SettingsService.save_print_template(template_type, html_content):
                    log_main_action('update', 'print_template', None,
                        f'Изменён шаблон печати: {template_type}', {'template_type': template_type})
                    flash('Шаблон печати успешно сохранен!', 'success')
                    success = True
                else:
                    flash('Ошибка при сохранении шаблона печати', 'error')
                    success = False
            # Обработка шаблонов писем
            elif 'email_template_type' in request.form:
                template_type = request.form.get('email_template_type')
                html_content = request.form.get('email_template_html', '')
                if SettingsService.save_email_template(template_type, html_content):
                    log_main_action(
                        'update',
                        'email_template',
                        None,
                        f'Изменён шаблон email: {template_type}',
                        {'template_type': template_type}
                    )
                    flash('Email-шаблон успешно сохранен!', 'success')
                    success = True
                else:
                    flash('Ошибка при сохранении email-шаблона', 'error')
                    success = False
        except Exception as e:
            logger.exception(f"Ошибка при сохранении настроек: {e}")
            flash('Ошибка при сохранении настроек', 'error')
            success = False

    # Получаем шаблоны печати
    try:
        customer_template = SettingsService.get_print_template_fresh('customer')
        sales_receipt_template = SettingsService.get_print_template_fresh('sales_receipt')
        work_act_template = SettingsService.get_print_template_fresh('work_act')

        # Автосоздание шаблонов "Товарный чек" и "Акт" по образцу квитанции клиента
        customer_html = ((customer_template or {}).get('html_content') or '').strip()
        if not customer_html:
            customer_html = """
<h3 style="margin:0 0 8px 0;">Квитанция по заявке ##ORDER_NUMBER##</h3>
<p style="margin:0 0 6px 0;">Клиент: ##CLIENT_NAME##, телефон: ##CLIENT_PHONE1##</p>
<p style="margin:0 0 6px 0;">Устройство: ##701809f9-23dc-4346-aff4-0aef32523aef## / ##b6a8f943-e1b0-46e8-a321-b25fcfaf6976##</p>
<p style="margin:0 0 6px 0;">Неисправность: ##f93f4677-15b5-4e57-97e7-a345cb5b0e21##</p>
<p style="margin:0;">Оплачено: <strong>##TOTAL_PAID##</strong></p>
""".strip()

        if not sales_receipt_template or not (sales_receipt_template.get('html_content') or '').strip():
            sales_html = """<table style="border-width: 0; width: 100%;" border="1">
<tbody>
<tr>
<td style="width: 68%; border-width: 0;">
<h1>Товарный чек</h1>
Продажа от <strong>##CREATED_AT##</strong></td>
<td style="border-width: 0; text-align: right; vertical-align: middle; width: 32%;">
<h1><img src="##COMPANY_LOGO_URL##" alt="" style="##COMPANY_LOGO_STYLE##"></h1>
<p style="text-align: left;">##COMPANY_NAME##, ##branch.address##</p>
<p style="text-align: left;"><strong>##branch.phone##, ##COMPANY_REQUISITES##</strong></p>
<p>&nbsp;</p>
</td>
</tr>
</tbody>
</table>
<table border="1">
<thead>
<tr>
<td><strong>№</strong></td>
<td style="width: 100%;"><strong>Позиция</strong></td>
<td><strong>Артикул</strong></td>
<td style="text-align: right;"><strong>Гарантия, дн.</strong></td>
<td style="text-align: right;"><strong>Цена, ##CURRENCY##</strong></td>
<td style="text-align: right;"><strong>Скидка, ##CURRENCY##</strong></td>
<td style="text-align: right;"><strong>Количество</strong></td>
<td style="text-align: right;"><strong>Сумма, ##CURRENCY##</strong></td>
</tr>
</thead>
<tbody>
<tr data-for="ITEMS">
<td>##INDEX##</td>
<td style="width: 100%;">##ITEM_NAME##</td>
<td>##ITEM_SKU##</td>
<td style="text-align: right;">##ITEM_WARRANTY##</td>
<td style="text-align: right;">##ITEM_PRICE##</td>
<td style="text-align: right;">##ITEM_DISCOUNT##</td>
<td style="text-align: right;">##ITEM_QUANTITY##</td>
<td style="text-align: right;">##ITEM_SUM##</td>
</tr>
<tr>
<td style="text-align: right;" colspan="7"><strong>Сумма, ##CURRENCY##</strong></td>
<td style="text-align: right;"><strong>##TOTAL_ITEMS##</strong></td>
</tr>
</tbody>
</table>
<p>&nbsp;</p>
<table style="border-width: 0;" border="1">
<tbody>
<tr>
<td style="width: 50%; border-width: 0;">
<p><strong>Продавец</strong>: __________________ ##EMPLOYEE_NAME##</p>
<p><br><strong>Дата</strong>: ##DATE_TODAY## ##TIME_NOW##</p>
</td>
</tr>
</tbody>
</table>"""
            SettingsService.save_print_template('sales_receipt', sales_html)
            sales_receipt_template = SettingsService.get_print_template_fresh('sales_receipt')

        if not work_act_template or not (work_act_template.get('html_content') or '').strip():
            act_html = """<table style="border-width: 0; width: 100%;" border="1">
<tbody>
<tr>
<td style="width: 68%; border-width: 0;">
<h1>Акт выполненных работ</h1>
<p>№ заказа <strong>##ORDER_NUMBER##</strong> от <strong>##CREATED_AT##</strong></p>
<p>Настоящий акт составлен о том, что Исполнителем выполнены нижеперечисленные работы (оказаны услуги), оборудование (товар) передано Заказчику.</p>
</td>
<td style="border-width: 0; text-align: right; vertical-align: top; width: 32%;">
<p style="text-align: left;"><strong>##COMPANY_NAME##</strong><br>##branch.address##<br>##branch.phone##<br>##COMPANY_REQUISITES##</p>
<p>&nbsp;</p>
</td>
</tr>
</tbody>
</table>
<table border="1">
<tbody>
<tr>
<td style="width: 22%;"><strong>Заказчик</strong></td>
<td>##CLIENT_NAME##, ##CLIENT_PHONE1##</td>
</tr>
<tr>
<td><strong>Исполнитель</strong></td>
<td>##COMPANY_NAME##</td>
</tr>
</tbody>
</table>
<table border="1">
<thead>
<tr>
<td><strong>№</strong></td>
<td style="width: 100%;"><strong>Наименование работ (услуг) / товара</strong></td>
<td><strong>Артикул</strong></td>
<td style="text-align: right;"><strong>Гарантия, дн.</strong></td>
<td style="text-align: right;"><strong>Цена, ##CURRENCY##</strong></td>
<td style="text-align: right;"><strong>Скидка, ##CURRENCY##</strong></td>
<td style="text-align: right;"><strong>Кол-во</strong></td>
<td style="text-align: right;"><strong>Сумма, ##CURRENCY##</strong></td>
</tr>
</thead>
<tbody>
<tr data-for="ITEMS">
<td>##INDEX##</td>
<td style="width: 100%;">##ITEM_NAME##</td>
<td>##ITEM_SKU##</td>
<td style="text-align: right;">##ITEM_WARRANTY##</td>
<td style="text-align: right;">##ITEM_PRICE##</td>
<td style="text-align: right;">##ITEM_DISCOUNT##</td>
<td style="text-align: right;">##ITEM_QUANTITY##</td>
<td style="text-align: right;">##ITEM_SUM##</td>
</tr>
<tr>
<td style="text-align: right;" colspan="7"><strong>Итого:</strong></td>
<td style="text-align: right;"><strong>##TOTAL_ITEMS## ##CURRENCY##</strong></td>
</tr>
</tbody>
</table>
<p><strong>Работы выполнены в полном объёме, в срок и с надлежащим качеством. Заказчик претензий по объёму, срокам и качеству не имеет. Стоимость работ (услуг) и товаров Заказчиком принята.</strong></p>
<table style="border-width: 0;" border="1">
<tbody>
<tr>
<td style="width: 50%; border-width: 0;">
<p><strong>Исполнитель</strong>: __________________ / ##EMPLOYEE_NAME##</p>
</td>
<td style="width: 50%; border-width: 0;">
<p><strong>Заказчик</strong>: __________________ / ##CLIENT_NAME##</p>
</td>
</tr>
<tr>
<td colspan="2" style="border-width: 0;"><strong>Дата</strong>: ##DATE_TODAY## ##TIME_NOW##</td>
</tr>
</tbody>
</table>"""
            SettingsService.save_print_template('work_act', act_html)
            work_act_template = SettingsService.get_print_template_fresh('work_act')
    except Exception as e:
        logger.error(f"Ошибка при получении шаблона печати: {e}")
        customer_template = None
        sales_receipt_template = None
        work_act_template = None

    # Получаем шаблоны email
    try:
        email_templates = {
            'order_accepted': SettingsService.get_email_template('order_accepted'),
            'order_status_update': SettingsService.get_email_template('order_status_update'),
            'order_ready': SettingsService.get_email_template('order_ready'),
            'order_closed_thanks': SettingsService.get_email_template('order_closed_thanks'),
        }
        director_email_templates = {
            'director_order_accepted': SettingsService.get_email_template('director_order_accepted'),
            'director_order_closed_report': SettingsService.get_email_template('director_order_closed_report'),
        }

        # Автосоздание email-шаблонов, если они еще не заполнены в настройках
        from app.services.notification_service import NotificationService
        for template_type in (
            'order_accepted',
            'order_status_update',
            'order_ready',
            'order_closed_thanks',
            'director_order_accepted',
            'director_order_closed_report',
        ):
            item = email_templates.get(template_type)
            if item is None:
                item = director_email_templates.get(template_type)
            has_content = bool((item or {}).get('html_content', '').strip()) if item else False
            if not has_content:
                SettingsService.save_email_template(
                    template_type,
                    NotificationService._get_default_email_template(template_type)
                )
                if template_type in email_templates:
                    email_templates[template_type] = SettingsService.get_email_template(template_type)
                else:
                    director_email_templates[template_type] = SettingsService.get_email_template(template_type)
    except Exception as e:
        logger.error(f"Ошибка при получении email-шаблонов: {e}")
        email_templates = {
            'order_accepted': None,
            'order_status_update': None,
            'order_ready': None,
            'order_closed_thanks': None,
        }
        director_email_templates = {
            'director_order_accepted': None,
            'director_order_closed_report': None,
        }

    # Получаем настройки НДС
    try:
        vat_settings = SettingsService.get_vat_settings()
    except Exception as e:
        logger.error(f"Ошибка при получении настроек НДС: {e}")
        vat_settings = {'vat_enabled': False, 'vat_rate': 20.0}

    return render_template(
        'settings.html',
        settings=settings,
        vat_settings=vat_settings,
        statuses=statuses,
        device_types=device_types,
        device_brands=device_brands,
        symptoms=symptoms,
        appearance_tags=appearance_tags,
        services=services,
        order_models=order_models,
        currency_options=currency_options,
        country_options=country_options,
        customer_template=customer_template,
        sales_receipt_template=sales_receipt_template,
        work_act_template=work_act_template,
        email_templates=email_templates,
        director_email_templates=director_email_templates,
        director_test_result=director_test_result,
        payment_method_settings=payment_method_settings,
        success=success,
        usage_counts=usage_counts,
    )


# ==================== API для управления пользователями, правами и ролями ====================

@bp.route('/api/settings/users', methods=['GET'])
@login_required
@permission_required('manage_users')
def api_get_users():
    """Получает список всех пользователей."""
    try:
        include_inactive = request.args.get('include_inactive', 'false').lower() == 'true'
        role_filter = request.args.get('role', None)  # Новый параметр для фильтрации по роли

        users = UserService.get_all_users(include_inactive=include_inactive, role=role_filter)
        # Убираем password_hash из ответа
        for user in users:
            user.pop('password_hash', None)
        return jsonify({'success': True, 'users': users})
    except Exception as e:
        logger.error(f"Ошибка при получении списка пользователей: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/settings/users', methods=['POST'])
@login_required
@permission_required('manage_users')
def api_create_user():
    """Создает нового пользователя."""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '')
        role = data.get('role', 'viewer')
        is_active = data.get('is_active', 1)
        
        if not username:
            return jsonify({'success': False, 'error': 'Имя пользователя обязательно'}), 400
        
        if not password:
            return jsonify({'success': False, 'error': 'Пароль обязателен'}), 400
        
        user_id = UserService.create_user(username, password, role)
        
        # Устанавливаем is_active, если нужно
        if is_active == 0:
            UserService.update_user(user_id, is_active=0)
        
        return jsonify({'success': True, 'user_id': user_id})
    except ValidationError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Ошибка при создании пользователя: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/settings/users/<int:user_id>', methods=['GET'])
@login_required
@permission_required('manage_users')
def api_get_user(user_id):
    """Получает данные одного пользователя."""
    try:
        user = UserService.get_user_by_id(user_id, include_inactive=True)
        if not user:
            return jsonify({'success': False, 'error': 'Пользователь не найден'}), 404
        
        # Убираем password_hash из ответа
        user.pop('password_hash', None)
        return jsonify({'success': True, 'user': user})
    except Exception as e:
        logger.error(f"Ошибка при получении пользователя: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/settings/users/<int:user_id>', methods=['PATCH'])
@login_required
@permission_required('manage_users')
def api_update_user(user_id):
    """Обновляет данные пользователя."""
    try:
        data = request.get_json()
        username = data.get('username')
        role = data.get('role')
        is_active = data.get('is_active')
        
        UserService.update_user(
            user_id,
            username=username,
            role=role,
            is_active=is_active
        )
        
        return jsonify({'success': True})
    except ValidationError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Ошибка при обновлении пользователя: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/settings/users/<int:user_id>/change-password', methods=['POST'])
@login_required
@permission_required('manage_users')
def api_change_password(user_id):
    """Изменяет пароль пользователя."""
    try:
        data = request.get_json()
        new_password = data.get('password', '')
        
        if not new_password:
            return jsonify({'success': False, 'error': 'Пароль обязателен'}), 400
        
        UserService.change_password(user_id, new_password)
        
        return jsonify({'success': True})
    except ValidationError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Ошибка при смене пароля: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/settings/users/<int:user_id>', methods=['DELETE'])
@login_required
@permission_required('manage_users')
def api_delete_user(user_id):
    """Удаляет пользователя."""
    try:
        # Проверяем, является ли это первый администратор
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Получаем минимальный ID среди всех администраторов
            cursor.execute("SELECT MIN(id) FROM users WHERE role = 'admin' AND is_active = 1")
            first_admin_id = cursor.fetchone()[0]
            
            if first_admin_id and user_id == first_admin_id:
                return jsonify({'success': False, 'error': 'Нельзя удалить первого администратора системы'}), 400
        
        UserService.delete_user(user_id)
        return jsonify({'success': True})
    except ValidationError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Ошибка при удалении пользователя: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/settings/permissions', methods=['GET'])
@login_required
@permission_required('manage_users')
def api_get_permissions():
    """Получает список всех прав."""
    try:
        permissions = UserService.get_all_permissions()
        return jsonify({'success': True, 'permissions': permissions})
    except Exception as e:
        logger.error(f"Ошибка при получении списка прав: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/settings/permissions/<int:permission_id>', methods=['PATCH'])
@login_required
@permission_required('manage_users')
def api_update_permission(permission_id):
    """Обновляет описание права."""
    try:
        data = request.get_json()
        description = data.get('description', '')
        
        UserService.update_permission(permission_id, description)
        
        return jsonify({'success': True})
    except ValidationError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Ошибка при обновлении права: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/settings/roles', methods=['GET'])
@login_required
@permission_required('manage_users')
def api_get_roles():
    """Получает список всех ролей с их правами."""
    try:
        roles = UserService.get_all_roles()
        return jsonify({'success': True, 'roles': roles})
    except Exception as e:
        logger.error(f"Ошибка при получении списка ролей: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/settings/roles', methods=['POST'])
@login_required
@permission_required('manage_users')
def api_create_role():
    """Создает новую роль."""
    try:
        data = request.get_json()
        role_name = data.get('role', '').strip()
        permission_ids = data.get('permission_ids', [])
        
        if not role_name:
            return jsonify({'success': False, 'error': 'Название роли обязательно'}), 400
        
        UserService.create_role(role_name, permission_ids)
        
        return jsonify({'success': True})
    except ValidationError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Ошибка при создании роли: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/settings/roles/<role>', methods=['GET'])
@login_required
@permission_required('manage_users')
def api_get_role(role):
    """Получает данные роли с её правами."""
    try:
        all_roles = UserService.get_all_roles()
        role_data = next((r for r in all_roles if r['role'] == role), None)
        if not role_data:
            return jsonify({'success': False, 'error': 'Роль не найдена'}), 404
        return jsonify({'success': True, 'role': role_data})
    except Exception as e:
        logger.error(f"Ошибка при получении роли {role}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/settings/roles/<role>', methods=['PATCH'])
@login_required
@permission_required('manage_users')
def api_update_role(role):
    """Обновляет права роли."""
    try:
        data = request.get_json()
        permission_ids = data.get('permission_ids', [])
        
        UserService.update_role(role, permission_ids)
        
        return jsonify({'success': True})
    except ValidationError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Ошибка при обновлении роли: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/settings/roles/<role>', methods=['DELETE'])
@login_required
@permission_required('manage_users')
def api_delete_role(role):
    """Удаляет роль."""
    try:
        UserService.delete_role(role)
        return jsonify({'success': True})
    except ValidationError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Ошибка при удалении роли: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

