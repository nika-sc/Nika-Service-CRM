"""
Blueprint для публичного личного кабинета клиента.
"""
from flask import Blueprint, request, render_template, session, redirect, url_for, jsonify
from functools import wraps
from app.services.customer_portal_service import CustomerPortalService
from app.services.customer_service import CustomerService
from app.services.order_service import OrderService
from app.services.device_service import DeviceService
from app.utils.exceptions import ValidationError, NotFoundError
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('customer_portal', __name__, url_prefix='/portal')

# Инициализация limiter для этого blueprint
limiter = None

def init_limiter(app_limiter):
    """Инициализирует limiter для этого blueprint."""
    global limiter
    limiter = app_limiter

def rate_limit_if_available(limit_str):
    """
    Декоратор для rate limiting, который работает только если limiter инициализирован.
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Проверяем limiter во время выполнения, а не во время декорирования.
            if limiter:
                return limiter.limit(limit_str)(f)(*args, **kwargs)
            return f(*args, **kwargs)
        return wrapper
    return decorator


@bp.route('/login', methods=['GET', 'POST'])
@rate_limit_if_available("5 per minute")
def portal_login():
    """Вход в личный кабинет."""
    if request.method == 'POST':
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        new_password = request.form.get('new_password', '').strip()
        new_password_confirm = request.form.get('new_password_confirm', '').strip()
        change_password = request.form.get('change_password') == 'true'
        
        if not phone or not password:
            return render_template('portal/login.html', error='Введите телефон и пароль')
        
        # Защита от пустого/некорректного телефона (normalize может вернуть "")
        from app.utils.validators import normalize_phone
        normalized_phone = normalize_phone(phone)
        if not normalized_phone or len(normalized_phone) < 10:
            return render_template('portal/login.html', error='Неверные данные для входа')
        
        # Аутентификация по паролю
        customer_data = CustomerPortalService.authenticate_by_password(phone, password)
        
        if customer_data:
            # Защита от session fixation: очищаем сессию перед установкой данных
            session.clear()
            # Если требуется смена пароля
            if change_password and customer_data.get('needs_password_change'):
                if not new_password or len(new_password) < 6:
                    return render_template('portal/login.html', 
                                         error='Новый пароль должен быть не менее 6 символов',
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
            return redirect(url_for('customer_portal.portal_dashboard'))
        else:
            return render_template('portal/login.html', error='Неверные данные для входа')
    
    return render_template('portal/login.html')


@bp.route('/logout', methods=['POST'])
def portal_logout():
    """Выход из личного кабинета."""
    session.pop('portal_customer_id', None)
    session.pop('portal_customer_name', None)
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

        return render_template('portal/dashboard.html',
                             customer=customer,
                             orders=orders,
                             payments=payments,
                             wallet_balance=wallet_balance)
    except Exception as e:
        logger.error(f"Ошибка при загрузке дашборда портала: {e}")
        return render_template(
            'portal/dashboard.html',
            customer=None,
            orders=[],
            payments=[],
            wallet_balance=0.0,
            error='Ошибка загрузки данных'
        )


@bp.route('/api/order/<int:order_id>', methods=['GET'])
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
        # Удаляем комментарии
        out = {
            'order': full.get('order'),
            'device': full.get('device'),
            'services': full.get('services', []),
            'parts': full.get('parts', []),
            'payments': full.get('payments', []),
            'totals': full.get('totals', {}),
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


