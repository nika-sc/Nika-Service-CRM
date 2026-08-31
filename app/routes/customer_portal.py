"""
Blueprint для публичного личного кабинета клиента.
"""
from flask import Blueprint, request, render_template, session, redirect, url_for, jsonify, send_file
from functools import wraps
from flask_login import current_user, logout_user
from app.services.customer_portal_service import CustomerPortalService
from app.services.customer_service import CustomerService
from app.services.order_service import OrderService
from app.services.device_service import DeviceService
from app.utils.exceptions import ValidationError, NotFoundError
from app.utils import login_lockout
from app.utils.login_lockout import user_lockout_message
import logging
import time

logger = logging.getLogger(__name__)

bp = Blueprint('customer_portal', __name__, url_prefix='/portal')

# Инициализация limiter для этого blueprint
limiter = None

def init_limiter(app_limiter):
    """Инициализирует limiter для этого blueprint."""
    global limiter
    limiter = app_limiter

def rate_limit_if_available(limit_str, methods=None):
    """
    Декоратор для rate limiting, который работает только если limiter инициализирован.
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Проверяем limiter во время выполнения, а не во время декорирования.
            if limiter:
                if methods and request.method not in methods:
                    return f(*args, **kwargs)
                return limiter.limit(limit_str)(f)(*args, **kwargs)
            return f(*args, **kwargs)
        return wrapper
    return decorator


def login_required(f):
    """Portal API: only a client portal session (staff cookie is not enough)."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if session.get('portal_customer_id'):
            return f(*args, **kwargs)
        return jsonify({'success': False, 'error': 'Не авторизован'}), 401
    return wrapper


def _portal_client_ip() -> str:
    from app.utils.request_ip import client_ip
    return client_ip()


def _portal_login_guard_key(phone: str) -> str:
    return f"{_portal_client_ip()}|{(phone or '').strip()}"


def _is_portal_login_locked(key: str) -> bool:
    return login_lockout.is_locked('portal', key)


def _mask_portal_phone(phone: str) -> str:
    digits = "".join(ch for ch in (phone or "") if ch.isdigit())
    if len(digits) <= 4:
        return digits or "?"
    return f"***{digits[-4:]}"


def _audit_portal_login_failure(phone: str, *, locked: bool) -> None:
    try:
        from app.services.action_log_service import ActionLogService

        mask = _mask_portal_phone(phone)
        ActionLogService.log_action(
            user_id=None,
            username=None,
            action_type="login_lockout" if locked else "login_failed",
            entity_type="portal_auth",
            description=(
                f"Lockout portal ({mask})"
                if locked
                else f"Неудачный вход portal ({mask})"
            ),
            details={
                "ip": _portal_client_ip(),
                "phone_mask": mask,
            },
        )
    except Exception as exc:
        logger.debug("portal login audit log failed: %s", exc)


def _register_portal_login_failure(key: str, phone: str = ""):
    locked = login_lockout.register_failure('portal', key)
    _audit_portal_login_failure(phone, locked=locked)
    logger.warning("AUTH_FAIL ip=%s kind=portal", _portal_client_ip())
    return locked


def _reset_portal_login_guard(key: str):
    login_lockout.clear('portal', key)


def _audit_portal_login_success(customer_id, phone: str) -> None:
    try:
        from app.services.action_log_service import ActionLogService

        mask = _mask_portal_phone(phone)
        ActionLogService.log_action(
            user_id=None,
            username=None,
            action_type="login_success",
            entity_type="portal_auth",
            entity_id=int(customer_id) if customer_id is not None else None,
            description=f"Успешный вход portal ({mask})",
            details={
                "ip": _portal_client_ip(),
                "phone_mask": mask,
                "customer_id": customer_id,
            },
        )
    except Exception as exc:
        logger.debug("portal login success audit failed: %s", exc)
    logger.info("AUTH_OK ip=%s kind=portal phone=%s", _portal_client_ip(), _mask_portal_phone(phone))




@bp.route('/login', methods=['GET', 'POST'])
# Первый вход может включать несколько POST (логин + смена пароля),
# поэтому повышаем лимит, чтобы избежать ложных 429.
@rate_limit_if_available("20 per minute", methods=("POST",))
@rate_limit_if_available("120 per hour", methods=("POST",))
def portal_login():
    """Вход в личный кабинет."""
    if request.method == 'POST':
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        from app.utils.validators import normalize_phone
        normalized_phone = normalize_phone(phone)
        login_key = _portal_login_guard_key(normalized_phone or phone)

        if _is_portal_login_locked(login_key):
            return render_template(
                'portal/login.html',
                error=user_lockout_message('portal', login_key),
                phone=phone,
            )
        new_password = request.form.get('new_password', '').strip()
        new_password_confirm = request.form.get('new_password_confirm', '').strip()
        change_password = request.form.get('change_password') == 'true'
        
        if not phone or not password:
            return render_template('portal/login.html', error='Введите телефон и пароль', phone=phone)
        
        if not normalized_phone or len(normalized_phone) < 10:
            return render_template('portal/login.html', error='Неверные данные для входа', phone=phone)

        from app.utils.validators import password_eligible_for_verify, password_meets_policy
        if not password_eligible_for_verify(password):
            _register_portal_login_failure(login_key, normalized_phone or phone)
            return render_template('portal/login.html', error='Неверные данные для входа', phone=phone)
        
        # Аутентификация по паролю
        customer_data = CustomerPortalService.authenticate_by_password(phone, password)
        
        if customer_data:
            # Staff remember-me must not survive a portal login (logout before session.clear).
            if getattr(current_user, 'is_authenticated', False):
                logout_user()
            session.clear()
            # Если требуется смена пароля
            if change_password and customer_data.get('needs_password_change'):
                from app.utils.validators import password_meets_policy, PASSWORD_MAX_LEN
                if not password_meets_policy(new_password):
                    err = (
                        'Пароль слишком длинный'
                        if len(new_password or '') > PASSWORD_MAX_LEN
                        else 'Новый пароль должен быть не менее 6 символов'
                    )
                    return render_template('portal/login.html', 
                                         error=err,
                                         needs_password_change=True,
                                         phone=phone)
                if new_password != new_password_confirm:
                    return render_template('portal/login.html',
                                         error='Пароли не совпадают',
                                         needs_password_change=True,
                                         phone=phone)
                
                # Устанавливаем новый пароль (без сброса флага, так как клиент сам меняет)
                # set_portal_password с reset_change_flag=False уже устанавливает флаг
                if CustomerPortalService.set_portal_password(
                    customer_data['customer_id'], 
                    new_password, 
                    reset_change_flag=False
                ):
                    session['portal_customer_id'] = customer_data['customer_id']
                    session['portal_customer_name'] = customer_data['name']
                    session.permanent = True
                    session['_portal_last_active'] = time.time()
                    _reset_portal_login_guard(login_key)
            _audit_portal_login_success(customer_data['customer_id'], normalized_phone or phone)
                    return redirect(url_for('customer_portal.portal_dashboard'))
                else:
                    return render_template('portal/login.html', 
                                         error='Ошибка при смене пароля',
                                         needs_password_change=True,
                                         phone=phone)
            
            # Обычный вход
            if customer_data.get('needs_password_change'):
                # Первый вход - требуем смену пароля
                return render_template('portal/login.html', 
                                     needs_password_change=True,
                                     phone=phone)
            
            session['portal_customer_id'] = customer_data['customer_id']
            session['portal_customer_name'] = customer_data['name']
            session.permanent = True
            session['_portal_last_active'] = time.time()
            _reset_portal_login_guard(login_key)
            _audit_portal_login_success(customer_data['customer_id'], normalized_phone or phone)
            return redirect(url_for('customer_portal.portal_dashboard'))
        else:
            _register_portal_login_failure(login_key, normalized_phone or phone)
            return render_template('portal/login.html', error='Неверные данные для входа', phone=phone)

    prefill = (request.args.get('phone') or '').strip()[:32]
    staff_hint = bool(getattr(current_user, 'is_authenticated', False))
    return render_template(
        'portal/login.html',
        phone=prefill,
        staff_hint=staff_hint,
    )


@bp.route('/set-password', methods=['GET', 'POST'])
@rate_limit_if_available("10 per minute")
@rate_limit_if_available("30 per hour")
def portal_set_password():
    """Задать пароль ЛК по одноразовой ссылке из письма (без текущего пароля)."""
    token = (request.values.get('token') or '').strip()
    if not token or len(token) > 200:
        return render_template(
            'portal/set_password.html',
            error='Ссылка недействительна или устарела.',
        ), 400
    info = CustomerPortalService.validate_token(token)
    if not info:
        return render_template(
            'portal/set_password.html',
            error='Ссылка недействительна или устарела. Попросите сервис выслать новую.',
        ), 400
    if request.method == 'GET':
        return render_template(
            'portal/set_password.html',
            token=token,
            name=info.get('name') or '',
        )
    password = request.form.get('password', '')
    confirm = request.form.get('password_confirm', '')
    from app.utils.validators import password_meets_policy, PASSWORD_MAX_LEN
    if not password_meets_policy(password):
        err = (
            'Пароль слишком длинный.'
            if len(password or '') > PASSWORD_MAX_LEN
            else 'Пароль должен быть не менее 6 символов.'
        )
        return render_template(
            'portal/set_password.html',
            token=token,
            name=info.get('name') or '',
            error=err,
        )
    if password != confirm:
        return render_template(
            'portal/set_password.html',
            token=token,
            name=info.get('name') or '',
            error='Пароли не совпадают.',
        )
    if CustomerPortalService.set_portal_password(
        info['customer_id'], password, reset_change_flag=False
    ):
        CustomerPortalService.revoke_token(token)
        return render_template(
            'portal/set_password.html',
            success=True,
            phone=info.get('phone') or '',
        )
    return render_template(
        'portal/set_password.html',
        token=token,
        name=info.get('name') or '',
        error='Не удалось сохранить пароль. Попробуйте ещё раз.',
    )


@bp.route('/logout', methods=['POST'])
def portal_logout():
    """Выход из личного кабинета."""
    session.pop('portal_customer_id', None)
    session.pop('portal_customer_name', None)
    session.pop('_portal_last_active', None)
    return redirect(url_for('customer_portal.portal_login'))


@bp.route('', methods=['GET'])
@bp.route('/dashboard', methods=['GET'])
@rate_limit_if_available("60 per minute")
def portal_dashboard():
    """Дашборд клиента: заявки, история платежей."""
    customer_id = session.get('portal_customer_id')
    if not customer_id:
        return redirect(url_for('customer_portal.portal_login'))
    
    try:
        customer = CustomerService.get_customer(customer_id)
        orders = CustomerService.get_customer_orders(customer_id, limit=50)
        
        # История платежей по всем заявкам
        payments = []
        order_uuid_map = {o['id']: o.get('order_id', str(o['id'])) for o in orders}
        for order in orders:
            for p in OrderService.get_order_payments(order['id']):
                pp = dict(p)
                pp['order_uuid'] = order_uuid_map.get(p.get('order_id'), str(p.get('order_id', '')))
                payments.append(pp)
        payments.sort(key=lambda x: (x.get('payment_date') or '', x.get('created_at') or ''), reverse=True)
        
        # Предоплата/переплата по заявкам (без депозитов)
        wallet_balance, _ = _get_prepayment_overpayment(customer_id)
        ready_orders = [o for o in orders if _is_ready_for_pickup(o)]
        org = _portal_org_card()

        return render_template('portal/dashboard.html',
                             customer=customer,
                             orders=orders,
                             payments=payments,
                             wallet_balance=wallet_balance,
                             ready_orders=ready_orders,
                             org=org)
    except Exception as e:
        logger.error(f"Ошибка при загрузке дашборда портала: {e}")
        return render_template(
            'portal/dashboard.html',
            customer=None,
            orders=[],
            payments=[],
            wallet_balance=0.0,
            ready_orders=[],
            org=_portal_org_card(),
            error='Ошибка загрузки данных'
        )


def _portal_public_order(order_data: dict) -> dict:
    """Поля заявки для ЛК: без пароля устройства и staff-комментариев."""
    drop = {
        "password",
        "device_password",
        "comment",
        "manager_id",
        "master_id",
        "prepayment_method",
        "manager_name",
        "master_name",
    }
    return {k: v for k, v in (order_data or {}).items() if k not in drop}


_PORTAL_LINE_DROP = frozenset({
    "purchase_price",
    "cost_price",
    "executor_id",
    "executor_username",
    "executor_user_id",
    "base_price",
    "discount_type",
    "discount_value",
    "part_id",
    "service_id",
    "stock_quantity",
    "category",
    "part_number",
    "salary_rule_type",
    "salary_rule_value",
})


def sanitize_portal_order_lines(items):
    """Убирает закупочные цены и исполнителей из позиций заявки для ЛК."""
    out = []
    for it in items or []:
        if not isinstance(it, dict):
            continue
        out.append({k: v for k, v in it.items() if k not in _PORTAL_LINE_DROP})
    return out


def _is_ready_for_pickup(order: dict) -> bool:
    if order.get("is_final"):
        return False
    code = str(order.get("status_code") or order.get("status") or "").lower()
    name = str(order.get("status_name") or "").lower()
    return ("ready" in code) or ("готов" in name)


def _portal_org_card():
    try:
        from app.services.settings_service import SettingsService
        s = SettingsService.get_general_settings() or {}
        return {
            "org_name": (s.get("org_name") or "").strip(),
            "phone": (s.get("phone") or "").strip(),
            "address": (s.get("address") or "").strip(),
        }
    except Exception:
        return {"org_name": "", "phone": "", "address": ""}


@bp.route('/api/order/<int:order_id>', methods=['GET'])
@login_required
@rate_limit_if_available("120 per minute")
def portal_api_order(order_id):
    """
    API: данные заявки для модального окна (без комментариев и чата).
    Доступно только для заявок текущего клиента.
    """
    customer_id = session.get('portal_customer_id')
    if not customer_id:
        return jsonify({'success': False, 'error': 'Не авторизован'}), 401
    try:
        full = OrderService.get_order_full_data(order_id)
        order_data = full.get('order') or {}
        if order_data.get('customer_id') != customer_id:
            return jsonify({'success': False, 'error': 'Доступ запрещён'}), 403
        order_public = _portal_public_order(order_data)
        files = []
        try:
            from app.services.order_diagnostics_service import OrderDiagnosticsService
            files = OrderDiagnosticsService.get_payload(order_data.get('id') or order_id).get('files') or []
        except Exception:
            files = []
        out = {
            'order': order_public,
            'device': full.get('device'),
            'services': sanitize_portal_order_lines(full.get('services', [])),
            'parts': sanitize_portal_order_lines(full.get('parts', [])),
            'payments': full.get('payments', []),
            'totals': full.get('totals', {}),
            'diagnostics_files': files,
        }
        # Сериализуем даты
        def _serialize(obj):
            if obj is None:
                return None
            if isinstance(obj, dict):
                return {k: _serialize(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [_serialize(x) for x in obj]
            if hasattr(obj, 'isoformat'):
                return obj.isoformat()
            return obj
        return jsonify({'success': True, 'data': _serialize(out)})
    except NotFoundError:
        return jsonify({'success': False, 'error': 'Заявка не найдена'}), 404
    except Exception as e:
        logger.warning(f"portal api order {order_id}: {e}")
        return jsonify({'success': False, 'error': 'Ошибка загрузки данных'}), 500


@bp.route('/api/order/<int:order_id>/file/<int:file_id>', methods=['GET'])
@login_required
@rate_limit_if_available("60 per minute")
def portal_order_file(order_id, file_id):
    customer_id = session.get('portal_customer_id')
    if not customer_id:
        return jsonify({'success': False, 'error': 'unauthorized', 'error_type': 'auth'}), 401
    try:
        full = OrderService.get_order_full_data(order_id)
        order_data = full.get('order') or {}
        if order_data.get('customer_id') != customer_id:
            return jsonify({'success': False, 'error': 'Доступ запрещён'}), 403
        from app.services.order_diagnostics_service import OrderDiagnosticsService
        from app.utils.safe_files import mime_from_filename
        info = OrderDiagnosticsService.get_file_for_order(order_data.get('id') or order_id, file_id)
        inline = (info['mime_type'] or '').startswith('image/')
        resp = send_file(
            info['abs_path'],
            mimetype=mime_from_filename(info['filename']),
            as_attachment=not inline,
            download_name=info['filename'],
        )
        resp.headers['X-Content-Type-Options'] = 'nosniff'
        return resp
    except NotFoundError:
        return jsonify({'success': False, 'error': 'Файл не найден'}), 404
    except Exception as e:
        logger.warning("portal file %s/%s: %s", order_id, file_id, e)
        return jsonify({'success': False, 'error': 'Ошибка загрузки файла'}), 500


@bp.route('/orders', methods=['GET'])
@rate_limit_if_available("60 per minute")
def portal_orders():
    """История заявок клиента."""
    customer_id = session.get('portal_customer_id')
    if not customer_id:
        return redirect(url_for('customer_portal.portal_login'))
    
    try:
        orders = CustomerService.get_customer_orders(customer_id, limit=100)
        return render_template('portal/orders.html', orders=orders)
    except Exception as e:
        logger.error(f"Ошибка при загрузке заявок портала: {e}")
        return render_template('portal/orders.html', orders=[], error='Ошибка загрузки данных')


@bp.route('/payments', methods=['GET'])
@rate_limit_if_available("60 per minute")
def portal_payments():
    """История платежей клиента."""
    customer_id = session.get('portal_customer_id')
    if not customer_id:
        return redirect(url_for('customer_portal.portal_login'))
    
    try:
        # Получаем платежи через заявки клиента
        orders = CustomerService.get_customer_orders(customer_id, limit=100)
        payments = []
        for order in orders:
            order_payments = OrderService.get_order_payments(order['id'])
            payments.extend(order_payments)
        
        payments.sort(key=lambda x: x.get('payment_date', ''), reverse=True)
        return render_template('portal/payments.html', payments=payments)
    except Exception as e:
        logger.error(f"Ошибка при загрузке платежей портала: {e}")
        return render_template('portal/payments.html', payments=[], error='Ошибка загрузки данных')


@bp.route('/devices', methods=['GET'])
@rate_limit_if_available("60 per minute")
def portal_devices():
    """Мои устройства с информацией о поломках (заявках)."""
    customer_id = session.get('portal_customer_id')
    if not customer_id:
        return redirect(url_for('customer_portal.portal_login'))
    try:
        devices_raw = DeviceService.get_customer_devices(customer_id)
        devices_with_orders = []
        for device in devices_raw:
            dev_dict = device.to_dict()
            orders = DeviceService.get_device_orders(device.id)
            last_order_date = orders[0]['created_at'] if orders else None
            devices_with_orders.append({'device': dev_dict, 'orders': orders, 'last_order_date': last_order_date})
        devices_with_orders.sort(key=lambda x: (x['last_order_date'] or ''), reverse=True)
        return render_template('portal/devices.html', devices_with_orders=devices_with_orders)
    except Exception as e:
        logger.error(f"Ошибка при загрузке устройств портала: {e}")
        return render_template('portal/devices.html', devices_with_orders=[], error='Ошибка загрузки данных')


def _get_prepayment_overpayment(customer_id: int) -> tuple[float, list]:
    """
    Возвращает (balance, order_rows).
    balance: сумма предоплаты/переплаты по заявкам (paid - total).
    order_rows: список {order_id, order_uid, total, paid, diff, created_at} для каждой заявки.
    """
    orders = CustomerService.get_customer_orders(customer_id, limit=500)
    if not orders:
        return 0.0, []
    from app.database.queries.order_queries import OrderQueries
    totals = OrderQueries.get_orders_totals_batch([o['id'] for o in orders])
    balance = 0.0
    rows = []
    for o in orders:
        t = totals.get(o['id'], {})
        total = float(t.get('total', 0) or 0)
        paid = float(t.get('paid', 0) or 0)
        diff = paid - total
        balance += diff
        rows.append({
            'id': o['id'],
            'order_id': o.get('order_id'),
            'total': total,
            'paid': paid,
            'diff': diff,
            'created_at': o.get('created_at'),
        })
    rows.sort(key=lambda r: (r['created_at'] or ''), reverse=True)
    return balance, rows


@bp.route('/wallet', methods=['GET'])
@rate_limit_if_available("60 per minute")
def portal_wallet():
    """Предоплата / переплата по заявкам (без депозитов)."""
    customer_id = session.get('portal_customer_id')
    if not customer_id:
        return redirect(url_for('customer_portal.portal_login'))
    try:
        balance, order_rows = _get_prepayment_overpayment(customer_id)
        return render_template('portal/wallet.html', balance=balance, order_rows=order_rows)
    except Exception as e:
        logger.error(f"Ошибка при загрузке кошелька портала: {e}")
        return render_template('portal/wallet.html', balance=0.0, order_rows=[], error='Ошибка загрузки данных')


def _warranty_by_order_ids(order_ids):
    """Макс. гарантия в днях по заявкам (товары + услуги)."""
    if not order_ids:
        return {}
    from app.database.connection import get_db_connection
    import sqlite3
    placeholders = ",".join(["?"] * len(order_ids))
    out = {}
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"""
                SELECT order_id, MAX(warranty_days)
                FROM (
                    SELECT order_id, warranty_days FROM order_parts
                    WHERE order_id IN ({placeholders}) AND warranty_days IS NOT NULL
                    UNION ALL
                    SELECT order_id, warranty_days FROM order_services
                    WHERE order_id IN ({placeholders}) AND warranty_days IS NOT NULL
                ) w
                GROUP BY order_id
                """,
                tuple(order_ids) + tuple(order_ids),
            )
            for row in cursor.fetchall():
                out[int(row[0])] = int(row[1] or 0)
    except Exception as e:
        logger.warning("warranty lookup: %s", e)
    return out


@bp.route('/history', methods=['GET'])
@rate_limit_if_available("60 per minute")
def portal_history():
    """История ремонтов: хронология заявок с диагностикой и гарантией."""
    customer_id = session.get('portal_customer_id')
    if not customer_id:
        return redirect(url_for('customer_portal.portal_login'))
    try:
        orders = CustomerService.get_customer_orders(customer_id, limit=200)
        warranty = _warranty_by_order_ids([o['id'] for o in orders])
        for o in orders:
            o['warranty_days'] = warranty.get(o['id']) or 0
            o['ready_pickup'] = _is_ready_for_pickup(o)
        return render_template('portal/history.html', orders=orders)
    except Exception as e:
        logger.error(f"Ошибка при загрузке истории портала: {e}")
        return render_template('portal/history.html', orders=[], error='Ошибка загрузки данных')


@bp.route('/profile', methods=['GET', 'POST'])
@rate_limit_if_available("20 per minute", methods=("POST",))
def portal_profile():
    """Профиль клиента: контакты СЦ и смена пароля."""
    customer_id = session.get('portal_customer_id')
    if not customer_id:
        return redirect(url_for('customer_portal.portal_login'))
    customer = CustomerService.get_customer(customer_id)
    org = _portal_org_card()
    success = None
    error = None
    if request.method == 'POST':
        current_password = request.form.get('current_password') or ''
        new_password = request.form.get('new_password') or ''
        confirm = request.form.get('new_password_confirm') or ''
        from app.utils.validators import password_meets_policy, PASSWORD_MAX_LEN
        if new_password != confirm:
            error = 'Новые пароли не совпадают.'
        elif not password_meets_policy(new_password):
            error = (
                'Пароль слишком длинный.'
                if len(new_password) > PASSWORD_MAX_LEN
                else 'Новый пароль должен быть не менее 6 символов.'
            )
        elif not CustomerPortalService.change_own_password(customer_id, current_password, new_password):
            error = 'Неверный текущий пароль.'
        else:
            success = 'Пароль обновлён.'
            session.clear()
            session['portal_customer_id'] = customer_id
            session['portal_customer_name'] = (customer.name if customer else None) or session.get('portal_customer_name')
            session.permanent = True
            session['_portal_last_active'] = time.time()
    return render_template(
        'portal/profile.html',
        customer=customer,
        org=org,
        success=success,
        error=error,
    )


