"""
Blueprint для работы с заявками и устройствами.
"""
from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash, current_app, Response
from flask_login import login_required, current_user
from collections import defaultdict
from functools import wraps
from app.routes.main import permission_required
from typing import Optional
import logging
import html as _html
from datetime import datetime

# Импорты сервисов
from app.services.order_service import OrderService
from app.services.customer_service import CustomerService
from app.services.device_service import DeviceService
from app.services.payment_service import PaymentService
from app.services.receipt_service import ReceiptService
from app.services.comment_service import CommentService
from app.services.reference_service import ReferenceService
from app.services.settings_service import SettingsService
from app.services.warehouse_service import WarehouseService
from app.services.salary_service import SalaryService
from app.services.user_service import UserService
from app.services.action_log_service import ActionLogService
from app.utils.validators import normalize_phone
from app.utils.exceptions import ValidationError, NotFoundError, DatabaseError
from app.utils.datetime_utils import get_moscow_now, get_moscow_now_str, get_moscow_now_naive, convert_to_moscow
from app.utils.cache import clear_cache
from app.database.connection import get_db_connection
from app.database.queries.order_queries import OrderQueries
from app.database.queries.warehouse_queries import WarehouseQueries
import sqlite3
import re
from urllib.parse import urljoin
from urllib.request import Request as UrlRequest, urlopen
from urllib.error import URLError, HTTPError

bp = Blueprint('orders', __name__)
logger = logging.getLogger(__name__)


@bp.route('/print/logo-proxy')
def print_logo_proxy():
    """
    Проксирует внешний логотип, чтобы печать из about:blank не зависела
    от hotlink-ограничений стороннего сайта.
    """
    settings = SettingsService.get_general_settings() or {}
    logo_url = (settings.get('logo_url') or '').strip()
    if not logo_url:
        return Response(status=204)
    if not re.match(r'^https?://', logo_url, flags=re.IGNORECASE):
        return Response(status=204)
    try:
        req = UrlRequest(logo_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urlopen(req, timeout=8) as resp:
            data = resp.read()
            content_type = resp.headers.get('Content-Type', 'image/png')
        return Response(data, mimetype=content_type)
    except (HTTPError, URLError, TimeoutError, ValueError):
        return Response(status=204)


def _orders_not_deleted_clause(cursor, alias: str = 'o') -> str:
    """
    Возвращает SQL-условие фильтра удаленных заявок.
    Backward compatibility: если колонки is_deleted нет, условие не добавляется.
    """
    try:
        cursor.execute("PRAGMA table_info(orders)")
        columns = {row[1] for row in cursor.fetchall()}
        if 'is_deleted' in columns:
            return f" AND ({alias}.is_deleted = 0 OR {alias}.is_deleted IS NULL)"
    except Exception:
        pass
    return ""


def _hide_status_from_all_orders_header_badges(counter: dict) -> bool:
    """Не показывать бейдж этого статуса в строке «Список заявок» / «Канбан доска»."""
    name = (counter.get('name') or '').strip().lower()
    code_l = str(counter.get('code') or '').strip().lower()
    if name in ('закрыт', 'закрыт неуспешно', 'на запчасти'):
        return True
    if 'незабираш' in name:
        return True
    if code_l in (
        'closed',
        'closed_failed',
        'closed_unsuccess',
        'abandoned',
        'waiting_parts',
        'on_parts',
        'parts_waiting',
    ):
        return True
    return False


def _amount_to_words_ru(amount: float) -> str:
    """Сумма прописью на русском (целые рубли). Для печати квитанций."""
    try:
        rub = int(round(float(amount)))
    except (TypeError, ValueError):
        return ""
    if rub < 0:
        return ""
    if rub == 0:
        return "ноль рублей"
    units = ("", "один", "два", "три", "четыре", "пять", "шесть", "семь", "восемь", "девять")
    units_f = ("", "одна", "две", "три", "четыре", "пять", "шесть", "семь", "восемь", "девять")
    teens = ("десять", "одиннадцать", "двенадцать", "тринадцать", "четырнадцать", "пятнадцать",
             "шестнадцать", "семнадцать", "восемнадцать", "девятнадцать")
    tens = ("", "", "двадцать", "тридцать", "сорок", "пятьдесят", "шестьдесят", "семьдесят", "восемьдесят", "девяносто")
    hundreds = ("", "сто", "двести", "триста", "четыреста", "пятьсот", "шестьсот", "семьсот", "восемьсот", "девятьсот")

    def triple(n: int, feminine: bool = False) -> str:
        u = units_f if feminine else units
        if n == 0:
            return ""
        res = []
        if n >= 100:
            res.append(hundreds[n // 100])
            n %= 100
        if n >= 20:
            res.append(tens[n // 10])
            n %= 10
        if n >= 10:
            res.append(teens[n - 10])
            return " ".join(res)
        if n > 0:
            res.append(u[n])
        return " ".join(res)

    def rubles_word(n: int) -> str:
        if 11 <= n % 100 <= 14:
            return "рублей"
        if n % 10 == 1:
            return "рубль"
        if 2 <= n % 10 <= 4:
            return "рубля"
        return "рублей"

    parts = []
    if rub >= 1_000_000:
        m = rub // 1_000_000
        parts.append(triple(m) + (" миллион" if m % 10 == 1 and m % 100 != 11 else " миллиона" if 2 <= m % 10 <= 4 and m % 100 not in (12, 13, 14) else " миллионов"))
        rub %= 1_000_000
    if rub >= 1_000:
        th = rub // 1_000
        parts.append(triple(th, feminine=True) + (" тысяча" if th % 10 == 1 and th % 100 != 11 else " тысячи" if 2 <= th % 10 <= 4 and th % 100 not in (12, 13, 14) else " тысяч"))
        rub %= 1_000
    if rub > 0:
        parts.append(triple(rub))
    return " ".join(parts).strip() + " " + rubles_word(int(round(float(amount))))


@bp.before_request
def _orders_api_permission_gate():
    """
    Минимальный RBAC-гейт для orders API: раньше многие /api/* были только @login_required.
    - Для чтения (GET/HEAD) требуем view_orders
    - Для изменений (POST/PUT/PATCH/DELETE) требуем edit_orders
    Исключение: /add_order (POST/GET) уже защищен create_orders.
    """
    try:
        # Only guard API endpoints under this blueprint
        if not request.path.startswith("/api/"):
            return None

        if not current_user.is_authenticated:
            return jsonify({"success": False, "error": "auth_required"}), 401

        perm = "view_orders" if request.method in ("GET", "HEAD", "OPTIONS") else "edit_orders"
        if not UserService.check_permission(current_user.id, perm):
            return jsonify({"success": False, "error": "forbidden", "required_permission": perm}), 403
    except Exception as e:
        logger.error(f"Ошибка RBAC-гейта orders API: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Internal server error"}), 500

    return None


def format_phone_display(phone: str) -> str:
    """Форматирует телефон для отображения."""
    if not phone:
        return ''
    digits = normalize_phone(phone)
    if len(digits) == 11 and digits.startswith('7'):
        return f"+{digits[0]}({digits[1:4]}){digits[4:7]}-{digits[7:9]}-{digits[9:]}"
    return phone


def _parse_customer_search_datetime(val) -> Optional[datetime]:
    """Преобразует значение created_at из БД в datetime (наивное)."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    s = str(val).strip()
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace('Z', '+00:00')[:19])
    except Exception:
        pass
    try:
        return datetime.strptime(s[:19], '%Y-%m-%d %H:%M:%S')
    except Exception:
        pass
    try:
        return datetime.strptime(s[:10], '%Y-%m-%d')
    except Exception:
        return None


def _format_customer_search_date_label(val) -> Optional[str]:
    dt = _parse_customer_search_datetime(val)
    if not dt:
        return None
    return dt.strftime('%d.%m.%Y')


def _format_add_order_device_line(
    device_type: str, device_brand: str, model: str, serial_number: str,
) -> str:
    parts = [p.strip() for p in (device_type or '', device_brand or '') if (p or '').strip()]
    line = ' '.join(parts)
    m = (model or '').strip()
    if m:
        line = f'{line} {m}'.strip() if line else m
    sn = (serial_number or '').strip()
    if sn:
        line = f'{line} №{sn}'.strip() if line else f'№{sn}'
    return line or '—'


def _enrich_add_order_customer_search_rows(cursor, customers: list) -> None:
    """
    Дополняет записи клиента для подсказки /add_order: последняя заявка и до 3 последних устройств.
    """
    ids = [c['id'] for c in customers if c.get('id') is not None]
    if not ids:
        return
    not_deleted = _orders_not_deleted_clause(cursor, 'o')
    placeholders = ','.join(['?'] * len(ids))

    cursor.execute(
        f'''
        SELECT o.customer_id, MAX(o.created_at) AS last_order_at
        FROM orders o
        WHERE o.customer_id IN ({placeholders})
          AND (o.hidden = 0 OR o.hidden IS NULL)
          {not_deleted}
        GROUP BY o.customer_id
        ''',
        ids,
    )
    last_map = {row[0]: row[1] for row in cursor.fetchall()}

    cursor.execute(
        f'''
        SELECT o.customer_id, o.created_at, o.device_id,
               COALESCE(dt.name, '') AS device_type,
               COALESCE(db.name, '') AS device_brand,
               COALESCE(NULLIF(TRIM(COALESCE(o.model, '')), ''), '') AS model,
               COALESCE(d.serial_number, '') AS serial_number
        FROM orders o
        JOIN devices d ON d.id = o.device_id
        LEFT JOIN device_types dt ON dt.id = d.device_type_id
        LEFT JOIN device_brands db ON db.id = d.device_brand_id
        WHERE o.customer_id IN ({placeholders})
          AND (o.hidden = 0 OR o.hidden IS NULL)
          {not_deleted}
        ORDER BY o.created_at DESC
        LIMIT 400
        ''',
        ids,
    )

    devices_by_customer = defaultdict(list)
    seen_device = defaultdict(set)
    for row in cursor.fetchall():
        cid, _created_at, dev_id, dt_name, db_name, model, sn = (
            row[0], row[1], row[2], row[3], row[4], row[5], row[6],
        )
        if len(devices_by_customer[cid]) >= 3:
            continue
        if dev_id is None or dev_id in seen_device[cid]:
            continue
        seen_device[cid].add(dev_id)
        label = _format_add_order_device_line(dt_name, db_name, model, sn)
        devices_by_customer[cid].append(label)

    for c in customers:
        cid = c.get('id')
        last_raw = last_map.get(cid)
        c['last_order_at'] = None
        c['last_order_label'] = None
        if last_raw is not None:
            dt = _parse_customer_search_datetime(last_raw)
            if dt:
                c['last_order_at'] = dt.strftime('%Y-%m-%d %H:%M:%S')
            lbl = _format_customer_search_date_label(last_raw)
            if lbl:
                c['last_order_label'] = lbl
        c['recent_devices'] = devices_by_customer.get(cid, [])


# Маршруты для заявок
@bp.route('/add_order', methods=['GET', 'POST'])
@login_required
@permission_required('create_orders')
def add_order():
    """Создание новой заявки."""
    customer_id = request.args.get('customer_id', type=int)
    prefill_customer = None
    if customer_id:
        customer = CustomerService.get_customer(customer_id)
        if customer:
            prefill_customer = customer.to_dict()
    
    if request.method == 'GET':
        # Используем сервис справочников с кэшированием
        refs = ReferenceService.get_all_references()
        
        # Преобразуем словари в кортежи для совместимости с шаблоном
        # Шаблон ожидает: device_types как (id, name), device_brands как (id, name)
        # managers/masters как (id, name), symptoms/appearance_tags как (id, name, sort_order)
        device_types = [(dt['id'], dt['name']) for dt in refs.get('device_types', [])]
        device_brands = [(db['id'], db['name']) for db in refs.get('device_brands', [])]
        managers = [(m['id'], m['name']) for m in refs.get('managers', [])]
        masters = [(m['id'], m['name']) for m in refs.get('masters', [])]
        symptoms = [(s['id'], s['name'], s.get('sort_order', 0)) for s in refs.get('symptoms', [])]
        appearance_tags = [(at['id'], at['name'], at.get('sort_order', 0)) for at in refs.get('appearance_tags', [])]
        order_models = [m['name'] for m in refs.get('order_models', []) if m.get('name')]
        
        return render_template('add_order.html',
            device_types=device_types,
            device_brands=device_brands,
            managers=managers,
            masters=masters,
            symptoms=symptoms,
            appearance_tags=appearance_tags,
            order_models=order_models,
            prefill_customer=prefill_customer
        )

    if request.method == 'POST':
        try:
            # Валидация обязательных полей
            client_name = request.form.get('client_name', '').strip()
            if not client_name:
                raise ValidationError("Имя клиента обязательно")
            
            phone_raw = request.form.get('phone', '').strip()
            if not phone_raw:
                raise ValidationError("Номер телефона обязателен")
            phone = normalize_phone(phone_raw)
            if not phone or len(phone) < 10:
                raise ValidationError("Неверный формат телефона")
            
            email = request.form.get('email', '').strip()
            if email:
                from app.utils.validators import validate_email
                try:
                    email = validate_email(email)
                except ValidationError as e:
                    raise ValidationError(f"Неверный формат email: {e}")
            
            symptom_tags = request.form.get('symptom_tags', '').strip()
            comment = request.form.get('comment', '').strip()
            if not symptom_tags:
                raise ValidationError("Описание неисправности обязательно")
            
            # Валидация device_type_id
            device_type_raw = request.form.get('device_type', '').strip()
            if not device_type_raw:
                raise ValidationError("Тип устройства обязателен")
            try:
                device_type_id = int(device_type_raw)
                if device_type_id <= 0:
                    raise ValidationError("Неверный тип устройства")
            except (ValueError, TypeError):
                raise ValidationError("Неверный формат типа устройства")
            
            # Валидация device_brand_id
            device_brand_raw = request.form.get('device_brand', '').strip()
            if not device_brand_raw:
                raise ValidationError("Бренд устройства обязателен")
            try:
                device_brand_id = int(device_brand_raw)
                if device_brand_id <= 0:
                    raise ValidationError("Неверный бренд устройства")
            except (ValueError, TypeError):
                raise ValidationError("Неверный формат бренда устройства")
            
            serial_number = request.form.get('serial_number', '').strip()
            appearance = request.form.get('appearance', '').strip()
            
            # Предоплата необязательна; пустое значение = 0
            prepayment_raw = request.form.get('prepayment', '0').strip()
            try:
                prepayment = float(prepayment_raw) if prepayment_raw else 0.0
                if prepayment < 0:
                    raise ValidationError("Предоплата не может быть отрицательной")
            except (ValueError, TypeError):
                raise ValidationError("Неверный формат предоплаты")
            
            # Способ предоплаты
            prepayment_method = request.form.get('prepayment_method', 'cash').strip()
            if prepayment_method not in ('cash', 'card', 'transfer'):
                prepayment_method = 'cash'
            
            password = request.form.get('password', '').strip()
            model_raw = request.form.get('model', '').strip()
            if not model_raw:
                raise ValidationError("Модель устройства обязательна")
            model = model_raw
            logger.debug(f"Получено поле model из формы: '{model_raw}' -> {model}")
            
            # Валидация manager_id
            manager_raw = request.form.get('manager', '').strip()
            if not manager_raw:
                raise ValidationError("Менеджер обязателен")
            try:
                manager_id = int(manager_raw)
                if manager_id <= 0:
                    raise ValidationError("Неверный менеджер")
            except (ValueError, TypeError):
                raise ValidationError("Неверный формат менеджера")
            
            # Валидация master_id (обязательно)
            master_raw = request.form.get('master', '').strip()
            if not master_raw:
                raise ValidationError("Мастер обязателен")
            try:
                master_id = int(master_raw)
                if master_id <= 0:
                    raise ValidationError("Выберите мастера")
            except (ValueError, TypeError):
                raise ValidationError("Неверный формат мастера")

            # Используем OrderService для создания заявки
            user_id = current_user.id if current_user.is_authenticated else None
            result = OrderService.create_order(
                customer_name=client_name,
                phone=phone,
                email=email,
                device_type_id=device_type_id,
                device_brand_id=device_brand_id,
                manager_id=manager_id,
                master_id=master_id,
                serial_number=serial_number if serial_number else None,
                prepayment=prepayment,
                prepayment_method=prepayment_method,
                password=password if password else None,
                appearance=appearance if appearance else None,
                comment=comment if comment else None,
                symptom_tags=symptom_tags if symptom_tags else None,
                model=model,
                user_id=user_id
            )

            # Письмо "Заказ принят" отправляем в фоне, чтобы не задерживать редирект.
            try:
                import threading
                app = current_app._get_current_object()
                order_db_id = result.get('id')
                customer_id = result.get('customer_id')

                def _send_order_accepted_email():
                    try:
                        with app.app_context():
                            from app.services.notification_service import NotificationService
                            NotificationService.send_customer_order_email(
                                order_id=order_db_id,
                                template_type='order_accepted',
                customer_id=customer_id
            )
                            NotificationService.send_director_order_email(
                                order_id=order_db_id,
                                template_type='director_order_accepted',
                                status_name='Новая'
                            )
                    except Exception as ex:
                        logger.warning(f"Не удалось отправить письмо 'Заказ принят' для заявки {order_db_id}: {ex}")

                if order_db_id and customer_id:
                    threading.Thread(target=_send_order_accepted_email, daemon=True).start()
            except Exception as e:
                logger.warning(f"Не удалось запустить отправку письма 'Заказ принят': {e}")

            # После создания заявки переходим на страницу заявки (без авто-печати квитанции)
            return redirect(url_for('orders.order_detail', order_id=result['order_id']))
        except (ValidationError, DatabaseError) as e:
            flash(f"Ошибка при сохранении заявки: {e}", 'error')
            refs = ReferenceService.get_all_references()
            # Преобразуем словари в кортежи для совместимости с шаблоном
            device_types = [(dt['id'], dt['name']) for dt in refs.get('device_types', [])]
            device_brands = [(db['id'], db['name']) for db in refs.get('device_brands', [])]
            managers = [(m['id'], m['name']) for m in refs.get('managers', [])]
            masters = [(m['id'], m['name']) for m in refs.get('masters', [])]
            symptoms = [(s['id'], s['name'], s.get('sort_order', 0)) for s in refs.get('symptoms', [])]
            appearance_tags = [(at['id'], at['name'], at.get('sort_order', 0)) for at in refs.get('appearance_tags', [])]
            order_models = [m['name'] for m in refs.get('order_models', []) if m.get('name')]
            return render_template('add_order.html',
                error=str(e),
                device_types=device_types,
                device_brands=device_brands,
                managers=managers,
                masters=masters,
                symptoms=symptoms,
                appearance_tags=appearance_tags,
                order_models=order_models
            )
        except Exception as e:
            flash(f"Неожиданная ошибка: {e}", 'error')
            refs = ReferenceService.get_all_references()
            # Преобразуем словари в кортежи для совместимости с шаблоном
            device_types = [(dt['id'], dt['name']) for dt in refs.get('device_types', [])]
            device_brands = [(db['id'], db['name']) for db in refs.get('device_brands', [])]
            managers = [(m['id'], m['name']) for m in refs.get('managers', [])]
            masters = [(m['id'], m['name']) for m in refs.get('masters', [])]
            symptoms = [(s['id'], s['name'], s.get('sort_order', 0)) for s in refs.get('symptoms', [])]
            appearance_tags = [(at['id'], at['name'], at.get('sort_order', 0)) for at in refs.get('appearance_tags', [])]
            order_models = [m['name'] for m in refs.get('order_models', []) if m.get('name')]
            return render_template('add_order.html',
                error="Ошибка при сохранении заявки",
                device_types=device_types,
                device_brands=device_brands,
                managers=managers,
                masters=masters,
                symptoms=symptoms,
                appearance_tags=appearance_tags,
                order_models=order_models
            )

@bp.route('/all_orders')
@login_required
@permission_required('view_orders')
def all_orders():
    """Список всех заявок."""
    try:
        # Получаем параметры из запроса
        sort_by = request.args.get('sort_by', 'created_at')
        sort_order = request.args.get('sort_order', 'DESC').upper()
        status_filter = request.args.get('status')
        view = request.args.get('view', 'registry')  # registry | kanban | log
        search_query = request.args.get('q', '').strip()
        manager_filter = request.args.get('manager')
        master_filter = request.args.get('master')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        
        # Пагинация
        # Реестр: server-side DataTables, данные подгружаются через AJAX (см. /api/datatables/orders)
        # Канбан: оставляем старую пагинацию
        try:
            page = int(request.args.get('page', 1))
            if page < 1:
                page = 1
        except (ValueError, TypeError):
            page = 1
        per_page = 50
        
        # Формируем фильтры
        filters = {}
        if status_filter:
            filters['status'] = status_filter
        # search_query используется только для канбана (в реестре поиск делает DataTables)
        if search_query and view != 'registry':
            filters['search'] = search_query
        if manager_filter:
            try:
                filters['manager_id'] = int(manager_filter)
            except (ValueError, TypeError):
                pass
        if master_filter:
            try:
                filters['master_id'] = int(master_filter)
            except (ValueError, TypeError):
                pass
        if date_from:
            filters['date_from'] = date_from
        if date_to:
            filters['date_to'] = date_to
        
        # Получаем заявки
        if view == 'registry':
            orders = []
            paginator = None
        elif view == 'kanban':
            # Канбан: нужны все подходящие заявки, иначе колонки только для статусов,
            # попавших на первую страницу пагинации (раньше было per_page=50).
            _kanban_max_orders = 10000
            count_pg = OrderService.get_orders_with_details(filters, 1, 1)
            if count_pg.total <= 0:
                paginator = count_pg
                orders = []
            else:
                take = min(count_pg.total, _kanban_max_orders)
                paginator = OrderService.get_orders_with_details(filters, 1, take)
                orders = paginator.items
        else:
            paginator = OrderService.get_orders_with_details(filters, page, per_page)
            orders = paginator.items
        
        # Форматируем телефоны для отображения
        for order in orders:
            if 'phone' in order:
                order['phone_display'] = format_phone_display(order['phone'])
        
        # Получаем справочники
        refs = ReferenceService.get_all_references()
        # По умолчанию в формах — только неархивные; канбан дополняется статусами из фактических заявок
        order_statuses = [s for s in refs['order_statuses'] if not s.get('is_archived')]
        if view == 'kanban':
            all_status_by_id = {s['id']: s for s in refs['order_statuses']}
            seen_ids = {s['id'] for s in order_statuses}
            for order in orders:
                sid = order.get('status_id')
                if sid is None:
                    continue
                if sid not in seen_ids and sid in all_status_by_id:
                    order_statuses.append(all_status_by_id[sid])
                    seen_ids.add(sid)
            order_statuses.sort(
                key=lambda s: (
                    1 if s.get('is_archived') else 0,
                    s.get('sort_order', 999) if s.get('sort_order') is not None else 999,
                    (s.get('name') or '').lower(),
                    s['id'],
                )
            )
        # Конвертируем в кортежи для шаблона
        managers = [(m['id'], m['name']) for m in refs.get('managers', [])]
        masters = [(m['id'], m['name']) for m in refs.get('masters', [])]
        device_types = refs['device_types']
        device_brands = refs['device_brands']
        
        # Создаем мапы для быстрого доступа
        status_map = {s['id']: s for s in order_statuses}
        status_map_by_code = {str(s['code']): s for s in order_statuses}
        
        # Подсчет статистики по статусам - БЕЗ ВСЕХ ФИЛЬТРОВ (только hidden = 0)
        # Показываем ВСЕ статусы (включая архивные) с сортировкой по sort_order и имени
        from app.database.connection import get_db_connection
        import sqlite3

        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()

                not_deleted_clause = _orders_not_deleted_clause(cursor, 'o')
                master_in_progress_counters = []
                # Все статусы (в т.ч. архивные), как в «Управление статусами»: sort_order, name, is_archived для группировки
                cursor.execute('''
                    SELECT
                        os.id,
                        os.code,
                        os.name,
                        os.color,
                        COALESCE(os.sort_order, 999) AS sort_order,
                        (os.is_archived = 1) AS is_archived,
                        COALESCE(COUNT(o.id), 0) AS cnt
                    FROM order_statuses AS os
                    LEFT JOIN orders AS o
                        ON o.status_id = os.id
                        AND (o.hidden = 0 OR o.hidden IS NULL)
                ''' + not_deleted_clause + '''
                    GROUP BY os.id, os.code, os.name, os.color, os.sort_order, os.is_archived
                    ORDER BY (os.is_archived = 1), COALESCE(os.sort_order, 999), os.name, os.id
                ''')
                
                status_counts = cursor.fetchall()
                status_dict = {row['code']: row['cnt'] for row in status_counts if row['code']}
                status_counters = [dict(row) for row in status_counts]
                # Как в «Управление статусами»: активные и архивные отдельно для отображения в card-title
                active_status_counters = [s for s in status_counters if not s.get('is_archived')]
                archived_status_counters = [s for s in status_counters if s.get('is_archived')]
                active_status_counters = [
                    s for s in active_status_counters if not _hide_status_from_all_orders_header_badges(s)
                ]
                archived_status_counters = [
                    s for s in archived_status_counters if not _hide_status_from_all_orders_header_badges(s)
                ]
                
                # Количество заявок «в работе» (все статусы кроме финальных и кроме «Незабирашка»)
                cursor.execute('''
                    SELECT COUNT(o.id)
                    FROM orders AS o
                    LEFT JOIN order_statuses AS os ON os.id = o.status_id
                    WHERE (o.hidden = 0 OR o.hidden IS NULL)''' + not_deleted_clause + '''
                    AND (os.is_final = 0 OR os.is_final IS NULL)
                    AND (LOWER(TRIM(os.name)) NOT LIKE '%незабираш%')
                ''')
                in_progress_orders_count = (cursor.fetchone() or [0])[0] or 0

                # «В работе у [мастер]: N» — количество заявок в работе по каждому мастеру (без финальных и без Незабирашка)
                cursor.execute('''
                    SELECT
                        m.id,
                        m.name,
                        (SELECT COUNT(*) FROM orders o
                         JOIN order_statuses os ON os.id = o.status_id
                         WHERE o.master_id = m.id
                           AND (o.hidden = 0 OR o.hidden IS NULL)
                ''' + not_deleted_clause + '''
                           AND (os.is_final = 0 OR os.is_final IS NULL)
                           AND (LOWER(TRIM(os.name)) NOT LIKE '%незабираш%')
                        ) AS cnt
                    FROM masters m
                    ORDER BY m.name
                ''')
                master_in_progress_rows = cursor.fetchall()
                master_in_progress_counters = [dict(row) for row in master_in_progress_rows]
                
        except Exception as e:
            logger.error(f"Ошибка при подсчете статистики по статусам: {e}")
            status_dict = {}
            status_counters = []
            active_status_counters = []
            archived_status_counters = []
            in_progress_orders_count = 0
            master_in_progress_counters = []
        
        # total_orders - это сумма всех счетчиков по статусам (точное количество заявок в таблице)
        total_orders = sum(status_dict.values()) if status_dict else 0
        new_orders_count = status_dict.get('new', 0)
        in_progress_count = status_dict.get('in_progress', 0)
        completed_count = status_dict.get('completed', 0)
        closed_count = status_dict.get('closed', 0)
        close_print_mode = (SettingsService.get_general_settings() or {}).get('close_print_mode', 'choice')
        
        return render_template(
            'all_orders.html',
            orders=orders,
            sort_by=sort_by,
            sort_order=sort_order,
            status_filter=status_filter,
            view=view,
            search_query=search_query,
            manager_filter=manager_filter,
            master_filter=master_filter,
            date_from=date_from,
            date_to=date_to,
            managers=managers,
            masters=masters,
            device_types=device_types,
            device_brands=device_brands,
            order_statuses=order_statuses,
            status_map=status_map,
            status_map_by_code=status_map_by_code,
            status_dict=status_dict,
            status_counters=status_counters,
            active_status_counters=active_status_counters,
            archived_status_counters=archived_status_counters,
            master_in_progress_counters=master_in_progress_counters,
            total_orders=total_orders,
            in_progress_orders_count=in_progress_orders_count,
            new_orders_count=new_orders_count,
            in_progress_count=in_progress_count,
            completed_count=completed_count,
            closed_count=closed_count,
            page=paginator.page if paginator else 1,
            per_page=paginator.per_page if paginator else per_page,
            total=paginator.total if paginator else 0,
            pages=paginator.pages if paginator else 1,
            close_print_mode=close_print_mode,
        )
    except Exception as e:
        logger.error(f"Ошибка при получении списка заявок: {e}", exc_info=True)
        flash('Ошибка при загрузке списка заявок', 'error')
        return render_template('errors/500.html'), 500


def _format_date_ddmm(created_at) -> str:
    if not created_at:
        return ''
    try:
        if isinstance(created_at, datetime):
            return created_at.strftime("%d.%m")
        date_part = str(created_at).replace('T', ' ').split(' ')[0]
        y, m, d = date_part.split('-')
        return f"{d}.{m}"
    except Exception:
        return ''


def _format_date_full(created_at, with_time: bool = False) -> str:
    """Форматирует дату как dd.mm.yyyy или dd.mm.yyyy HH:mm."""
    if not created_at:
        return '—'
    try:
        if isinstance(created_at, datetime):
            return created_at.strftime("%d.%m.%Y %H:%M" if with_time else "%d.%m.%Y")
        parts = str(created_at).replace('T', ' ').split(' ')
        date_part = parts[0]
        y, m, d = date_part.split('-')
        out = f"{d}.{m}.{y}"
        if with_time and len(parts) > 1 and parts[1]:
            time_part = parts[1][:5]  # HH:mm
            out += ' ' + time_part
        return out
    except Exception:
        return '—'


def _format_money(value: float) -> str:
    """Форматирует сумму для отображения в таблице."""
    try:
        v = float(value)
        return f"{v:,.2f} ₽".replace(',', ' ')
    except (TypeError, ValueError):
        return "—"


def _split_tags(s: str):
    if not s:
        return []
    return [t.strip() for t in str(s).split(',') if t and t.strip()]


@bp.route('/api/datatables/orders')
@login_required
def api_datatables_orders():
    """Server-side DataTables источник данных для /all_orders?view=registry."""
    draw = int(request.args.get('draw', 1))
    start = int(request.args.get('start', 0))
    length = int(request.args.get('length', 25))
    if length <= 0:
        length = 25
    if length > 200:
        length = 200
    page = (start // length) + 1

    # Фильтры со страницы
    status_filter = request.args.get('status') or None
    manager_filter = request.args.get('manager') or None
    master_filter = request.args.get('master') or None
    date_from = request.args.get('date_from') or None
    date_to = request.args.get('date_to') or None

    base_filters = {}
    if status_filter:
        base_filters['status'] = status_filter
    if manager_filter:
        try:
            base_filters['manager_id'] = int(manager_filter)
        except (ValueError, TypeError):
            pass
    if master_filter:
        try:
            base_filters['master_id'] = int(master_filter)
        except (ValueError, TypeError):
            pass
    if date_from:
        base_filters['date_from'] = date_from
    if date_to:
        base_filters['date_to'] = date_to

    search_value = (request.args.get('search[value]', '') or '').strip()
    filters = dict(base_filters)
    if search_value:
        has_alpha = any(ch.isalpha() for ch in search_value)
        digits = ''.join(ch for ch in search_value if ch.isdigit())
        if (not has_alpha) and digits and len(digits) >= 6:
            filters['search'] = digits
        else:
            filters['search'] = search_value

    # Сортировка: DataTables при serverSide шлёт order[0][column] и order[0][dir].
    # Важно: при ColReorder нельзя полагаться только на индекс колонки.
    # Берем data-ключ колонки из columns[{idx}][data] и мапим его в поле БД.
    sort_by = 'updated_at'
    sort_order = 'DESC'
    order_col = request.args.get('order[0][column]')
    order_dir = (request.args.get('order[0][dir]') or 'desc').strip().lower()
    if order_col is not None and order_dir in ('asc', 'desc'):
        try:
            col_index = int(order_col)
            sort_order = 'ASC' if order_dir == 'asc' else 'DESC'
            col_data_key = request.args.get(f'columns[{col_index}][data]', '') or ''

            # DataTables data-ключ колонки -> поле сортировки SQL
            col_data_to_sort = {
                'id_col': 'id',
                'status_col': 'status',
                'client_col': 'client_name',
                'device_col': 'device_type',
                'brand_col': 'device_brand',
                'master_col': 'master',
                'manager_col': 'manager',
                'created_at_col': 'created_at',
                'updated_at_col': 'updated_at',
            }
            sort_by = col_data_to_sort.get(col_data_key, 'updated_at')
        except (ValueError, TypeError):
            pass

    # recordsTotal: без глобального поиска (но с фиксированными фильтрами)
    total_result = OrderQueries.get_orders_with_all_details(
        filters=base_filters if base_filters else None,
        page=1,
        per_page=1,
        sort_by=sort_by,
        sort_order=sort_order
    )
    records_total = int(total_result['total'])

    result = OrderQueries.get_orders_with_all_details(
        filters=filters if filters else None,
        page=page,
        per_page=length,
        sort_by=sort_by,
        sort_order=sort_order
    )
    records_filtered = int(result['total'])

    # Список статусов для дропдауна
    with get_db_connection(row_factory=sqlite3.Row) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, code, name, color
            FROM order_statuses
            WHERE is_archived = 0 OR is_archived IS NULL
            ORDER BY id
            """
        )
        statuses = [dict(r) for r in cursor.fetchall()]

    order_ids = [o.get('id') for o in result['items'] if o.get('id')]
    totals_batch = OrderQueries.get_orders_totals_batch(order_ids) if order_ids else {}

    data = []
    for o in result['items']:
        oid = o.get('id')
        order_uid = o.get('order_id') or ''
        created_at = o.get('created_at') or ''
        totals = totals_batch.get(oid, {})

        status_name = o.get('status_name') or 'Не указан'
        status_color = o.get('status_color') or '#6c757d'
        status_id = o.get('status_id') or ''

        customer_id = o.get('customer_id')
        client_name = o.get('client_name') or '—'
        phone = o.get('phone') or ''

        device_id = o.get('device_id')
        device_type = o.get('device_type') or '—'
        device_brand = o.get('device_brand') or '—'
        model = o.get('model') or ''

        symptom_tags = o.get('symptom_tags') or ''
        appearance = o.get('appearance') or ''
        master = o.get('master') or '—'

        # col 0: ID + дата (dd.mm)
        ddmm = _format_date_ddmm(created_at)
        col_id = (
            f'<div class="fw-bold">#{oid}</div>'
            + (f'<div class="text-muted small">{ddmm}</div>' if ddmm else '')
        )

        # col 1: статус с dropdown
        dropdown_items = []
        for st in statuses:
            st_id = st.get('id')
            st_code = st.get('code') or ''
            st_name = st.get('name') or '—'
            st_color = st.get('color') or '#6c757d'
            active = 'active' if str(status_id) == str(st_id) else ''
            dropdown_items.append(
                '<li>'
                f'<a class="dropdown-item status-dropdown-item {active}" href="#" '
                f'data-status-id="{st_id}" data-status-code="{_html.escape(str(st_code))}" '
                f'data-status-name="{_html.escape(str(st_name))}" data-status-color="{_html.escape(str(st_color))}" '
                'onclick="return window.selectQuickStatus ? window.selectQuickStatus(this, event) : false;">'
                f'<span class="status-indicator" style="background-color: {_html.escape(str(st_color))};"></span>'
                f'{_html.escape(str(st_name))}'
                '</a></li>'
            )
        col_status = (
            '<div class="dropdown" onclick="event.stopPropagation();">'
            f'<button class="btn btn-sm dropdown-toggle quick-status-btn" type="button" '
            'onmousedown="event.stopPropagation();" '
            'onclick="return window.toggleQuickStatusMenu ? window.toggleQuickStatusMenu(this, event) : false;" '
            f'aria-expanded="false" data-order-id="{_html.escape(str(order_uid))}" data-order-db-id="{oid}" '
            f'data-status-id="{status_id}" data-status-color="{_html.escape(str(status_color))}" '
            f'style="background-color: {_html.escape(str(status_color))}; border-color: {_html.escape(str(status_color))}; '
            'color: #fff; min-width: 150px;">'
            f'{_html.escape(str(status_name))}'
            '</button>'
            '<ul class="dropdown-menu status-dropdown-menu">'
            + ''.join(dropdown_items) +
            '</ul></div>'
        )

        # col 2: клиент + телефон
        if customer_id:
            client_html = (
                f'<a href="/clients/{customer_id}" class="text-primary fw-bold text-decoration-none" onclick="event.stopPropagation();">'
                f'{_html.escape(str(client_name))}</a>'
            )
        else:
            client_html = f'<span class="fw-bold">{_html.escape(str(client_name))}</span>'

        phone_digits = ''.join(ch for ch in str(phone) if ch.isdigit()) if phone else ''
        phone_block = ''
        if phone_digits:
            phone_display = format_phone_display(phone_digits) if phone_digits else phone_digits
            phone_block = (
                '<div class="contact-item mt-1">'
                f'<span class="contact-value text-muted small" data-phone="{phone_digits}" '
                f'onclick="showPhoneMenu(event, \'{phone_digits}\')">{_html.escape(phone_display)}</span>'
                f'<div class="contact-dropdown" id="phoneMenu-{phone_digits}">'
                f'<a href="tel:{phone_digits}" class="contact-dropdown-item" onclick="event.stopPropagation();"><i class="fas fa-phone"></i> Позвонить</a>'
                f'<a href="https://wa.me/{phone_digits}" class="contact-dropdown-item" onclick="event.stopPropagation();"><i class="fab fa-whatsapp"></i> WhatsApp</a>'
                f'<a href="viber://chat?number={phone_digits}" class="contact-dropdown-item" onclick="event.stopPropagation();"><i class="fab fa-viber"></i> Viber</a>'
                f'<a href="https://t.me/+{(phone_digits if phone_digits.startswith("7") else ("7" + phone_digits[1:] if len(phone_digits) == 11 and phone_digits.startswith("8") else phone_digits))}" class="contact-dropdown-item" onclick="event.stopPropagation();"><i class="fab fa-telegram"></i> Написать в Телеграмм</a>'
                f'<a href="#" class="contact-dropdown-item" onclick="copyToClipboard(\'{phone_digits}\', event)"><i class="fas fa-copy"></i> Копировать</a>'
                '</div>'
                f'<button class="contact-btn" onclick="copyToClipboard(\'{phone_digits}\', event)" title="Копировать"><i class="fas fa-copy"></i></button>'
                '</div>'
            )
        col_client = f'<div onclick="event.stopPropagation();">{client_html}{phone_block}</div>'

        # col 3: устройство (тип)
        if device_id and device_type and device_type != '—':
            col_device = f'<a href="/device/{device_id}" class="text-primary text-decoration-none" onclick="event.stopPropagation();">{_html.escape(str(device_type))}</a>'
        else:
            col_device = _html.escape(str(device_type or '—'))

        # col 4: бренд (+ модель)
        brand_text = f"{device_brand}{(' ' + model) if model else ''}".strip()
        if device_id and brand_text and brand_text != '—':
            col_brand = f'<a href="/device/{device_id}" class="text-primary text-decoration-none" onclick="event.stopPropagation();">{_html.escape(brand_text)}</a>'
        else:
            col_brand = _html.escape(brand_text or '—')

        # col 5: неисправность
        tags = _split_tags(symptom_tags)
        if tags:
            col_symptoms = '<div class="symptom-tags">' + ''.join(
                f'<span class="symptom-tag">{_html.escape(t)}</span>' for t in tags
            ) + '</div>'
        else:
            col_symptoms = '<span class="text-muted">—</span>'

        # col 6: внешний вид
        tags2 = _split_tags(appearance)
        if tags2:
            col_appearance = '<div class="symptom-tags">' + ''.join(
                f'<span class="symptom-tag">{_html.escape(t)}</span>' for t in tags2
            ) + '</div>'
        else:
            col_appearance = '<span class="text-muted">—</span>'

        # col 7: мастер
        col_master = _html.escape(str(master))

        # col 8: менеджер
        manager_name = o.get('manager') or o.get('manager_name') or '—'
        col_manager = _html.escape(str(manager_name))

        # col 9: дата создания
        col_created_at = _format_date_full(created_at, with_time=True)

        # col 10–12: суммы (из batch)
        col_total = _format_money(totals.get('total', 0))
        col_paid = _format_money(totals.get('paid', 0))
        debt_val = totals.get('debt', 0) or 0
        col_debt = _format_money(debt_val) if debt_val > 0 else '—'

        # col 13–15: услуги, запчасти, предоплата (скрыты по умолчанию)
        col_services_total = _format_money(totals.get('services_total', 0))
        col_parts_total = _format_money(totals.get('parts_total', 0))
        col_prepayment = _format_money(totals.get('prepayment', 0))

        # col 16–20: серийный номер, email, комментарий, дата обновления, кол-во комментариев (скрыты по умолчанию)
        col_serial_number = _html.escape(str(o.get('serial_number') or '—'))
        col_email = _html.escape(str(o.get('email') or '—'))
        comment_raw = (o.get('comment') or '').strip()
        col_comment = _html.escape(comment_raw[:50] + ('…' if len(comment_raw) > 50 else '')) if comment_raw else '—'
        col_updated_at = _format_date_full(o.get('updated_at') or '', with_time=True)
        col_comments_count = str(o.get('comments_count') or 0)

        data.append({
            "order_id": order_uid,
            "id_col": col_id,
            "status_col": col_status,
            "client_col": col_client,
            "device_col": col_device,
            "brand_col": col_brand,
            "symptoms_col": col_symptoms,
            "appearance_col": col_appearance,
            "master_col": col_master,
            "manager_col": col_manager,
            "created_at_col": col_created_at,
            "total_col": col_total,
            "paid_col": col_paid,
            "debt_col": col_debt,
            "services_total_col": col_services_total,
            "parts_total_col": col_parts_total,
            "prepayment_col": col_prepayment,
            "serial_number_col": col_serial_number,
            "email_col": col_email,
            "comment_col": col_comment,
            "updated_at_col": col_updated_at,
            "comments_count_col": col_comments_count,
        })

    return jsonify({
        "draw": draw,
        "recordsTotal": records_total,
        "recordsFiltered": records_filtered,
        "data": data
    })

@bp.route('/order/<order_id>', methods=['GET', 'POST'])
@login_required
@permission_required('view_orders')
def order_detail(order_id):
    """Детали заявки. В URL может быть UUID заявки или внутренний id (число)."""
    try:
        logger.info(f"Попытка открыть заявку: {order_id}")
        
        # Сначала ищем по UUID (orders.order_id)
        order = OrderService.get_order_by_uuid(order_id)
        # Если не найден и передан числовой id — ищем по внутреннему id
        if not order and str(order_id).isdigit():
            order = OrderService.get_order(int(order_id))
        if not order:
            logger.warning(f"Заявка {order_id} не найдена (ни по UUID, ни по id)")
            flash('Заявка не найдена', 'error')
            return redirect(url_for('orders.all_orders'))
        
        logger.info(f"Заявка найдена: ID={order.id}, UUID={order.order_id}")

        # Получаем полные данные заявки
        try:
            order_data = OrderService.get_order_full_data(order.id)
        except NotFoundError as e:
            logger.error(f"Заявка с ID {order.id} не найдена в get_order_full_data: {e}")
            flash('Ошибка при загрузке данных заявки', 'error')
            return redirect(url_for('orders.all_orders'))
        except Exception as e:
            logger.exception(f"Ошибка при получении полных данных заявки {order.id}: {e}")
            flash('Ошибка при загрузке данных заявки', 'error')
            return redirect(url_for('orders.all_orders'))
        
        # Получаем справочники для формы (нужны и для POST, и для GET)
        refs = ReferenceService.get_all_references()
        
        # Если POST - обновление заявки
        if request.method == 'POST':
            try:
                # Проверяем, разрешено ли редактирование заявки
                if not OrderService.check_order_edit_allowed(order.id):
                    flash('Редактирование заявки заблокировано для текущего статуса. Разрешено только добавление комментариев.', 'error')
                    # Перенаправляем обратно на страницу заявки (номер из БД — order_id, как в файле)
                    return redirect(url_for('orders.order_detail', order_id=order.order_id))
                
                # Извлекаем данные из формы
                # ВАЖНО: Поля клиента (client_name, phone, email) теперь скрыты в форме редактирования
                # и должны редактироваться в разделе клиента. Но оставляем их для обратной совместимости.
                client_name = request.form.get('client_name', '').strip()
                phone_raw = request.form.get('phone', '').strip()
                phone = normalize_phone(phone_raw) if phone_raw else None
                email = request.form.get('email', '').strip() or None
                
                symptom_tags = request.form.get('symptom_tags', '').strip()
                comment = request.form.get('comment', '').strip()
                device_type_id = int(request.form['device_type'])
                device_brand_id = int(request.form['device_brand'])
                serial_number = request.form.get('serial_number', '').strip()
                model = request.form.get('model', '').strip() or None
                appearance = request.form.get('appearance', '').strip()
                prepayment = request.form.get('prepayment', '0').strip()
                password = request.form.get('password', '').strip()
                manager_id = int(request.form['manager'])
                master_raw = request.form.get('master', '')
                master_id = int(master_raw) if master_raw and master_raw.isdigit() else None
                # Статус теперь не редактируется через форму - используется выпадающий список в интерфейсе
                # Не обновляем статус через форму редактирования заявки
                status_id = None  # Статус не обновляется через форму редактирования
                
                # Обновляем клиента только если данные клиента были переданы (для обратной совместимости)
                # В новой версии формы эти поля скрыты, поэтому клиент не будет обновляться
                if client_name and phone and order_data.get('customer') and order_data['customer'].get('id'):
                    customer_data = {
                        'name': client_name,
                        'phone': phone,
                        'email': email
                    }
                    CustomerService.update_customer(order_data['customer']['id'], customer_data)
                
                # Обновляем устройство
                DeviceService.update_device(
                    order_data['device']['id'],
                    device_type_id=device_type_id,
                    device_brand_id=device_brand_id,
                    serial_number=serial_number if serial_number else None,
                    password=password if password else None,
                    symptom_tags=symptom_tags if symptom_tags else None,
                    appearance_tags=appearance if appearance else None
                )
                
                # Обновляем заявку
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    # Обрабатываем model - находим или создаем в order_models
                    model_id_value = None
                    model_text_value = model if model else None
                    if model:
                        normalized_model = model.strip()
                        if normalized_model:
                            normalized_model = normalized_model[0].upper() + normalized_model[1:] if len(normalized_model) > 1 else normalized_model.upper()
                            cursor.execute('SELECT id FROM order_models WHERE name = ?', (normalized_model,))
                            model_row = cursor.fetchone()
                            if model_row:
                                model_id_value = model_row[0]
                            else:
                                cursor.execute('INSERT INTO order_models (name) VALUES (?)', (normalized_model,))
                                model_id_value = cursor.lastrowid
                    
                    # Получаем старый статус ДО обновления (для правильного логирования)
                    old_status_id = order_data['order'].get('status_id')
                    
                    # Обновляем основные поля заявки
                    # prepayment_cents (если колонка существует)
                    cursor.execute("PRAGMA table_info(orders)")
                    order_cols = [c[1] for c in cursor.fetchall()]
                    prepayment_cents = None
                    if 'prepayment_cents' in order_cols:
                        try:
                            prepayment_cents = int(round(float(prepayment or 0) * 100))
                        except Exception:
                            prepayment_cents = 0

                    # Обновляем заявку БЕЗ статуса (статус обновим через сервис для правильного логирования)
                    # Время в часовом поясе приложения (из настроек БД/конфига)
                    updated_at_moscow = get_moscow_now_str()
                    
                    cursor.execute('''
                        UPDATE orders
                        SET manager_id = ?, master_id = ?,
                            prepayment = ?, prepayment_cents = COALESCE(?, prepayment_cents), password = ?, appearance = ?,
                            comment = ?, symptom_tags = ?, model = ?, model_id = ?, updated_at = ?
                        WHERE id = ?
                    ''', (manager_id, master_id, prepayment, prepayment_cents,
                          password if password else None,
                          appearance if appearance else None,
                          comment if comment else None,
                          symptom_tags if symptom_tags else None,
                          model_text_value,
                          model_id_value,
                          updated_at_moscow,
                          order.id))
                    
                    # Обновляем симптомы в order_symptoms
                    # Сначала удаляем старые связи
                    cursor.execute('DELETE FROM order_symptoms WHERE order_id = ?', (order.id,))
                    
                    # Затем создаем новые связи
                    if symptom_tags:
                        symptom_names = re.split(r'[,;\n\r]+', symptom_tags)
                        for symptom_name in symptom_names:
                            normalized = symptom_name.strip()
                            if not normalized:
                                continue
                            normalized = normalized[0].upper() + normalized[1:] if len(normalized) > 1 else normalized.upper()
                            
                            cursor.execute('SELECT id FROM symptoms WHERE name = ?', (normalized,))
                            symptom_row = cursor.fetchone()
                            if symptom_row:
                                symptom_id = symptom_row[0]
                            else:
                                cursor.execute('''
                                    INSERT INTO symptoms (name, sort_order) 
                                    VALUES (?, (SELECT COALESCE(MAX(sort_order), 0) + 1 FROM symptoms))
                                ''', (normalized,))
                                symptom_id = cursor.lastrowid
                            
                            try:
                                cursor.execute('INSERT INTO order_symptoms (order_id, symptom_id) VALUES (?, ?)', 
                                             (order.id, symptom_id))
                            except sqlite3.IntegrityError:
                                pass
                    
                    # Обновляем теги внешнего вида в order_appearance_tags
                    # Сначала удаляем старые связи
                    cursor.execute('DELETE FROM order_appearance_tags WHERE order_id = ?', (order.id,))
                    
                    # Затем создаем новые связи
                    if appearance:
                        tag_names = re.split(r'[,;\n\r]+', appearance)
                        for tag_name in tag_names:
                            normalized = tag_name.strip()
                            if not normalized:
                                continue
                            normalized = normalized[0].upper() + normalized[1:] if len(normalized) > 1 else normalized.upper()
                            
                            cursor.execute('SELECT id FROM appearance_tags WHERE name = ?', (normalized,))
                            tag_row = cursor.fetchone()
                            if tag_row:
                                tag_id = tag_row[0]
                            else:
                                cursor.execute('''
                                    INSERT INTO appearance_tags (name, sort_order) 
                                    VALUES (?, (SELECT COALESCE(MAX(sort_order), 0) + 1 FROM appearance_tags))
                                ''', (normalized,))
                                tag_id = cursor.lastrowid
                            
                            try:
                                cursor.execute('INSERT INTO order_appearance_tags (order_id, appearance_tag_id) VALUES (?, ?)', 
                                             (order.id, tag_id))
                            except sqlite3.IntegrityError:
                                pass
                    
                    conn.commit()
                
                # Статус больше не обновляется через форму редактирования заявки
                # Используйте выпадающий список статуса в интерфейсе заявки для изменения статуса
                # if status_id is not None and status_id != old_status_id:
                #     user_id = current_user.id if current_user.is_authenticated else None
                #     OrderService.update_order_status(order.id, status_id, user_id)
                
                # Логируем обновление заявки в action_logs
                try:
                    user_id = current_user.id if current_user.is_authenticated else None
                    username = current_user.username if current_user.is_authenticated else None
                    
                    logger.info(f"=== Начало логирования изменений для заявки #{order.id} ===")
                    logger.info(f"Текущие значения из формы: manager_id={manager_id}, master_id={master_id}, device_type_id={device_type_id}, device_brand_id={device_brand_id}")
                    logger.info(f"Старые значения из order_data: manager_id={order_data['order'].get('manager_id')}, master_id={order_data['order'].get('master_id')}, device_type_id={order_data['device'].get('device_type_id')}, device_brand_id={order_data['device'].get('device_brand_id')}")
                    logger.info(f"order_data['device'] keys: {list(order_data['device'].keys())}")
                    logger.info(f"order_data['device'] full: {order_data['device']}")
                    
                    # Собираем информацию об изменениях
                    changes = {}
                    # Используем old_status_id, который был получен ДО обновления
                    if status_id is not None and status_id != old_status_id:
                        # Получаем названия статусов для читаемого отображения
                        old_status_name = None
                        new_status_name = None
                        
                        # Находим старый статус
                        old_status = next((s for s in refs['order_statuses'] if s['id'] == old_status_id), None)
                        if old_status:
                            old_status_name = old_status.get('name', f'ID: {old_status_id}')
                        
                        # Находим новый статус
                        new_status = next((s for s in refs['order_statuses'] if s['id'] == status_id), None)
                        if new_status:
                            new_status_name = new_status.get('name', f'ID: {status_id}')
                        
                        changes['status'] = {
                            'old_id': old_status_id,
                            'old_name': old_status_name,
                            'new_id': status_id,
                            'new_name': new_status_name
                        }
                    # Сравниваем manager_id с учетом None и типов
                    old_manager_id = order_data['order'].get('manager_id')
                    # Нормализуем типы для сравнения
                    old_manager_id_normalized = int(old_manager_id) if old_manager_id is not None else None
                    manager_id_normalized = int(manager_id) if manager_id is not None else None
                    logger.debug(f"Сравнение manager_id: старое={old_manager_id_normalized} (тип: {type(old_manager_id_normalized)}), новое={manager_id_normalized} (тип: {type(manager_id_normalized)})")
                    if manager_id_normalized != old_manager_id_normalized:
                        old_manager = next((m for m in refs['managers'] if m['id'] == old_manager_id_normalized), None) if old_manager_id_normalized else None
                        new_manager = next((m for m in refs['managers'] if m['id'] == manager_id_normalized), None) if manager_id_normalized else None
                        changes['manager'] = {
                            'old_id': old_manager_id_normalized,
                            'old_name': old_manager.get('name') if old_manager else 'Не назначен',
                            'new_id': manager_id_normalized,
                            'new_name': new_manager.get('name') if new_manager else 'Не назначен'
                        }
                        logger.debug(f"Обнаружено изменение manager: '{old_manager.get('name') if old_manager else 'Не назначен'}' -> '{new_manager.get('name') if new_manager else 'Не назначен'}'")
                    
                    # Сравниваем master_id с учетом None и типов
                    old_master_id = order_data['order'].get('master_id')
                    # Нормализуем типы для сравнения
                    old_master_id_normalized = int(old_master_id) if old_master_id is not None else None
                    master_id_normalized = int(master_id) if master_id is not None else None
                    logger.debug(f"Сравнение master_id: старое={old_master_id_normalized} (тип: {type(old_master_id_normalized)}), новое={master_id_normalized} (тип: {type(master_id_normalized)})")
                    if master_id_normalized != old_master_id_normalized:
                        old_master = next((m for m in refs['masters'] if m['id'] == old_master_id_normalized), None) if old_master_id_normalized else None
                        new_master = next((m for m in refs['masters'] if m['id'] == master_id_normalized), None) if master_id_normalized else None
                        changes['master'] = {
                            'old_id': old_master_id_normalized,
                            'old_name': old_master.get('name') if old_master else 'Не назначен',
                            'new_id': master_id_normalized,
                            'new_name': new_master.get('name') if new_master else 'Не назначен'
                        }
                        logger.debug(f"Обнаружено изменение master: '{old_master.get('name') if old_master else 'Не назначен'}' -> '{new_master.get('name') if new_master else 'Не назначен'}'")
                    if prepayment != str(order_data['order'].get('prepayment', 0)):
                        changes['prepayment'] = {'old': order_data['order'].get('prepayment'), 'new': prepayment}
                    
                    # Дополнительные поля для отслеживания
                    old_model = order_data['order'].get('model') or ''
                    if model != old_model:
                        changes['model'] = {'old': old_model or '—', 'new': model or '—'}
                    
                    # Сравниваем symptom_tags (нормализуем для сравнения - сортируем теги)
                    old_symptom_tags_raw = (order_data['order'].get('symptom_tags') or '').strip()
                    new_symptom_tags_raw = symptom_tags.strip() if symptom_tags else ''
                    # Нормализуем: разбиваем по запятым/точкам с запятой, убираем пробелы, сортируем
                    old_symptom_list = sorted([t.strip() for t in re.split(r'[,;\n\r]+', old_symptom_tags_raw) if t.strip()])
                    new_symptom_list = sorted([t.strip() for t in re.split(r'[,;\n\r]+', new_symptom_tags_raw) if t.strip()])
                    old_symptom_tags_normalized = ', '.join(old_symptom_list)
                    new_symptom_tags_normalized = ', '.join(new_symptom_list)
                    if old_symptom_tags_normalized != new_symptom_tags_normalized:
                        changes['symptom_tags'] = {'old': old_symptom_tags_raw or '—', 'new': new_symptom_tags_raw or '—'}
                        logger.debug(f"Обнаружено изменение symptom_tags: '{old_symptom_tags_raw}' -> '{new_symptom_tags_raw}'")
                    
                    # Сравниваем appearance (нормализуем для сравнения - сортируем теги)
                    old_appearance_raw = (order_data['order'].get('appearance') or '').strip()
                    new_appearance_raw = appearance.strip() if appearance else ''
                    # Нормализуем: разбиваем по запятым/точкам с запятой, убираем пробелы, сортируем
                    old_appearance_list = sorted([t.strip() for t in re.split(r'[,;\n\r]+', old_appearance_raw) if t.strip()])
                    new_appearance_list = sorted([t.strip() for t in re.split(r'[,;\n\r]+', new_appearance_raw) if t.strip()])
                    old_appearance_normalized = ', '.join(old_appearance_list)
                    new_appearance_normalized = ', '.join(new_appearance_list)
                    if old_appearance_normalized != new_appearance_normalized:
                        changes['appearance'] = {'old': old_appearance_raw or '—', 'new': new_appearance_raw or '—'}
                        logger.debug(f"Обнаружено изменение appearance: '{old_appearance_raw}' -> '{new_appearance_raw}'")
                    
                    old_password = order_data['order'].get('password') or ''
                    if password != old_password:
                        changes['password'] = {'old': '***' if old_password else '—', 'new': '***' if password else '—'}
                    
                    old_comment = order_data['order'].get('comment') or ''
                    if comment != old_comment:
                        changes['comment'] = {'old': (old_comment[:50] + '...' if len(old_comment) > 50 else old_comment) or '—', 
                                              'new': (comment[:50] + '...' if len(comment) > 50 else comment) or '—'}
                    
                    old_serial = order_data['device'].get('serial_number') or ''
                    if serial_number != old_serial:
                        changes['serial_number'] = {'old': old_serial or '—', 'new': serial_number or '—'}
                    
                    old_device_type_id = order_data['device'].get('device_type_id')
                    # Нормализуем типы для сравнения
                    old_device_type_id_normalized = int(old_device_type_id) if old_device_type_id is not None else None
                    device_type_id_normalized = int(device_type_id) if device_type_id is not None else None
                    logger.info(f"Сравнение device_type_id: старое={old_device_type_id_normalized} (тип: {type(old_device_type_id_normalized)}), новое={device_type_id_normalized} (тип: {type(device_type_id_normalized)})")
                    # Логируем только если действительно было изменение (оба значения не None и они разные)
                    if device_type_id_normalized != old_device_type_id_normalized and old_device_type_id_normalized is not None and device_type_id_normalized is not None:
                        old_type = next((dt for dt in refs['device_types'] if dt['id'] == old_device_type_id_normalized), None) if old_device_type_id_normalized else None
                        new_type = next((dt for dt in refs['device_types'] if dt['id'] == device_type_id_normalized), None) if device_type_id_normalized else None
                        changes['device_type'] = {
                            'old': old_type.get('name') if old_type else '—',
                            'new': new_type.get('name') if new_type else '—'
                        }
                        logger.debug(f"Обнаружено изменение device_type: '{old_type.get('name') if old_type else '—'}' -> '{new_type.get('name') if new_type else '—'}'")
                    
                    old_device_brand_id = order_data['device'].get('device_brand_id')
                    # Нормализуем типы для сравнения
                    old_device_brand_id_normalized = int(old_device_brand_id) if old_device_brand_id is not None else None
                    device_brand_id_normalized = int(device_brand_id) if device_brand_id is not None else None
                    logger.info(f"Сравнение device_brand_id: старое={old_device_brand_id_normalized} (тип: {type(old_device_brand_id_normalized)}), новое={device_brand_id_normalized} (тип: {type(device_brand_id_normalized)})")
                    # Логируем только если действительно было изменение (оба значения не None и они разные)
                    if device_brand_id_normalized != old_device_brand_id_normalized and old_device_brand_id_normalized is not None and device_brand_id_normalized is not None:
                        old_brand = next((db for db in refs['device_brands'] if db['id'] == old_device_brand_id_normalized), None) if old_device_brand_id_normalized else None
                        new_brand = next((db for db in refs['device_brands'] if db['id'] == device_brand_id_normalized), None) if device_brand_id_normalized else None
                        changes['device_brand'] = {
                            'old': old_brand.get('name') if old_brand else '—',
                            'new': new_brand.get('name') if new_brand else '—'
                        }
                        logger.debug(f"Обнаружено изменение device_brand: '{old_brand.get('name') if old_brand else '—'}' -> '{new_brand.get('name') if new_brand else '—'}'")
                    
                    # Также логируем изменения клиента
                    old_client_name = order_data['customer'].get('name') or ''
                    if client_name != old_client_name:
                        changes['client_name'] = {'old': old_client_name or '—', 'new': client_name}
                    
                    old_phone = order_data['customer'].get('phone') or ''
                    if phone != old_phone:
                        changes['phone'] = {'old': old_phone or '—', 'new': phone}
                    
                    old_email = order_data['customer'].get('email') or ''
                    if email != old_email:
                        changes['email'] = {'old': old_email or '—', 'new': email or '—'}
                    
                    # Фильтруем пустые изменения - проверяем, что есть реальные изменения
                    # Исключаем служебные поля и пустые значения
                    excluded_keys = ['order_uuid', 'field', 'created_via', 'comment_id', 'old_id', 'new_id', 'customer', 'device']
                    filtered_changes = {}
                    for key, value in changes.items():
                        if key in excluded_keys:
                            continue
                        # Пропускаем пустые значения или значения, где old и new одинаковы
                        if isinstance(value, dict):
                            old_val = value.get('old') or value.get('old_name') or value.get('old_id')
                            new_val = value.get('new') or value.get('new_name') or value.get('new_id')
                            # Если оба значения пустые или одинаковые, пропускаем
                            if (not old_val or old_val == '—') and (not new_val or new_val == '—'):
                                logger.debug(f"Пропущено изменение {key}: оба значения пустые (old={old_val}, new={new_val})")
                                continue
                            if old_val == new_val:
                                logger.debug(f"Пропущено изменение {key}: значения одинаковые (old={old_val}, new={new_val})")
                                continue
                        # Если значение не словарь, проверяем что оно не пустое
                        elif not value or value == '—' or value == '':
                            logger.debug(f"Пропущено изменение {key}: значение пустое ({value})")
                            continue
                        filtered_changes[key] = value
                    
                    logger.info(f"Исходные изменения: {list(changes.keys())}, отфильтрованные: {list(filtered_changes.keys())}")
                    if changes:
                        logger.info(f"Детали исходных изменений: {changes}")
                    if filtered_changes:
                        logger.info(f"Детали отфильтрованных изменений: {filtered_changes}")
                    
                    # Логируем только если есть реальные изменения
                    if filtered_changes:
                        logger.info(f"Логирование изменений заявки #{order.id}: {list(filtered_changes.keys())}")
                        logger.debug(f"Детали изменений: {filtered_changes}")
                        ActionLogService.log_action(
                            user_id=user_id,
                            username=username,
                            action_type='update',
                            entity_type='order',
                            entity_id=order.id,
                            details=filtered_changes
                        )
                    else:
                        logger.info(f"Нет реальных изменений для логирования в заявке #{order.id} (исходных изменений: {len(changes)}, отфильтровано: {len(changes) - len(filtered_changes)})")
                        if changes:
                            logger.debug(f"Все изменения были отфильтрованы. Исходные изменения: {changes}")
                except Exception as e:
                    logger.error(f"Не удалось залогировать обновление заявки #{order.id}: {e}", exc_info=True)
                
                # Очищаем кэш
                clear_cache(key_prefix='order')
                clear_cache(key_prefix='customer')
                clear_cache(key_prefix='device')
                
                flash('Заявка успешно обновлена!', 'success')
                return redirect(url_for('orders.order_detail', order_id=order.order_id))
                
            except (ValidationError, NotFoundError, DatabaseError) as e:
                flash(f"Ошибка при обновлении заявки: {e}", 'error')
            except Exception as e:
                logger.exception("Неожиданная ошибка при обновлении заявки")
                flash("Произошла непредвиденная ошибка при обновлении заявки.", 'error')
        
        # Получаем обновленные данные после возможного обновления
        order_data = OrderService.get_order_full_data(order.id)
        
        # Форматируем телефон
        if order_data.get('customer') and order_data['customer'].get('phone'):
            order_data['customer']['phone_display'] = format_phone_display(order_data['customer']['phone'])
        
        # Получаем настройки для печати
        settings = SettingsService.get_general_settings()
        
        # Получаем историю заявки из action_logs
        from datetime import datetime
        import json
        
        order_history = []
        
        # Добавляем событие создания заявки
        if order_data['order'].get('created_at'):
            try:
                created_at_str = order_data['order']['created_at']
                if isinstance(created_at_str, str):
                    # Парсим дату
                    if ' ' in created_at_str and len(created_at_str) >= 19:
                        created_at = datetime.strptime(created_at_str[:19], '%Y-%m-%d %H:%M:%S')
                        # Уже в московском времени (если заявка создана после наших изменений)
                        # Для старых заявок можно было бы конвертировать, но оставляем как есть
                    else:
                        created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                        created_at = convert_to_moscow(created_at).replace(tzinfo=None)
                else:
                    created_at = created_at_str if isinstance(created_at_str, datetime) else get_moscow_now_naive()
                    if isinstance(created_at, datetime) and created_at.tzinfo:
                        created_at = convert_to_moscow(created_at).replace(tzinfo=None)
            except (ValueError, TypeError, AttributeError):
                created_at = get_moscow_now_naive()
            
            order_history.append({
                'date_str': created_at.strftime('%Y-%m-%d') if isinstance(created_at, datetime) else get_moscow_now_str('%Y-%m-%d'),
                'time_str': created_at.strftime('%H:%M') if isinstance(created_at, datetime) else get_moscow_now_str('%H:%M'),
                'datetime': created_at,
                'type': 'created',
                'icon': 'plus',
                'color': 'green',
                'title': 'Заявка создана',
                'description': f'Заявка #{order_data["order"]["id"]} создана',
                'username': None
            })
        
        # Множество для отслеживания уже обработанных смен статусов (по old_status_id, new_status_id)
        # Это поможет избежать дублирования при обработке action_logs
        processed_status_changes = set()
        
        # Получаем историю статусов из order_status_history
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT osh.*, 
                           os_old.name as old_status_name,
                           os_old.color as old_status_color,
                           os_new.name as new_status_name,
                           os_new.color as new_status_color
                    FROM order_status_history osh
                    LEFT JOIN order_statuses os_old ON os_old.id = osh.old_status_id
                    LEFT JOIN order_statuses os_new ON os_new.id = osh.new_status_id
                    WHERE osh.order_id = ?
                    ORDER BY osh.created_at ASC
                ''', (order.id,))
                
                status_history_rows = cursor.fetchall()
                logger.debug(f"Найдено записей в истории статусов для заявки #{order.id}: {len(status_history_rows)}")
                
                for row in status_history_rows:
                    try:
                        created_at_str = row['created_at']
                        if isinstance(created_at_str, str):
                            # Пробуем разные форматы даты
                            try:
                                # Формат SQLite: YYYY-MM-DD HH:MM:SS
                                if ' ' in created_at_str and len(created_at_str) >= 19:
                                    # Парсим как naive datetime (без часового пояса)
                                    status_created_at = datetime.strptime(created_at_str[:19], '%Y-%m-%d %H:%M:%S')
                                    # НОВЫЕ записи уже сохраняются в московском времени (UTC+3)
                                    # СТАРЫЕ записи были в UTC, их нужно конвертировать
                                    # Определяем по дате: если запись создана после 2025-12-27, считаем что уже в московском
                                    # Или просто не конвертируем - новые записи уже в московском
                                    # Для старых записей можно добавить проверку даты, но проще - не конвертировать вообще
                                    # так как теперь все новые записи сохраняются в московском времени
                                    # status_created_at уже в московском времени, не конвертируем
                                # ISO формат с Z
                                elif 'Z' in created_at_str:
                                    status_created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                                    status_created_at = convert_to_moscow(status_created_at).replace(tzinfo=None)
                                # ISO формат с +00:00
                                elif '+' in created_at_str or created_at_str.count('-') >= 3:
                                    status_created_at = datetime.fromisoformat(created_at_str)
                                    # Конвертируем в московское время, если есть информация о часовом поясе
                                    if status_created_at.tzinfo:
                                        status_created_at = convert_to_moscow(status_created_at).replace(tzinfo=None)
                                else:
                                    status_created_at = datetime.strptime(created_at_str, '%Y-%m-%d %H:%M:%S')
                                    # Уже в московском времени (новые записи), не конвертируем
                            except (ValueError, AttributeError) as e:
                                # Если не удалось распарсить, пробуем ISO формат
                                try:
                                    status_created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                                    status_created_at = convert_to_moscow(status_created_at).replace(tzinfo=None)
                                except (ValueError, TypeError, AttributeError):
                                    status_created_at = get_moscow_now_naive()
                        elif isinstance(created_at_str, datetime):
                            if created_at_str.tzinfo:
                                status_created_at = convert_to_moscow(created_at_str).replace(tzinfo=None)
                            else:
                                status_created_at = created_at_str
                        else:
                            status_created_at = get_moscow_now_naive()
                    except Exception as e:
                        logger.warning(f"Ошибка парсинга даты created_at для записи истории статуса: {e}, значение: {row.get('created_at')}")
                        status_created_at = get_moscow_now_naive()
                    
                    old_status_id_from_history = row['old_status_id']
                    new_status_id_from_history = row['new_status_id']
                    old_status_name = row['old_status_name'] or 'Не указан'
                    new_status_name = row['new_status_name'] or 'Не указан'
                    old_status_color = row['old_status_color'] or '#6c757d'
                    new_status_color = row['new_status_color'] or '#6c757d'
                    changed_by_username = row['changed_by_username'] or 'Система'
                    
                    # Отслеживаем обработанную смену статуса
                    status_change_key = (old_status_id_from_history, new_status_id_from_history)
                    processed_status_changes.add(status_change_key)
                    
                    date_str = status_created_at.strftime('%Y-%m-%d') if isinstance(status_created_at, datetime) else get_moscow_now_str('%Y-%m-%d')
                    time_str = status_created_at.strftime('%H:%M') if isinstance(status_created_at, datetime) else get_moscow_now_str('%H:%M')
                    
                    # Определяем цвет для иконки на основе нового статуса
                    status_color_class = 'primary'
                    if new_status_color:
                        # Преобразуем hex цвет в класс Bootstrap, если возможно
                        color_lower = new_status_color.lower()
                        if '#28a745' in color_lower or '#4caf50' in color_lower:
                            status_color_class = 'success'
                        elif '#dc3545' in color_lower or '#f44336' in color_lower:
                            status_color_class = 'danger'
                        elif '#17a2b8' in color_lower or '#00bcd4' in color_lower:
                            status_color_class = 'info'
                        elif '#ffc107' in color_lower or '#ff9800' in color_lower:
                            status_color_class = 'warning'
                    
                    order_history.append({
                        'date_str': date_str,
                        'time_str': time_str,
                        'datetime': status_created_at,
                        'type': 'status_change',
                        'icon': 'sync',
                        'color': status_color_class,
                        'title': 'Изменен статус',
                        'description': f'Статус изменен с "{old_status_name}" на "{new_status_name}"',
                        'old_status_name': old_status_name,
                        'old_status_color': old_status_color,
                        'new_status_name': new_status_name,
                        'new_status_color': new_status_color,
                        'username': changed_by_username
                    })
        except Exception as e:
            logger.error(f"Не удалось получить историю статусов из order_status_history для заявки #{order.id}: {e}", exc_info=True)
        
        # Получаем логи действий для заявки
        try:
            action_logs = ActionLogService.get_action_logs(
                entity_type='order',
                entity_id=order.id,
                page=1,
                per_page=1000
            ).items
            
            for log in action_logs:
                try:
                    log_created_at_str = log.get('created_at')
                    if isinstance(log_created_at_str, str):
                        # action_logs уже сохраняются в московском времени (UTC+3) через action_log_service
                        # Поэтому не нужно конвертировать - просто парсим как есть
                        if ' ' in log_created_at_str and len(log_created_at_str) >= 19:
                            # Формат SQLite: YYYY-MM-DD HH:MM:SS (уже в московском времени)
                            log_created_at = datetime.strptime(log_created_at_str[:19], '%Y-%m-%d %H:%M:%S')
                        else:
                            # ISO формат - может быть с часовым поясом
                            log_created_at = datetime.fromisoformat(log_created_at_str.replace('Z', '+00:00'))
                            if log_created_at.tzinfo:
                                log_created_at = convert_to_moscow(log_created_at).replace(tzinfo=None)
                    elif isinstance(log_created_at_str, datetime):
                        log_created_at = log_created_at_str
                        # action_logs уже сохраняются в московском времени
                        # Если datetime naive - уже в московском времени, не конвертируем
                        if log_created_at.tzinfo:
                            log_created_at = convert_to_moscow(log_created_at).replace(tzinfo=None)
                    else:
                        log_created_at = get_moscow_now_naive()
                except (ValueError, TypeError, AttributeError):
                    log_created_at = get_moscow_now_naive()
                
                action_type = log.get('action_type', '')
                details = log.get('details', {})
                if isinstance(details, str):
                    try:
                        details = json.loads(details)
                    except (json.JSONDecodeError, TypeError):
                        details = {}
                
                username = log.get('username', 'Система')
                date_str = log_created_at.strftime('%Y-%m-%d') if isinstance(log_created_at, datetime) else get_moscow_now_str('%Y-%m-%d')
                time_str = log_created_at.strftime('%H:%M') if isinstance(log_created_at, datetime) else get_moscow_now_str('%H:%M')
                
                # Обрабатываем разные типы действий
                # Пропускаем update_order_status, так как статусы уже получены из order_status_history
                if action_type == 'update_order_status':
                    # Статусы уже обработаны из order_status_history, пропускаем
                    continue
                elif action_type in ['add_service', 'remove_service']:
                    service_name = details.get('Услуга') or details.get('name') or 'Услуга'
                    quantity = details.get('Количество') or details.get('quantity') or 1
                    price = details.get('Цена') or details.get('price') or 0
                    try:
                        price_float = float(price) if price else 0
                    except (ValueError, TypeError):
                        price_float = 0
                    action_text = 'Добавлена услуга' if action_type == 'add_service' else 'Удалена услуга'
                    order_history.append({
                        'date_str': date_str,
                        'time_str': time_str,
                        'datetime': log_created_at,
                        'type': action_type,
                        'icon': 'plus' if action_type == 'add_service' else 'minus',
                        'color': 'success' if action_type == 'add_service' else 'danger',
                        'title': action_text,
                        'description': f'{service_name} (количество: {quantity} шт., цена: {price_float:.2f} ₽)',
                        'username': username
                    })
                elif action_type in ['add_part', 'remove_part']:
                    part_name = details.get('Товар') or details.get('name') or 'Товар'
                    quantity = details.get('Количество') or details.get('quantity') or 1
                    price = details.get('Цена') or details.get('price') or 0
                    try:
                        price_float = float(price) if price else 0
                    except (ValueError, TypeError):
                        price_float = 0
                    action_text = 'Добавлен товар' if action_type == 'add_part' else 'Удален товар'
                    order_history.append({
                        'date_str': date_str,
                        'time_str': time_str,
                        'datetime': log_created_at,
                        'type': action_type,
                        'icon': 'plus' if action_type == 'add_part' else 'minus',
                        'color': 'success' if action_type == 'add_part' else 'danger',
                        'title': action_text,
                        'description': f'{part_name} (количество: {quantity} шт., цена: {price_float:.2f} ₽)',
                        'username': username
                    })
                elif action_type == 'update':
                    # Обработка изменения статуса из action_logs (если его еще нет в order_status_history)
                    # Это нужно для старых записей, которые были созданы до внедрения order_status_history
                    if 'status' in details:
                        status_info = details.get('status', {})
                        if isinstance(status_info, dict):
                            old_status_id_log = status_info.get('old_id')
                            new_status_id_log = status_info.get('new_id')
                            old_status_name_log = status_info.get('old_name') or 'Не указан'
                            new_status_name_log = status_info.get('new_name') or 'Не указан'
                            
                            # Проверяем, не обработана ли уже эта смена статуса из order_status_history
                            status_change_key = (old_status_id_log, new_status_id_log)
                            if status_change_key not in processed_status_changes:
                                # Получаем цвета статусов для отображения
                                statuses = ReferenceService.get_order_statuses()
                                old_status_color_log = '#6c757d'
                                new_status_color_log = '#6c757d'
                                
                                if old_status_id_log:
                                    old_status_obj = next((s for s in statuses if s['id'] == old_status_id_log), None)
                                    if old_status_obj:
                                        old_status_color_log = old_status_obj.get('color', '#6c757d')
                                
                                if new_status_id_log:
                                    new_status_obj = next((s for s in statuses if s['id'] == new_status_id_log), None)
                                    if new_status_obj:
                                        new_status_color_log = new_status_obj.get('color', '#6c757d')
                                
                                # Определяем цвет для иконки на основе нового статуса
                                status_color_class = 'primary'
                                if new_status_color_log:
                                    color_lower = new_status_color_log.lower()
                                    if '#28a745' in color_lower or '#4caf50' in color_lower:
                                        status_color_class = 'success'
                                    elif '#dc3545' in color_lower or '#f44336' in color_lower:
                                        status_color_class = 'danger'
                                    elif '#17a2b8' in color_lower or '#00bcd4' in color_lower:
                                        status_color_class = 'info'
                                    elif '#ffc107' in color_lower or '#ff9800' in color_lower:
                                        status_color_class = 'warning'
                                
                                order_history.append({
                                    'date_str': date_str,
                                    'time_str': time_str,
                                    'datetime': log_created_at,
                                    'type': 'status_change',
                                    'icon': 'sync',
                                    'color': status_color_class,
                                    'title': 'Изменен статус',
                                    'description': f'Статус изменен с "{old_status_name_log}" на "{new_status_name_log}"',
                                    'old_status_name': old_status_name_log,
                                    'old_status_color': old_status_color_log,
                                    'new_status_name': new_status_name_log,
                                    'new_status_color': new_status_color_log,
                                    'username': username
                                })
                                # Отслеживаем обработанную смену статуса
                                processed_status_changes.add(status_change_key)
                                logger.debug(f"Добавлена смена статуса из action_logs для заявки #{order.id}: {old_status_name_log} -> {new_status_name_log}")
                    
                    # Обработка изменения менеджера
                    if 'manager' in details or 'Менеджер' in details:
                        manager_info = details.get('manager') or details.get('Менеджер') or {}
                        if isinstance(manager_info, dict):
                            old_name = manager_info.get('old_name') or manager_info.get('old') or 'Не назначен'
                            new_name = manager_info.get('new_name') or manager_info.get('new') or 'Не назначен'
                            order_history.append({
                                'date_str': date_str,
                                'time_str': time_str,
                                'datetime': log_created_at,
                                'type': 'manager_change',
                                'icon': 'user-tie',
                                'color': 'info',
                                'title': 'Изменен менеджер',
                                'description': f'Менеджер изменен с "{old_name}" на "{new_name}"',
                                'username': username
                            })
                    
                    # Обработка изменения мастера
                    if 'master' in details or 'Мастер' in details:
                        master_info = details.get('master') or details.get('Мастер') or {}
                        if isinstance(master_info, dict):
                            old_name = master_info.get('old_name') or master_info.get('old') or 'Не назначен'
                            new_name = master_info.get('new_name') or master_info.get('new') or 'Не назначен'
                            order_history.append({
                                'date_str': date_str,
                                'time_str': time_str,
                                'datetime': log_created_at,
                                'type': 'master_change',
                                'icon': 'wrench',
                                'color': 'warning',
                                'title': 'Изменен мастер',
                                'description': f'Мастер изменен с "{old_name}" на "{new_name}"',
                                'username': username
                            })
                    
                    # Обработка изменения предоплаты
                    if 'prepayment' in details or 'Предоплата' in details:
                        prepayment_info = details.get('prepayment') or details.get('Предоплата') or {}
                        if isinstance(prepayment_info, dict):
                            old_val = prepayment_info.get('old') or '0'
                            new_val = prepayment_info.get('new') or '0'
                            order_history.append({
                                'date_str': date_str,
                                'time_str': time_str,
                                'datetime': log_created_at,
                                'type': 'prepayment_change',
                                'icon': 'money-bill-wave',
                                'color': 'success',
                                'title': 'Изменена предоплата',
                                'description': f'Предоплата изменена с {old_val} ₽ на {new_val} ₽',
                                'username': username
                            })
                    
                    # Обработка изменения модели устройства
                    if 'model' in details or 'Модель' in details:
                        model_info = details.get('model') or details.get('Модель') or {}
                        if isinstance(model_info, dict):
                            old_val = model_info.get('old') or '—'
                            new_val = model_info.get('new') or '—'
                            order_history.append({
                                'date_str': date_str,
                                'time_str': time_str,
                                'datetime': log_created_at,
                                'type': 'model_change',
                                'icon': 'laptop',
                                'color': 'secondary',
                                'title': 'Изменена модель',
                                'description': f'Модель изменена с "{old_val}" на "{new_val}"',
                                'username': username
                            })
                    
                    # Обработка изменения неисправности
                    if 'symptom_tags' in details or 'Неисправность' in details:
                        symptom_info = details.get('symptom_tags') or details.get('Неисправность') or {}
                        if isinstance(symptom_info, dict):
                            old_val = symptom_info.get('old') or '—'
                            new_val = symptom_info.get('new') or '—'
                            if old_val != new_val:
                                order_history.append({
                                    'date_str': date_str,
                                    'time_str': time_str,
                                    'datetime': log_created_at,
                                    'type': 'symptom_change',
                                    'icon': 'exclamation-triangle',
                                    'color': 'warning',
                                    'title': 'Изменена неисправность',
                                    'description': f'С "{old_val}" на "{new_val}"',
                                    'username': username
                                })
                    
                    # Обработка изменения внешнего вида
                    if 'appearance' in details or 'Внешний вид' in details:
                        appearance_info = details.get('appearance') or details.get('Внешний вид') or {}
                        if isinstance(appearance_info, dict):
                            old_val = appearance_info.get('old') or '—'
                            new_val = appearance_info.get('new') or '—'
                            if old_val != new_val:
                                order_history.append({
                                    'date_str': date_str,
                                    'time_str': time_str,
                                    'datetime': log_created_at,
                                    'type': 'appearance_change',
                                    'icon': 'paint-brush',
                                    'color': 'secondary',
                                    'title': 'Изменен внешний вид',
                                    'description': f'С "{old_val}" на "{new_val}"',
                                    'username': username
                                })
                    
                    # Обработка изменения пароля
                    if 'password' in details or 'Пароль' in details:
                        password_info = details.get('password') or details.get('Пароль') or {}
                        if isinstance(password_info, dict):
                            old_val = password_info.get('old') or '—'
                            new_val = password_info.get('new') or '—'
                            if old_val != new_val:
                                order_history.append({
                                    'date_str': date_str,
                                    'time_str': time_str,
                                    'datetime': log_created_at,
                                    'type': 'password_change',
                                    'icon': 'key',
                                    'color': 'secondary',
                                    'title': 'Изменен пароль',
                                    'description': 'Пароль изменен',
                                    'username': username
                                })
                    
                    # Обработка изменения комментария
                    if 'comment' in details or 'Комментарий' in details:
                        comment_info = details.get('comment') or details.get('Комментарий') or {}
                        if isinstance(comment_info, dict):
                            old_val = comment_info.get('old') or '—'
                            new_val = comment_info.get('new') or '—'
                            if old_val != new_val:
                                order_history.append({
                                    'date_str': date_str,
                                    'time_str': time_str,
                                    'datetime': log_created_at,
                                    'type': 'comment_change',
                                    'icon': 'comment-dots',
                                    'color': 'info',
                                    'title': 'Изменен комментарий',
                                    'description': f'Комментарий обновлен',
                                    'username': username
                                })
                    
                    # Обработка изменения серийного номера
                    if 'serial_number' in details or 'Серийный номер' in details:
                        serial_info = details.get('serial_number') or details.get('Серийный номер') or {}
                        if isinstance(serial_info, dict):
                            old_val = serial_info.get('old') or '—'
                            new_val = serial_info.get('new') or '—'
                            if old_val != new_val:
                                order_history.append({
                                    'date_str': date_str,
                                    'time_str': time_str,
                                    'datetime': log_created_at,
                                    'type': 'serial_change',
                                    'icon': 'barcode',
                                    'color': 'secondary',
                                    'title': 'Изменен серийный номер',
                                    'description': f'С "{old_val}" на "{new_val}"',
                                    'username': username
                                })
                    
                    # Обработка изменения типа устройства
                    if 'device_type' in details or 'Тип устройства' in details:
                        device_type_info = details.get('device_type') or details.get('Тип устройства') or {}
                        if isinstance(device_type_info, dict):
                            old_val = device_type_info.get('old') or '—'
                            new_val = device_type_info.get('new') or '—'
                            if old_val != new_val:
                                order_history.append({
                                    'date_str': date_str,
                                    'time_str': time_str,
                                    'datetime': log_created_at,
                                    'type': 'device_type_change',
                                    'icon': 'mobile-alt',
                                    'color': 'info',
                                    'title': 'Изменен тип устройства',
                                    'description': f'С "{old_val}" на "{new_val}"',
                                    'username': username
                                })
                    
                    # Обработка изменения бренда устройства
                    if 'device_brand' in details or 'Бренд устройства' in details:
                        device_brand_info = details.get('device_brand') or details.get('Бренд устройства') or {}
                        if isinstance(device_brand_info, dict):
                            old_val = device_brand_info.get('old') or '—'
                            new_val = device_brand_info.get('new') or '—'
                            if old_val != new_val:
                                order_history.append({
                                    'date_str': date_str,
                                    'time_str': time_str,
                                    'datetime': log_created_at,
                                    'type': 'device_brand_change',
                                    'icon': 'tag',
                                    'color': 'info',
                                    'title': 'Изменен бренд устройства',
                                    'description': f'С "{old_val}" на "{new_val}"',
                                    'username': username
                                })
                    
                    # Обработка изменения имени клиента
                    if 'client_name' in details or 'Имя клиента' in details:
                        client_name_info = details.get('client_name') or details.get('Имя клиента') or {}
                        if isinstance(client_name_info, dict):
                            old_val = client_name_info.get('old') or '—'
                            new_val = client_name_info.get('new') or '—'
                            if old_val != new_val:
                                order_history.append({
                                    'date_str': date_str,
                                    'time_str': time_str,
                                    'datetime': log_created_at,
                                    'type': 'client_name_change',
                                    'icon': 'user',
                                    'color': 'secondary',
                                    'title': 'Изменено имя клиента',
                                    'description': f'С "{old_val}" на "{new_val}"',
                                    'username': username
                                })
                    
                    # Обработка изменения телефона
                    if 'phone' in details or 'Телефон' in details:
                        phone_info = details.get('phone') or details.get('Телефон') or {}
                        if isinstance(phone_info, dict):
                            old_val = phone_info.get('old') or '—'
                            new_val = phone_info.get('new') or '—'
                            if old_val != new_val:
                                order_history.append({
                                    'date_str': date_str,
                                    'time_str': time_str,
                                    'datetime': log_created_at,
                                    'type': 'phone_change',
                                    'icon': 'phone',
                                    'color': 'secondary',
                                    'title': 'Изменен телефон',
                                    'description': f'С "{old_val}" на "{new_val}"',
                                    'username': username
                                })
                    
                    # Обработка изменения email
                    if 'email' in details or 'Email' in details:
                        email_info = details.get('email') or details.get('Email') or {}
                        if isinstance(email_info, dict):
                            old_val = email_info.get('old') or '—'
                            new_val = email_info.get('new') or '—'
                            if old_val != new_val:
                                order_history.append({
                                    'date_str': date_str,
                                    'time_str': time_str,
                                    'datetime': log_created_at,
                                    'type': 'email_change',
                                    'icon': 'envelope',
                                    'color': 'secondary',
                                    'title': 'Изменен email',
                                    'description': f'С "{old_val}" на "{new_val}"',
                                'username': username
                            })
                elif action_type == 'add_payment':
                    amount = details.get('Сумма') or details.get('amount') or 0
                    payment_type = details.get('Тип оплаты') or details.get('payment_type') or 'Неизвестно'
                    order_history.append({
                        'date_str': date_str,
                        'time_str': time_str,
                        'datetime': log_created_at,
                        'type': 'payment',
                        'icon': 'money-bill',
                        'color': 'success',
                        'title': 'Добавлена оплата',
                        'description': f'Оплата {amount} ₽ ({payment_type})',
                        'username': username
                    })
                elif action_type == 'delete_payment':
                    # Получаем сумму - может быть строкой или числом
                    amount_str = details.get('Сумма')
                    amount_num = details.get('amount') or 0
                    
                    # Если есть строка с форматированием, используем её, иначе форматируем число
                    if amount_str:
                        amount_display = amount_str
                    else:
                        try:
                            amount_display = f"{float(amount_num):.2f} ₽"
                        except (ValueError, TypeError):
                            amount_display = f"{amount_num} ₽"
                    
                    payment_type = details.get('Тип оплаты') or details.get('payment_type') or 'Неизвестно'
                    order_history.append({
                        'date_str': date_str,
                        'time_str': time_str,
                        'datetime': log_created_at,
                        'type': 'payment_delete',
                        'icon': 'money-bill-wave',
                        'color': 'danger',
                        'title': 'Удалена оплата',
                        'description': f'Оплата {amount_display} ({payment_type})',
                        'username': username
                    })
                elif action_type == 'add_comment':
                    comment_text = details.get('Текст') or details.get('text') or 'Комментарий'
                    if len(comment_text) > 100:
                        comment_text = comment_text[:100] + '...'
                    order_history.append({
                        'date_str': date_str,
                        'time_str': time_str,
                        'datetime': log_created_at,
                        'type': 'comment',
                        'icon': 'comment',
                        'color': 'info',
                        'title': 'Добавлен комментарий',
                        'description': comment_text,
                        'username': username
                    })
        except Exception as e:
            logger.warning(f"Не удалось получить историю заявки: {e}")
        
        # Сортируем историю по дате и времени (от новых к старым)
        order_history.sort(key=lambda x: x['datetime'] if isinstance(x['datetime'], datetime) else get_moscow_now(), reverse=True)
        
        # Логируем итоговую статистику истории
        status_changes_count = sum(1 for event in order_history if event.get('type') == 'status_change')
        logger.debug(f"Итоговая статистика истории для заявки #{order.id}: всего событий={len(order_history)}, из них смен статуса={status_changes_count}")
        
        # Извлекаем totals для обратной совместимости с шаблоном
        totals = order_data.get('totals', {})
        order_services = order_data.get('services', [])
        order_parts = order_data.get('parts', [])

        # ===== Зарплата / прибыль (для отображения в карточке заявки) =====
        salary_profit = None
        salary_accruals = []
        salary_totals = {
            'master_cents': 0,
            'manager_cents': 0,
            'total_cents': 0
        }
        try:
            salary_profit = SalaryService.calculate_order_profit(order.id)
            salary_accruals = SalaryService.get_accruals_for_order(order.id) or []
            # Если у статуса заявки включено начисление зарплаты:
            # - создаем начисления при их отсутствии
            # - пересчитываем, если после последнего начисления были изменения по заявке
            if order_data['order'].get('status_id'):
                with get_db_connection() as conn:
                    cur = conn.cursor()
                    cur.execute(
                        'SELECT accrues_salary FROM order_statuses WHERE id = ?',
                        (order_data['order']['status_id'],)
                    )
                    row = cur.fetchone()
                    if row and row[0]:
                        try:
                            if not salary_accruals:
                                SalaryService.accrue_salary_for_order(order.id)
                                logger.info(f"Зарплата по заявке #{order.id} рассчитана при открытии карточки (начислений не было)")
                            elif SalaryService.order_changed_since_last_accrual(order.id):
                                SalaryService.accrue_salary_for_order(order.id, force_recalculate=True)
                                logger.info(f"Зарплата по заявке #{order.id} пересчитана при открытии карточки (обнаружены изменения)")
                            salary_accruals = SalaryService.get_accruals_for_order(order.id) or []
                        except Exception as accrue_e:
                            logger.warning(f"Не удалось автоматически начислить зарплату для заявки #{order.id}: {accrue_e}")
            for a in salary_accruals:
                amount_cents = int(a.get('amount_cents') or 0)
                salary_totals['total_cents'] += amount_cents
                if a.get('role') == 'master':
                    salary_totals['master_cents'] += amount_cents
                elif a.get('role') == 'manager':
                    salary_totals['manager_cents'] += amount_cents
        except Exception as e:
            logger.warning(f"Не удалось получить данные зарплаты/прибыли для заявки #{order.id}: {e}")
        
        # Проверяем блокировку редактирования на основе текущего статуса заявки
        blocks_edit = False
        is_final = False
        if order_data['order'].get('status_id'):
            try:
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT blocks_edit, is_final
                        FROM order_statuses
                        WHERE id = ?
                    ''', (order_data['order']['status_id'],))
                    status_row = cursor.fetchone()
                    if status_row:
                        blocks_edit = bool(status_row[0])
                        is_final = bool(status_row[1])
                        # Если статус финальный, также блокируем редактирование
                        if is_final:
                            blocks_edit = True
            except Exception as e:
                logger.warning(f"Не удалось проверить блокировку редактирования для заявки #{order.id}: {e}")

        # ===== Шаблон печати для клиента (из настроек «Формы для печати») =====
        # Берём шаблон без кэша, чтобы всегда использовать актуальный из /settings
        customer_template_rendered = None
        sales_receipt_template_rendered = None
        work_act_template_rendered = None
        try:
            tpl = SettingsService.get_print_template_fresh('customer')
            html_content = (tpl or {}).get('html_content') if isinstance(tpl, dict) else None
            sales_tpl = SettingsService.get_print_template_fresh('sales_receipt')
            sales_html = (sales_tpl or {}).get('html_content') if isinstance(sales_tpl, dict) else None
            work_tpl = SettingsService.get_print_template_fresh('work_act')
            work_html = (work_tpl or {}).get('html_content') if isinstance(work_tpl, dict) else None
            logger.debug(f"Шаблон печати для заявки #{order.id}: tpl={tpl is not None}, html_content={'есть' if html_content else 'нет'}")
            if (
                (html_content and isinstance(html_content, str) and html_content.strip()) or
                (sales_html and isinstance(sales_html, str) and sales_html.strip()) or
                (work_html and isinstance(work_html, str) and work_html.strip())
            ):
                # Источник переменных — данные заявки/клиента/устройства + общие настройки
                order_obj = order_data.get('order') or {}
                customer_obj = order_data.get('customer') or {}
                device_obj = order_data.get('device') or {}

                def _safe(v) -> str:
                    return _html.escape("" if v is None else str(v))

                try:
                    logo_max_width = int(settings.get('logo_max_width') or 320)
                except (TypeError, ValueError):
                    logo_max_width = 320
                try:
                    logo_max_height = int(settings.get('logo_max_height') or 120)
                except (TypeError, ValueError):
                    logo_max_height = 120

                raw_logo_url = (settings.get('logo_url') or '').strip()
                # Печать идет из about:blank, поэтому logo_url нужен абсолютный.
                if raw_logo_url and re.match(r'^https?://', raw_logo_url, flags=re.IGNORECASE):
                    logo_url = url_for('orders.print_logo_proxy', _external=True)
                elif raw_logo_url:
                    logo_url = urljoin(request.url_root, raw_logo_url.lstrip('/'))
                else:
                    logo_url = raw_logo_url

                # Базовые переменные
                values = {
                    # Организация
                    'COMPANY_NAME': _safe(settings.get('org_name') or ''),
                    'branch.address': _safe(settings.get('address') or ''),
                    'branch.phone': _safe(settings.get('phone') or ''),
                    'COMPANY_REQUISITES': _safe(" ".join([p for p in [
                        f"ИНН: {settings.get('inn')}" if settings.get('inn') else "",
                        f"ОГРН: {settings.get('ogrn')}" if settings.get('ogrn') else "",
                    ] if p]).strip()),

                    # Заявка
                    'ORDER_NUMBER': _safe(f"#{order_obj.get('id')}" if order_obj.get('id') else ''),
                    'ORDER_ID': _safe(order_obj.get('id') or ''),
                    'ORDER_UUID': _safe(order_obj.get('order_id') or ''),
                    'STATUS_NAME': _safe(order_obj.get('status_name') or ''),

                    # Клиент
                    'CLIENT_NAME': _safe(order_obj.get('client_name') or customer_obj.get('name') or ''),
                    'CLIENT_PHONE1': _safe(order_obj.get('phone_display') or order_obj.get('phone') or customer_obj.get('phone_display') or customer_obj.get('phone') or ''),
                    'CLIENT_PHONE': _safe(order_obj.get('phone') or customer_obj.get('phone') or ''),
                    'CLIENT_EMAIL': _safe(order_obj.get('email') or customer_obj.get('email') or ''),

                    # Оплата (форматируем как денежную сумму)
                    'TOTAL_PAID': _safe(f"{totals.get('paid', 0):.2f}" if isinstance(totals, dict) and totals.get('paid') else "0.00"),

                    # Мастер
                    'ENGINEER_NAME': _safe(order_obj.get('master_name') or ''),
                    'MASTER_NAME': _safe(order_obj.get('master_name') or ''),
                    
                    # Менеджер
                    'MANAGER_NAME': _safe(order_obj.get('manager_name') or ''),
                    # Валюта и сотрудник для чека
                    'CURRENCY': _safe('₽'),
                    'EMPLOYEE_NAME': _safe(order_obj.get('master_name') or order_obj.get('manager_name') or ''),
                    'COMPANY_LOGO_URL': _safe(logo_url),
                    'COMPANY_LOGO_STYLE': _safe(
                        f"max-width: {logo_max_width}px; max-height: {logo_max_height}px; width: auto; height: auto;"
                    ),
                }

                # Список позиций для товарного чека (ITEMS): услуги + товары
                print_items = []
                total_items_sum = 0.0
                for idx, s in enumerate(order_services or [], 1):
                    qty = int(s.get('quantity') or 1)
                    price = float(s.get('price') or s.get('service_price') or 0)
                    discount_val = float(s.get('discount_value') or 0)
                    discount_type = (s.get('discount_type') or '').strip().lower()
                    if discount_type == 'percent' and discount_val:
                        discount_amount = round(price * qty * discount_val / 100.0, 2)
                    elif discount_type == 'fixed':
                        discount_amount = min(round(discount_val * qty, 2), round(price * qty, 2))
                    else:
                        discount_amount = 0.0
                    row_sum = round(price * qty - discount_amount, 2)
                    total_items_sum += row_sum
                    print_items.append({
                        'INDEX': _safe(str(idx)),
                        'ITEM_NAME': _safe(s.get('name') or s.get('service_name') or ''),
                        'ITEM_SKU': _safe(''),
                        'ITEM_WARRANTY': _safe(str(s.get('warranty_days') or '')),
                        'ITEM_PRICE': _safe(f"{price:.2f}"),
                        'ITEM_DISCOUNT': _safe(f"{discount_amount:.2f}"),
                        'ITEM_QUANTITY': _safe(str(qty)),
                        'ITEM_SUM': _safe(f"{row_sum:.2f}"),
                    })
                for idx, p in enumerate(order_parts or [], len(print_items) + 1):
                    qty = int(p.get('quantity') or 1)
                    price = float(p.get('price') or 0)
                    discount_val = float(p.get('discount_value') or 0)
                    discount_type = (p.get('discount_type') or '').strip().lower()
                    if discount_type == 'percent' and discount_val:
                        discount_amount = round(price * qty * discount_val / 100.0, 2)
                    elif discount_type == 'fixed':
                        discount_amount = min(round(discount_val * qty, 2), round(price * qty, 2))
                    else:
                        discount_amount = 0.0
                    row_sum = round(price * qty - discount_amount, 2)
                    total_items_sum += row_sum
                    print_items.append({
                        'INDEX': _safe(str(idx)),
                        'ITEM_NAME': _safe(p.get('name') or p.get('part_name') or ''),
                        'ITEM_SKU': _safe(p.get('part_number') or ''),
                        'ITEM_WARRANTY': _safe(str(p.get('warranty_days') or '')),
                        'ITEM_PRICE': _safe(f"{price:.2f}"),
                        'ITEM_DISCOUNT': _safe(f"{discount_amount:.2f}"),
                        'ITEM_QUANTITY': _safe(str(qty)),
                        'ITEM_SUM': _safe(f"{row_sum:.2f}"),
                    })
                values['TOTAL_ITEMS'] = _safe(f"{total_items_sum:.2f}")

                # Дата/время
                try:
                    from datetime import datetime as _dt
                    now = _dt.now()
                    # Форматируем дату в читаемый формат ДД.ММ.ГГГГ
                    values['DATE_TODAY'] = _safe(now.strftime('%d.%m.%Y'))
                    values['TIME_NOW'] = _safe(now.strftime('%H:%M'))
                except Exception:
                    values['DATE_TODAY'] = ''
                    values['TIME_NOW'] = ''

                # created_at в человекочитаемом виде
                created_at_val = order_obj.get('created_at')
                if created_at_val:
                    try:
                        from datetime import datetime as _dt
                        # Пробуем разные форматы
                        date_str = str(created_at_val).strip()
                        formatted = None
                        for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d']:
                            try:
                                dt = _dt.strptime(date_str[:19] if len(date_str) >= 19 else date_str, fmt)
                                if ' ' in date_str or 'T' in date_str:
                                    formatted = dt.strftime('%d.%m.%Y %H:%M:%S')
                                else:
                                    formatted = dt.strftime('%d.%m.%Y')
                                break
                            except ValueError:
                                continue
                        if not formatted and len(date_str) >= 10:
                            # Пробуем взять первые 10 символов
                            try:
                                dt = _dt.strptime(date_str[:10], '%Y-%m-%d')
                                formatted = dt.strftime('%d.%m.%Y')
                            except ValueError:
                                pass
                        values['CREATED_AT'] = _safe(formatted or date_str)
                    except Exception:
                        values['CREATED_AT'] = _safe(str(created_at_val))
                else:
                    values['CREATED_AT'] = ''

                # UUID-теги устройства из UI настроек (в т.ч. Модель — UUID из шаблона настроек)
                values.update({
                    '701809f9-23dc-4346-aff4-0aef32523aef': _safe(order_obj.get('device_type_name') or device_obj.get('device_type') or ''),
                    'b6a8f943-e1b0-46e8-a321-b25fcfaf6976': _safe(order_obj.get('device_brand_name') or device_obj.get('device_brand') or ''),
                    'c5286c7d-44aa-4579-8258-935b003998cf': _safe(order_obj.get('serial_number') or device_obj.get('serial_number') or ''),
                    'c76b5bc7-7a68-4672-9542-cabaf2962600': _safe(order_obj.get('model') or ''),  # Модель (UUID из формы настроек)
                    'bc1ae9b1-7b8b-4da6-add5-26982865629e': _safe(order_obj.get('appearance') or ''),
                    'f93f4677-15b5-4e57-97e7-a345cb5b0e21': _safe(order_obj.get('symptom_tags') or ''),
                    'dfd7aa33-fd89-462a-bbbc-39c1550415da': _safe(''),  # Комплектация - пока пусто
                })
                
                # Дополнительные переменные
                try:
                    prepayment_val = float(order_obj.get('prepayment', 0) or 0)
                    values['PREPAYMENT'] = _safe(f"{prepayment_val:.2f}")
                except (ValueError, TypeError):
                    values['PREPAYMENT'] = _safe("0.00")
                
                values.update({
                    'MODEL': _safe(order_obj.get('model') or ''),
                    'COMMENT': _safe(order_obj.get('comment') or ''),
                })

                # Сумма прописью (для шаблона из настроек)
                try:
                    paid_val = float(totals.get('paid', 0) or 0)
                    values['total.paid.words'] = _safe(_amount_to_words_ru(paid_val))
                    prep_for_words = float(order_obj.get('prepayment', 0) or 0)
                    values['PREPAYMENT_WORDS'] = _safe(_amount_to_words_ru(prep_for_words))
                except (ValueError, TypeError):
                    values['total.paid.words'] = ''
                    values['PREPAYMENT_WORDS'] = ''

                # Ссылка на статус заказа (QR) и штрих-код номера заказа
                try:
                    order_uuid = order_obj.get('order_id') or ''
                    if order_uuid:
                        values['ticket.status.qrcode'] = _safe(url_for('orders.order_detail', order_id=order_uuid, _external=True))
                    else:
                        values['ticket.status.qrcode'] = ''
                except Exception:
                    values['ticket.status.qrcode'] = ''
                values['ticket.numberId.barcode'] = _safe(order_obj.get('order_id') or str(order_obj.get('id') or ''))

                def _render_print_html(template_html: str) -> str:
                    # Разворачиваем цикл data-for="ITEMS"
                    data_for_items = re.search(
                        r'<(\w+)[^>]*\s+data-for\s*=\s*["\']ITEMS["\'][^>]*>(.*?)</\1>',
                        template_html,
                        re.IGNORECASE | re.DOTALL
                    )
                    if data_for_items:
                        tag_name = data_for_items.group(1)
                        row_html = data_for_items.group(2)
                        rows = []
                        for item_vals in print_items:
                            line = row_html
                            for key, val in item_vals.items():
                                line = re.sub(
                                    r'<var-inline[^>]*\s+data-var\s*=\s*["\']' + re.escape(key) + r'["\'][^>]*>.*?</var-inline>',
                                    (lambda _m, _val=val: _val),
                                    line,
                                    flags=re.IGNORECASE | re.DOTALL
                                )
                                line = line.replace(f'##{key}##', val)
                            rows.append(f'<{tag_name}>{line}</{tag_name}>')
                        replacement = ''.join(rows)
                        template_html = template_html[:data_for_items.start()] + replacement + template_html[data_for_items.end():]

                    # Рендерим <var-inline data-var="...">...</var-inline>
                    def _replace_var_inline(m: re.Match) -> str:
                        var_name = m.group(1)
                        return values.get(var_name, '')

                    rendered_html = template_html
                    _var_inline_patterns = [
                        r'<var-inline[^>]*\s+data-var\s*=\s*"([^"]+)"[^>]*>.*?</var-inline>',
                        r"<var-inline[^>]*\s+data-var\s*=\s*'([^']+)'[^>]*>.*?</var-inline>",
                    ]
                    for _pattern in _var_inline_patterns:
                        prev = None
                        while prev != rendered_html:
                            prev = rendered_html
                            rendered_html = re.sub(
                                _pattern,
                                _replace_var_inline,
                                rendered_html,
                                flags=re.IGNORECASE | re.DOTALL
                            )

                    # Затем заменяем формат ##TAG##
                    def _replace_hash_tag(m: re.Match) -> str:
                        var_name = m.group(1)
                        return values.get(var_name, f'##{var_name}##')

                    rendered_html = re.sub(
                        r'##([A-Za-z_][A-Za-z0-9_.-]*)##',
                        _replace_hash_tag,
                        rendered_html
                    )

                    uuid_tags_list = [
                        '701809f9-23dc-4346-aff4-0aef32523aef', 'b6a8f943-e1b0-46e8-a321-b25fcfaf6976',
                        'c5286c7d-44aa-4579-8258-935b003998cf', 'c76b5bc7-7a68-4672-9542-cabaf2962600',
                        'bc1ae9b1-7b8b-4da6-add5-26982865629e', 'f93f4677-15b5-4e57-97e7-a345cb5b0e21',
                        'dfd7aa33-fd89-462a-bbbc-39c1550415da'
                    ]
                    for uuid_tag in uuid_tags_list:
                        if uuid_tag in values:
                            rendered_html = rendered_html.replace(f'##{uuid_tag}##', values[uuid_tag])
                            rendered_html = rendered_html.replace(f'##{uuid_tag.upper()}##', values[uuid_tag])

                    # Fallback: если logo img не содержит style, добавим ограничения из настроек.
                    logo_url_safe = values.get('COMPANY_LOGO_URL', '')
                    logo_style_safe = values.get('COMPANY_LOGO_STYLE', '')
                    if logo_url_safe and logo_style_safe:
                        def _ensure_logo_style(match: re.Match) -> str:
                            img_tag = match.group(0)
                            if re.search(r'\sstyle\s*=', img_tag, flags=re.IGNORECASE):
                                return img_tag
                            return img_tag[:-1] + f' style="{logo_style_safe}">'

                        rendered_html = re.sub(
                            r'<img\b[^>]*\bsrc\s*=\s*["\']' + re.escape(logo_url_safe) + r'["\'][^>]*>',
                            _ensure_logo_style,
                            rendered_html,
                            flags=re.IGNORECASE
                        )
                    # Санитизация перед выводом (защита от XSS)
                    try:
                        from bleach import clean
                        rendered_html = clean(
                            rendered_html,
                            tags=['p', 'table', 'tbody', 'tr', 'td', 'th', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                                  'strong', 'em', 'u', 'ol', 'ul', 'li', 'br', 'img', 'span', 'div', 'var-inline'],
                            attributes={'*': ['style', 'class', 'width', 'height', 'border', 'colspan', 'rowspan',
                                              'data-var', 'data-for', 'src', 'alt']},
                            protocols=['http', 'https', 'data'],
                            strip=False,
                            strip_comments=True,
                        )
                    except ImportError:
                        pass
                    return rendered_html

                if html_content and isinstance(html_content, str) and html_content.strip():
                    customer_template_rendered = _render_print_html(html_content)
                    logger.debug(f"Шаблон печати customer отрендерен для заявки #{order.id}, длина: {len(customer_template_rendered)} символов")

                if sales_html and isinstance(sales_html, str) and sales_html.strip():
                    sales_receipt_template_rendered = _render_print_html(sales_html)

                if work_html and isinstance(work_html, str) and work_html.strip():
                    work_act_template_rendered = _render_print_html(work_html)
            else:
                logger.debug(f"Шаблон печати пуст или отсутствует для заявки #{order.id}")
        except Exception as e:
            logger.error(f"Не удалось отрендерить шаблон печати клиента для заявки #{order.id}: {e}", exc_info=True)
        
        return render_template(
            'order_detail.html',
            order=order_data['order'],
            blocks_edit=blocks_edit,
            is_final=is_final,
            customer=order_data['customer'],
            device=order_data['device'],
            services=order_services,
            parts=order_parts,
            payments=order_data.get('payments', []),
            comments=order_data.get('comments', []),
            totals=totals,
            # Передаем переменные отдельно для обратной совместимости с шаблоном
            order_services=order_services,
            order_parts=order_parts,
            order_services_total=totals.get('services_total', 0),
            order_parts_total=totals.get('parts_total', 0),
            order_total=totals.get('total', 0),
            order_paid=totals.get('paid', 0),
            order_debt=totals.get('debt', 0),
            settings=settings,  # Настройки для печати
            salary_profit=salary_profit,
            salary_accruals=salary_accruals,
            salary_totals=salary_totals,
            # Преобразуем в кортежи для совместимости с шаблоном (как в add_order)
            device_types=[(dt['id'], dt['name']) for dt in refs.get('device_types', [])],
            device_brands=[(db['id'], db['name']) for db in refs.get('device_brands', [])],
            managers=[(m['id'], m['name']) for m in refs.get('managers', [])],
            masters=[(m['id'], m['name']) for m in refs.get('masters', [])],
            symptoms=[(s['id'], s['name'], s.get('sort_order', 0)) for s in refs.get('symptoms', [])],
            appearance_tags=[(at['id'], at['name'], at.get('sort_order', 0)) for at in refs.get('appearance_tags', [])],
            order_statuses=refs['order_statuses'],
            services_list=refs['services'],
            parts_list=refs.get('parts', []),
            all_services=refs['services'],  # Для модального окна добавления услуг
            order_models=refs.get('order_models', []),  # Модели устройств для поля "Модель"
            order_history=order_history,  # История взаимодействий с заявкой
            customer_template_rendered=customer_template_rendered,
            sales_receipt_template_rendered=sales_receipt_template_rendered,
            work_act_template_rendered=work_act_template_rendered,
        )
    except NotFoundError:
        flash('Заявка не найдена', 'error')
        return redirect(url_for('orders.all_orders')), 404
    except Exception as e:
        logger.exception("Ошибка при получении деталей заявки")
        flash('Произошла ошибка при загрузке заявки', 'error')
        return redirect(url_for('orders.all_orders')), 500

@bp.route('/device/<int:device_id>')
@login_required
def device_history(device_id):
    """История устройства."""
    device = DeviceService.get_device(device_id)
    if not device:
        return "Устройство не найдено", 404
    
    orders = DeviceService.get_device_orders(device_id)
    device_dict = device.to_dict()
    
    if device_dict.get('customer_phone'):
        device_dict['customer_phone_display'] = format_phone_display(device_dict['customer_phone'])
    
    for order in orders:
        if order.get('customer_phone'):
            order['customer_phone_display'] = format_phone_display(order['customer_phone'])
    
    return render_template('device_history.html',
        device=device_dict, orders=orders, orders_count=len(orders)
    )

# API endpoints для заявок
@bp.route('/api/orders/check_duplicate', methods=['POST'])
@login_required
def api_check_duplicate():
    """Проверка дубликатов."""
    try:
        from app.utils.validators import normalize_phone
        from app.database.connection import get_db_connection
        import sqlite3
        
        data = request.get_json(silent=True) or {}
        phone = data.get('phone', '')
        serial_number = data.get('serial_number')
        
        if not phone.strip():
            return jsonify({'success': False, 'error': 'phone_required'}), 400
        
        # Нормализуем телефон
        phone_normalized = normalize_phone(phone)
        
        if not phone_normalized or len(phone_normalized) != 11:
            return jsonify({'success': True, 'duplicates': False})
        
        # Проверяем наличие дубликатов
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Ищем клиента по телефону
            cursor.execute("SELECT id FROM customers WHERE phone = ?", (phone_normalized,))
            customer = cursor.fetchone()
            
            if not customer:
                return jsonify({'success': True, 'duplicates': False})
            
            customer_id = customer[0]
            
            # Проверяем наличие заявок за последние 30 дней
            not_deleted_clause = _orders_not_deleted_clause(cursor)
            if serial_number:
                cursor.execute('''
                    SELECT COUNT(*) FROM orders 
                    WHERE customer_id = ? 
                    AND device_id IN (SELECT id FROM devices WHERE serial_number = ?)
                    AND created_at > datetime('now', '-30 days')
                    AND (hidden = 0 OR hidden IS NULL)
                ''' + not_deleted_clause, (customer_id, serial_number))
            else:
                cursor.execute('''
                    SELECT COUNT(*) FROM orders 
                    WHERE customer_id = ? 
                    AND created_at > datetime('now', '-30 days')
                    AND (hidden = 0 OR hidden IS NULL)
                ''' + not_deleted_clause, (customer_id,))
            
            count = cursor.fetchone()[0]
            result = count > 0
            
        return jsonify({'success': True, 'duplicates': result})
    except Exception as e:
        logger.exception("Ошибка при проверке дубликатов")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@bp.route('/api/order/<order_id>/status', methods=['PUT'])
@login_required
def update_order_status_api(order_id):
    """API для обновления статуса заявки."""
    try:
        logger.info(f"Обновление статуса заявки {order_id}")
        logger.info(f"Request method: {request.method}")
        logger.info(f"Request content type: {request.content_type}")
        logger.info(f"Request data (decoded): {request.data.decode('utf-8') if request.data else 'None'}")
        logger.debug(f"Request headers: {dict(request.headers)}")
        logger.debug(f"Request data (raw): {request.data}")
        
        # Пробуем получить JSON данные
        try:
            data = request.get_json(silent=True)
            if data is None:
                # Если get_json вернул None, пробуем распарсить вручную
                if request.data:
                    import json
                    try:
                        data = json.loads(request.data.decode('utf-8'))
                        logger.debug(f"JSON parsed manually: {data}")
                    except json.JSONDecodeError as e:
                        logger.error(f"Ошибка парсинга JSON: {e}, data: {request.data}")
                        return jsonify({'success': False, 'error': f'Неверный формат JSON: {str(e)}'}), 400
                else:
                    data = {}
                    logger.warning("Request data is empty")
            logger.debug(f"Parsed JSON data: {data}")
        except Exception as e:
            logger.error(f"Ошибка при получении JSON данных: {e}")
            return jsonify({'success': False, 'error': f'Ошибка парсинга данных: {str(e)}'}), 400
        
        status_id = data.get('status_id')
        logger.debug(f"Extracted status_id: {status_id} (type: {type(status_id)})")
        
        # Обрабатываем случай, когда status_id может быть пустой строкой или None
        if status_id is None or status_id == '':
            # Разрешаем сброс статуса (установка в NULL)
            logger.debug("status_id is None or empty, setting to None")
            status_id = None
        else:
            try:
                status_id = int(status_id)
                if status_id <= 0:
                    logger.warning(f"Invalid status_id: {status_id} (must be > 0)")
                    return jsonify({'success': False, 'error': 'Неверный ID статуса'}), 400
                logger.debug(f"Parsed status_id to int: {status_id}")
            except (ValueError, TypeError) as e:
                logger.error(f"Error parsing status_id '{status_id}': {e}")
                return jsonify({'success': False, 'error': f'Неверный ID статуса: {status_id}'}), 400
        
        # Получаем заявку по UUID (order_id может быть как UUID, так и числовым ID)
        order = None
        try:
            # Пробуем сначала как UUID
            logger.debug(f"Попытка найти заявку по UUID: {order_id}")
            order = OrderService.get_order_by_uuid(order_id)
            if order:
                logger.debug(f"Заявка найдена по UUID: ID={order.id}, UUID={order.order_id}")
        except Exception as e:
            logger.debug(f"Ошибка при поиске по UUID: {e}")
            pass
        
        # Если не нашли по UUID, пробуем как числовой ID
        if not order:
            try:
                logger.debug(f"Попытка найти заявку по числовому ID: {order_id}")
                order_id_int = int(order_id)
                order = OrderService.get_order(order_id_int)
                if order:
                    logger.debug(f"Заявка найдена по числовому ID: ID={order.id}")
            except (ValueError, TypeError) as e:
                logger.error(f"Неверный формат ID заявки '{order_id}': {e}")
                return jsonify({'success': False, 'error': f'Неверный ID заявки: {order_id}'}), 400
        
        if not order:
            logger.warning(f"Заявка с ID/UUID '{order_id}' не найдена")
            return jsonify({'success': False, 'error': 'Заявка не найдена'}), 404
        
        # Обновляем статус используя числовой ID заявки
        user_id = current_user.id if current_user.is_authenticated else None
        
        if status_id is None:
            # Сброс статуса (установка в NULL)
            from app.database.connection import get_db_connection
            with get_db_connection() as conn:
                cursor = conn.cursor()
                # Получаем старый статус перед обновлением
                cursor.execute('SELECT status_id FROM orders WHERE id = ?', (order.id,))
                old_status_row = cursor.fetchone()
                old_status_id = old_status_row[0] if old_status_row else None
                
                updated_at_moscow = get_moscow_now_str()
                cursor.execute('''
                    UPDATE orders 
                    SET status_id = NULL, updated_at = ?
                    WHERE id = ?
                ''', (updated_at_moscow, order.id))
                
                # Логирование сброса статуса
                # ВАЖНО: Не логируем в order_status_history, так как new_status_id имеет ограничение NOT NULL
                # Вместо этого логируем только в action_logs для аудита
                try:
                    from app.services.action_log_service import ActionLogService
                    username = current_user.username if current_user.is_authenticated else None
                    
                    # Получаем название старого статуса для логирования
                    from app.services.reference_service import ReferenceService
                    statuses = ReferenceService.get_order_statuses()
                    old_status_name = 'Не указан'
                    if old_status_id:
                        old_status = next((s for s in statuses if s['id'] == old_status_id), None)
                        if old_status:
                            old_status_name = old_status.get('name', f'ID: {old_status_id}')
                    
                    ActionLogService.log_action(
                        user_id=user_id,
                        username=username,
                        action_type='update_order_status',
                        entity_type='order',
                        entity_id=order.id,
                        details={
                            'old_status_id': old_status_id,
                            'old_status_name': old_status_name,
                            'new_status_id': None,
                            'new_status_name': 'Сброшен',
                            'action': 'Сброс статуса'
                        }
                    )
                    logger.info(f"Сброс статуса заявки #{order.id} залогирован в action_logs (старый статус: {old_status_name})")
                except Exception as e:
                    logger.warning(f"Не удалось залогировать сброс статуса в action_logs: {e}")
                
                conn.commit()
            
            status_info = {'id': None, 'name': 'Не указан', 'color': '#6c757d'}
            return jsonify({
                'success': True,
                'status_id': None,
                'status_name': 'Не указан',
                'status_color': '#6c757d',
                'triggers_payment_modal': False,
                'accrues_salary': False
            })
        else:
            # Обновляем через сервис (теперь возвращает словарь с триггерами)
            result = OrderService.update_order_status(order.id, status_id, user_id, comment=data.get('comment'))
            
            # Отправляем уведомления о смене статуса в фоновом потоке,
            # чтобы не блокировать ответ API (SMTP-таймаут может занимать секунды).
            if result and status_id:
                try:
                    from app.services.reference_service import ReferenceService
                    refs = ReferenceService.get_all_references()
                    new_status = next((s for s in refs.get('order_statuses', []) if s['id'] == status_id), None)
                    new_status_name = new_status.get('name', 'Неизвестный статус') if new_status else 'Неизвестный статус'

                    import threading
                    from flask import current_app
                    app = current_app._get_current_object()
                    _order_id = order.id
                    _customer_id = order.customer_id
                    _user_id = user_id

                    def _send_notification():
                        try:
                            with app.app_context():
                                from app.services.notification_service import NotificationService
                                NotificationService.notify_order_status_change(
                                    order_id=_order_id,
                                    new_status=new_status_name,
                                    customer_id=_customer_id,
                                    changed_by_user_id=_user_id
                                )
                        except Exception as ex:
                            logger.warning(f"Не удалось отправить уведомления о смене статуса (фон): {ex}")
                    threading.Thread(target=_send_notification, daemon=True).start()
                except Exception as e:
                    logger.warning(f"Не удалось запустить фоновую отправку уведомлений: {e}")
            
            # Получаем информацию о новом статусе для ответа
            from app.services.reference_service import ReferenceService
            statuses = ReferenceService.get_order_statuses()
            status_info = next((s for s in statuses if s['id'] == status_id), None)
            if not status_info:
                status_info = {'id': status_id, 'name': 'Не указан', 'color': '#6c757d'}
            
            # Возвращаем результат с триггерами
            return jsonify({
                'success': result.get('success', True),
                'status_id': status_info['id'],
                'status_name': status_info['name'],
                'status_color': status_info['color'],
                'triggers_payment_modal': result.get('triggers_payment_modal', False),
                'accrues_salary': result.get('accrues_salary', False),
                'blocks_edit': result.get('blocks_edit', False),
                'is_final': result.get('is_final', False),
                'requires_comment': result.get('requires_comment', False)
            })
    except (ValidationError, NotFoundError) as e:
        logger.error(f"Validation/NotFound error при обновлении статуса {order_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 400
    except DatabaseError as e:
        logger.error(f"Database error при обновлении статуса {order_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    except Exception as e:
        logger.exception(f"Неожиданная ошибка при обновлении статуса заявки {order_id}: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'success': False, 'error': f'Internal server error: {str(e)}'}), 500

@bp.route('/api/order/<int:order_id>/comment', methods=['POST'])
@login_required
def add_comment(order_id):
    """API для добавления комментария."""
    try:
        data = request.get_json(silent=True) or {}
        author_name = data.get('author_name', '')
        comment_text = data.get('comment_text', '')
        is_internal = data.get('is_internal', False)
        attachment_ids = data.get('attachment_ids', [])
        
        if not author_name or not comment_text:
            return jsonify({'success': False, 'error': 'author_name and comment_text required'}), 400
        
        user_id = current_user.id if current_user.is_authenticated else None
        if not author_name and user_id:
            # Используем display_name пользователя, если доступен
            from app.services.user_service import UserService
            user = UserService.get_user_by_id(user_id)
            if user and user.get('display_name'):
                author_name = user['display_name']
            elif user:
                author_name = user.get('username', 'Неизвестный пользователь')
        
        comment_id = CommentService.add_comment(
            order_id=order_id,
            author_name=author_name,
            comment_text=comment_text,
            user_id=user_id,
            is_internal=is_internal,
            attachment_ids=attachment_ids
        )
        comments = CommentService.get_order_comments(order_id)
        
        # Логируем добавление комментария
        try:
            from app.services.action_log_service import ActionLogService
            user_id = current_user.id if current_user.is_authenticated else None
            username = current_user.username if current_user.is_authenticated else author_name
            
            ActionLogService.log_action(
                user_id=user_id,
                username=username,
                action_type='add_comment',
                entity_type='order',
                entity_id=order_id,
                details={'ID комментария': comment_id, 'Текст': comment_text[:100]}
            )
        except Exception as e:
            logger.warning(f"Не удалось залогировать добавление комментария: {e}")
        
        # Возвращаем новый комментарий для отображения в интерфейсе
        new_comment = None
        for c in comments:
            if c.get('id') == comment_id:
                new_comment = c
                break
        
        if not new_comment:
            # Если не нашли в списке, создаём объект вручную
            from app.utils.datetime_utils import get_moscow_now_str
            new_comment = {
                'id': comment_id,
                'author_name': author_name,
                'comment_text': comment_text,
                'created_at': get_moscow_now_str()
            }
        
        return jsonify({
            'success': True, 
            'comment_id': comment_id, 
            'comment': new_comment,
            'comments': comments
        }), 201
    except (ValidationError, NotFoundError) as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except DatabaseError as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/order/comment/<int:comment_id>', methods=['DELETE'])
@login_required
def delete_comment(comment_id):
    """API для удаления комментария."""
    try:
        # Получаем информацию о комментарии перед удалением
        from app.database.connection import get_db_connection
        import sqlite3
        order_id = None
        with get_db_connection(row_factory=sqlite3.Row) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT order_id FROM order_comments WHERE id = ?', (comment_id,))
            row = cursor.fetchone()
            if row:
                order_id = row['order_id']
        
        CommentService.delete_comment(comment_id)
        
        # Логируем удаление комментария
        if order_id:
            try:
                from app.services.action_log_service import ActionLogService
                user_id = current_user.id if current_user.is_authenticated else None
                username = current_user.username if current_user.is_authenticated else None
                
                ActionLogService.log_action(
                    user_id=user_id,
                    username=username,
                    action_type='delete_comment',
                    entity_type='order',
                    entity_id=order_id,
                    details={'ID комментария': comment_id}
                )
            except Exception as e:
                logger.warning(f"Не удалось залогировать удаление комментария: {e}")
        
        return jsonify({'success': True})
    except (ValidationError, NotFoundError) as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except DatabaseError as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/order/<int:order_id>/toggle-visibility', methods=['POST'])
@login_required
def toggle_order_visibility_api(order_id):
    """API для скрытия/показа заявки."""
    try:
        data = request.get_json(silent=True) or {}
        hidden = data.get('hidden', False)
        reason = data.get('reason')
        
        user_id = current_user.id
        OrderService.toggle_visibility(order_id, hidden, user_id, reason)
        
        return jsonify({'success': True, 'hidden': hidden})
    except (ValidationError, NotFoundError) as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except DatabaseError as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/order/<int:order_id>/delete', methods=['POST'])
@login_required
@permission_required('delete_orders')
def soft_delete_order_api(order_id):
    """Мягкое удаление заявки (soft-delete)."""
    try:
        data = request.get_json(silent=True) or {}
        reason = (data.get('reason') or '').strip()
        if not reason:
            return jsonify({'success': False, 'error': 'Укажите причину удаления'}), 400

        OrderService.soft_delete_order(
            order_id=order_id,
            reason=reason,
            user_id=current_user.id
        )
        return jsonify({'success': True})
    except (ValidationError, NotFoundError) as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except DatabaseError as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/orders/<int:order_id>/services', methods=['GET', 'POST'])
@login_required
def api_order_services(order_id):
    """API для услуг заявки."""
    if request.method == 'GET':
        services = OrderService.get_order_services(order_id)
        return jsonify(services)
    
    if request.method == 'POST':
        try:
            # Проверяем, разрешено ли редактирование заявки
            if not OrderService.check_order_edit_allowed(order_id):
                return jsonify({
                    'success': False, 
                    'error': 'Редактирование заявки заблокировано для текущего статуса. Разрешено только добавление комментариев.'
                }), 403
            
            data = request.get_json(silent=True) or {}
            service_id = data.get('service_id')
            name = data.get('name')
            quantity = int(data.get('quantity', 1))
            price = data.get('price')
            base_price = data.get('base_price')
            cost_price = data.get('cost_price')
            discount_type = data.get('discount_type')
            discount_value = data.get('discount_value')
            warranty_days = data.get('warranty_days')
            executor_id = data.get('executor_id')
            
            # Преобразуем service_id в int, если указан
            if service_id is not None:
                try:
                    service_id = int(service_id)
                except (ValueError, TypeError):
                    service_id = None
            
            # Преобразуем price в float, если указан
            price_float = float(price) if price is not None else None
            base_price_float = float(base_price) if base_price is not None and base_price != '' else None
            cost_price_float = float(cost_price) if cost_price is not None and cost_price != '' else None
            discount_value_float = float(discount_value) if discount_value is not None and discount_value != '' else None
            warranty_days_int = int(warranty_days) if warranty_days is not None and warranty_days != '' else None
            executor_id_int = int(executor_id) if executor_id is not None and executor_id != '' else None
            
            order_service_id = OrderService.add_order_service(
                order_id=order_id,
                service_id=service_id,
                quantity=quantity,
                price=price_float,
                name=name,
                base_price=base_price_float,
                cost_price=cost_price_float,
                discount_type=discount_type,
                discount_value=discount_value_float,
                warranty_days=warranty_days_int,
                executor_id=executor_id_int
            )
            services = OrderService.get_order_services(order_id)
            
            # Получаем обновленные totals для ответа
            totals = OrderService.get_order_totals(order_id)
            order_total = float(totals.get('total', 0) or 0)
            order_paid = float(totals.get('paid', 0) or 0)
            order_debt = float(totals.get('debt', 0) or 0)
            
            # Логируем добавление услуги
            try:
                from app.services.action_log_service import ActionLogService
                from app.database.queries.reference_queries import ReferenceQueries
                user_id = current_user.id if current_user.is_authenticated else None
                username = current_user.username if current_user.is_authenticated else None
                
                # Получаем название услуги
                service_name = name
                if service_id and not service_name:
                    services = ReferenceQueries.get_services()
                    service = next((s for s in services if s.get('id') == service_id), None)
                    if service:
                        service_name = service.get('name', 'Услуга')
                if not service_name:
                    service_name = 'Услуга'
                
                ActionLogService.log_action(
                    user_id=user_id,
                    username=username,
                    action_type='add_service',
                    entity_type='order',
                    entity_id=order_id,
                    details={
                        'Услуга': service_name,
                        'name': service_name,
                        'Количество': quantity,
                        'quantity': quantity,
                        'Цена': price_float if price_float else 0,
                        'price': price_float if price_float else 0
                    }
                )
            except Exception as e:
                logger.warning(f"Не удалось залогировать добавление услуги: {e}")
            
            return jsonify({
                'success': True, 
                'services': services,
                'order_total': order_total,
                'order_paid': order_paid,
                'order_debt': order_debt,
                'prepayment': totals.get('prepayment', 0),
                'overpayment': totals.get('overpayment', 0)
            }), 201
        except (ValidationError, NotFoundError) as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        except DatabaseError as e:
            return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/orders/items/price-history', methods=['GET'])
@login_required
def api_price_history():
    """История цен для услуги/товара за последние N дней (по умолчанию 30)."""
    try:
        item_type = (request.args.get('type') or '').strip().lower()
        item_id = request.args.get('id', type=int)
        days = request.args.get('days', default=30, type=int) or 30
        if item_type not in ('service', 'part'):
            return jsonify({'success': False, 'error': 'type must be service|part'}), 400
        if not item_id:
            return jsonify({'success': False, 'error': 'id required'}), 400
        if days < 1:
            days = 30

        import sqlite3
        from app.database.connection import get_db_connection

        table = 'order_services' if item_type == 'service' else 'order_parts'
        col = 'service_id' if item_type == 'service' else 'part_id'

        with get_db_connection(row_factory=sqlite3.Row) as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"""
                SELECT price, created_at
                FROM {table}
                WHERE {col} = ?
                  AND created_at >= datetime('now', ?)
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (item_id, f'-{days} days')
            )
            last_row = cursor.fetchone()

            cursor.execute(
                f"""
                SELECT AVG(price) AS avg_price, COUNT(*) AS cnt
                FROM {table}
                WHERE {col} = ?
                  AND created_at >= datetime('now', ?)
                """,
                (item_id, f'-{days} days')
            )
            agg = cursor.fetchone()

        return jsonify({
            'success': True,
            'days': days,
            'last_price': float(last_row['price']) if last_row and last_row['price'] is not None else None,
            'avg_price': float(agg['avg_price']) if agg and agg['avg_price'] is not None else None,
            'count': int(agg['cnt']) if agg and agg['cnt'] is not None else 0
        })
    except Exception as e:
        logger.error(f"Ошибка price-history: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@bp.route('/api/order-services/<int:order_service_id>', methods=['DELETE'])
@login_required
def api_delete_order_service(order_service_id):
    """API для удаления услуги."""
    try:
        # Получаем информацию об услуге перед удалением
        from app.database.connection import get_db_connection
        import sqlite3
        order_id = None
        with get_db_connection(row_factory=sqlite3.Row) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT order_id FROM order_services WHERE id = ?', (order_service_id,))
            row = cursor.fetchone()
            if row:
                order_id = row['order_id']
        
        # Проверяем, разрешено ли редактирование заявки
        if order_id and not OrderService.check_order_edit_allowed(order_id):
            return jsonify({
                'success': False, 
                'error': 'Редактирование заявки заблокировано для текущего статуса. Разрешено только добавление комментариев.'
            }), 403
        
        OrderService.delete_order_service(order_service_id)
        
        # Логируем удаление услуги
        if order_id:
            try:
                from app.services.action_log_service import ActionLogService
                from app.database.connection import get_db_connection
                import sqlite3
                user_id = current_user.id if current_user.is_authenticated else None
                username = current_user.username if current_user.is_authenticated else None
                
                # Получаем название услуги перед удалением
                service_name = 'Услуга'
                quantity = 1
                price = 0
                try:
                    with get_db_connection(row_factory=sqlite3.Row) as conn:
                        cursor = conn.cursor()
                        cursor.execute('''
                            SELECT s.name, os.quantity, os.price
                            FROM order_services os
                            LEFT JOIN services s ON s.id = os.service_id
                            WHERE os.id = ?
                        ''', (order_service_id,))
                        row = cursor.fetchone()
                        if row:
                            service_name = row['name'] or 'Услуга'
                            quantity = row['quantity'] or 1
                            price = float(row['price'] or 0)
                except Exception as e:
                    logger.warning(f"Не удалось получить данные услуги для лога: {e}")
                
                ActionLogService.log_action(
                    user_id=user_id,
                    username=username,
                    action_type='remove_service',
                    entity_type='order',
                    entity_id=order_id,
                    details={
                        'ID позиции услуги': order_service_id,
                        'Услуга': service_name,
                        'name': service_name,
                        'Количество': quantity,
                        'quantity': quantity,
                        'Цена': price,
                        'price': price
                    }
                )
            except Exception as e:
                logger.warning(f"Не удалось залогировать удаление услуги: {e}")
        
        return jsonify({'success': True})
    except (ValidationError, NotFoundError) as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except DatabaseError as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/order-services/<int:order_service_id>', methods=['PATCH'])
@login_required
def api_update_order_service(order_service_id):
    """API для обновления позиции услуги в заявке."""
    try:
        # Получаем order_id для проверки блокировки
        from app.database.connection import get_db_connection
        import sqlite3
        order_id = None
        with get_db_connection(row_factory=sqlite3.Row) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT order_id FROM order_services WHERE id = ?', (order_service_id,))
            row = cursor.fetchone()
            if row:
                order_id = row['order_id']
        
        # Проверяем, разрешено ли редактирование заявки
        if order_id and not OrderService.check_order_edit_allowed(order_id):
            return jsonify({
                'success': False, 
                'error': 'Редактирование заявки заблокировано для текущего статуса. Разрешено только добавление комментариев.'
            }), 403
        
        data = request.get_json(silent=True) or {}
        updates = {}

        if 'quantity' in data:
            updates['quantity'] = int(data.get('quantity') or 0)
        if 'price' in data:
            v = data.get('price')
            updates['price'] = float(v) if v is not None and v != '' else None
        if 'cost_price' in data:
            v = data.get('cost_price')
            updates['cost_price'] = float(v) if v is not None and v != '' else None
        if 'discount_type' in data:
            updates['discount_type'] = data.get('discount_type')
        if 'discount_value' in data:
            v = data.get('discount_value')
            updates['discount_value'] = float(v) if v is not None and v != '' else None
        if 'warranty_days' in data:
            v = data.get('warranty_days')
            updates['warranty_days'] = int(v) if v is not None and v != '' else None
        if 'executor_id' in data:
            v = data.get('executor_id')
            updates['executor_id'] = int(v) if v is not None and v != '' else None

        if 'discount_value' in updates and updates.get('discount_value') is None:
            updates['discount_type'] = None

        user_id = current_user.id if current_user.is_authenticated else None
        order_id = OrderService.update_order_service_item(order_service_id, updates, user_id=user_id)
        totals = OrderService.get_order_totals(order_id)

        return jsonify({
            'success': True,
            'order_total': float(totals.get('total', 0) or 0),
            'order_paid': float(totals.get('paid', 0) or 0),
            'order_debt': float(totals.get('debt', 0) or 0),
            'prepayment': totals.get('prepayment', 0),
            'overpayment': totals.get('overpayment', 0)
        })
    except (ValidationError, NotFoundError) as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except DatabaseError as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    except Exception as e:
        logger.error(f"Ошибка при обновлении услуги {order_service_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@bp.route('/api/orders/<int:order_id>/payments', methods=['GET', 'POST'])
@login_required
def api_order_payments(order_id):
    """API для оплат заявки."""
    if request.method == 'GET':
        payments = PaymentService.get_order_payments(order_id)
        return jsonify(payments)
    
    if request.method == 'POST':
        try:
            # Разрешаем добавление платежей даже для закрытых заявок
            # Это нужно для случая, когда при закрытии заявки нужно добавить платеж
            # Проверяем только существование заявки
            order = OrderService.get_order(order_id)
            if not order:
                return jsonify({
                    'success': False, 
                    'error': 'Заявка не найдена'
                }), 404
            
            data = request.get_json(silent=True) or {}
            amount = float(data.get('amount', 0))
            payment_type = data.get('payment_type', 'cash')
            comment = data.get('comment')
            kind = data.get('kind', 'payment')  # payment|deposit
            idempotency_key = data.get('idempotency_key')
            
            user_id = current_user.id if current_user.is_authenticated else None
            username = current_user.username if current_user.is_authenticated else None
            
            payment_id = PaymentService.add_payment(
                order_id, amount, payment_type, user_id, username, comment,
                kind=kind,
                status='captured',
                idempotency_key=idempotency_key
            )
            payments = PaymentService.get_order_payments(order_id)
            
            # Пересчёт зарплаты при добавлении оплаты (если статус «начисляет зарплату»)
            try:
                with get_db_connection() as conn:
                    cur = conn.cursor()
                    cur.execute(
                        'SELECT accrues_salary FROM order_statuses WHERE id = (SELECT status_id FROM orders WHERE id = ?)',
                        (order_id,)
                    )
                    row = cur.fetchone()
                    if row and row[0]:
                        SalaryService.accrue_salary_for_order(order_id, force_recalculate=True)
                        logger.info(f"Зарплата по заявке {order_id} пересчитана после добавления оплаты")
            except Exception as salary_err:
                logger.warning(f"Не удалось пересчитать зарплату после оплаты (заявка {order_id}): {salary_err}")
            
            # Пересчитываем суммы по заявке для обновления блока "Оплаты"
            # OrderService уже импортирован в начале файла, не нужно импортировать снова
            totals = OrderService.get_order_totals(order_id)
            order_total = float(totals.get('total', 0) or 0)
            order_paid = float(totals.get('paid', 0) or 0)
            order_debt = float(totals.get('debt', 0) or 0)
            
            # Логирование выполняется в PaymentService.add_payment
            return jsonify({
                'success': True,
                'payments': payments,
                'order_total': order_total,
                'order_paid': order_paid,
                'order_debt': order_debt,
                'prepayment': totals.get('prepayment', 0),
                'overpayment': totals.get('overpayment', 0)
            }), 201
        except (ValidationError, NotFoundError) as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        except DatabaseError as e:
            return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/orders/<int:order_id>/parts', methods=['GET', 'POST'])
@login_required
def api_order_parts(order_id):
    """API для запчастей/товаров в заявке (продажа со склада)."""
    if request.method == 'GET':
        parts = OrderService.get_order_parts(order_id)
        return jsonify(parts)

    if request.method == 'POST':
        try:
            # Проверяем, разрешено ли редактирование заявки
            if not OrderService.check_order_edit_allowed(order_id):
                return jsonify({
                    'success': False, 
                    'error': 'Редактирование заявки заблокировано для текущего статуса. Разрешено только добавление комментариев.'
                }), 403
            
            data = request.get_json(silent=True) or {}
            part_id = data.get('part_id')
            name = data.get('name')
            quantity = int(data.get('quantity', 1))
            price = data.get('price')
            base_price = data.get('base_price')
            purchase_price = data.get('purchase_price')  # себестоимость для позиции заявки
            discount_type = data.get('discount_type')
            discount_value = data.get('discount_value')
            warranty_days = data.get('warranty_days')
            executor_id = data.get('executor_id')

            # Преобразуем part_id в int, если указан
            if part_id is not None:
                try:
                    part_id = int(part_id)
                except (ValueError, TypeError):
                    part_id = None
            
            # Преобразуем price в float, если указан (с обработкой ошибок)
            try:
                price_float = float(price) if price is not None and price != '' else None
            except (ValueError, TypeError):
                price_float = None
                
            try:
                base_price_float = float(base_price) if base_price is not None and base_price != '' else None
            except (ValueError, TypeError):
                base_price_float = None
                
            try:
                purchase_price_float = float(purchase_price) if purchase_price is not None and purchase_price != '' else None
            except (ValueError, TypeError):
                purchase_price_float = None
                
            try:
                discount_value_float = float(discount_value) if discount_value is not None and discount_value != '' else None
            except (ValueError, TypeError):
                discount_value_float = None
                
            try:
                warranty_days_int = int(warranty_days) if warranty_days is not None and warranty_days != '' else None
            except (ValueError, TypeError):
                warranty_days_int = None
                
            try:
                executor_id_int = int(executor_id) if executor_id is not None and executor_id != '' else None
            except (ValueError, TypeError):
                executor_id_int = None

            order_part_id = OrderService.add_order_part(
                order_id=order_id,
                part_id=part_id,
                quantity=quantity,
                price=price_float,
                name=name,
                base_price=base_price_float,
                purchase_price=purchase_price_float,
                discount_type=discount_type,
                discount_value=discount_value_float,
                warranty_days=warranty_days_int,
                executor_id=executor_id_int
            )
            
            # Получаем обновленные totals для ответа
            totals = OrderService.get_order_totals(order_id)
            order_total = float(totals.get('total', 0) or 0)
            order_paid = float(totals.get('paid', 0) or 0)
            order_debt = float(totals.get('debt', 0) or 0)

            # Логируем добавление запчасти
            try:
                from app.services.action_log_service import ActionLogService
                from app.database.queries.warehouse_queries import WarehouseQueries
                user_id = current_user.id if current_user.is_authenticated else None
                username = current_user.username if current_user.is_authenticated else None

                # Получаем название товара
                part_name = name
                if part_id and not part_name:
                    part = WarehouseQueries.get_part_by_id(part_id)
                    if part:
                        part_name = part.get('name', 'Товар')
                if not part_name:
                    part_name = 'Товар'

                ActionLogService.log_action(
                    user_id=user_id,
                    username=username,
                    action_type='add_part',
                    entity_type='order',
                    entity_id=order_id,
                    details={
                        'ID позиции': order_part_id,
                        'Товар': part_name,
                        'name': part_name,
                        'Количество': quantity,
                        'quantity': quantity,
                        'Цена': price_float if price_float else 0,
                        'price': price_float if price_float else 0
                    }
                )
            except Exception as e:
                logger.warning(f"Не удалось залогировать добавление запчасти: {e}")

            return jsonify({
                'success': True, 
                'order_part_id': order_part_id,
                'order_total': order_total,
                'order_paid': order_paid,
                'order_debt': order_debt,
                'prepayment': totals.get('prepayment', 0),
                'overpayment': totals.get('overpayment', 0)
            }), 201
        except (ValidationError, NotFoundError) as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        except DatabaseError as e:
            return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/order-parts/<int:order_part_id>', methods=['DELETE'])
@login_required
def api_delete_order_part(order_part_id):
    """API для удаления запчасти/товара из заявки (возврат на склад)."""
    try:
        # Получаем order_id перед удалением для логов
        from app.database.connection import get_db_connection
        import sqlite3
        order_id = None
        with get_db_connection(row_factory=sqlite3.Row) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT order_id, part_id, quantity FROM order_parts WHERE id = ?', (order_part_id,))
            row = cursor.fetchone()
            if row:
                order_id = row['order_id']
                part_id = row['part_id']
                quantity = row['quantity']
            else:
                return jsonify({'success': False, 'error': 'Запчасть не найдена'}), 404

        # Проверяем, разрешено ли редактирование заявки
        if order_id and not OrderService.check_order_edit_allowed(order_id):
            return jsonify({
                'success': False, 
                'error': 'Редактирование заявки заблокировано для текущего статуса. Разрешено только добавление комментариев.'
            }), 403

        OrderService.delete_order_part(order_part_id)

        # Логируем удаление запчасти
        if order_id:
            try:
                from app.services.action_log_service import ActionLogService
                from app.database.connection import get_db_connection
                import sqlite3
                user_id = current_user.id if current_user.is_authenticated else None
                username = current_user.username if current_user.is_authenticated else None
                
                # Получаем название товара перед удалением
                part_name = 'Товар'
                price = 0
                try:
                    with get_db_connection(row_factory=sqlite3.Row) as conn:
                        cursor = conn.cursor()
                        cursor.execute('''
                            SELECT op.name, op.quantity, op.price, p.name AS part_name
                            FROM order_parts op
                            LEFT JOIN parts p ON p.id = op.part_id
                            WHERE op.id = ?
                        ''', (order_part_id,))
                        row = cursor.fetchone()
                        if row:
                            part_name = row['name'] or row['part_name'] or 'Товар'
                            quantity = row['quantity'] or 1
                            price = float(row['price'] or 0)
                except Exception as e:
                    logger.warning(f"Не удалось получить данные товара для лога: {e}")
                
                ActionLogService.log_action(
                    user_id=user_id,
                    username=username,
                    action_type='remove_part',
                    entity_type='order',
                    entity_id=order_id,
                    details={
                        'ID позиции товара': order_part_id,
                        'ID товара': part_id,
                        'Товар': part_name,
                        'name': part_name,
                        'Количество': quantity,
                        'quantity': quantity,
                        'Цена': price,
                        'price': price
                    }
                )
            except Exception as e:
                logger.warning(f"Не удалось залогировать удаление запчасти: {e}")

        return jsonify({'success': True})
    except (ValidationError, NotFoundError) as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except DatabaseError as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/order-parts/<int:order_part_id>', methods=['PATCH'])
@login_required
def api_update_order_part(order_part_id):
    """API для обновления позиции товара в заявке."""
    try:
        # Получаем order_id для проверки блокировки
        from app.database.connection import get_db_connection
        import sqlite3
        order_id = None
        with get_db_connection(row_factory=sqlite3.Row) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT order_id FROM order_parts WHERE id = ?', (order_part_id,))
            row = cursor.fetchone()
            if row:
                order_id = row['order_id']
        
        # Проверяем, разрешено ли редактирование заявки
        if order_id and not OrderService.check_order_edit_allowed(order_id):
            return jsonify({
                'success': False, 
                'error': 'Редактирование заявки заблокировано для текущего статуса. Разрешено только добавление комментариев.'
            }), 403
        
        data = request.get_json(silent=True) or {}
        updates = {}

        if 'quantity' in data:
            updates['quantity'] = int(data.get('quantity') or 0)
        if 'price' in data:
            v = data.get('price')
            updates['price'] = float(v) if v is not None and v != '' else None
        if 'purchase_price' in data:
            v = data.get('purchase_price')
            updates['purchase_price'] = float(v) if v is not None and v != '' else None
        if 'discount_type' in data:
            updates['discount_type'] = data.get('discount_type')
        if 'discount_value' in data:
            v = data.get('discount_value')
            updates['discount_value'] = float(v) if v is not None and v != '' else None
        if 'warranty_days' in data:
            v = data.get('warranty_days')
            updates['warranty_days'] = int(v) if v is not None and v != '' else None
        if 'executor_id' in data:
            v = data.get('executor_id')
            updates['executor_id'] = int(v) if v is not None and v != '' else None

        if 'discount_value' in updates and updates.get('discount_value') is None:
            updates['discount_type'] = None

        user_id = current_user.id if current_user.is_authenticated else None
        order_id = OrderService.update_order_part_item(order_part_id, updates, user_id=user_id)
        totals = OrderService.get_order_totals(order_id)

        return jsonify({
            'success': True,
            'order_total': float(totals.get('total', 0) or 0),
            'order_paid': float(totals.get('paid', 0) or 0),
            'order_debt': float(totals.get('debt', 0) or 0),
            'prepayment': totals.get('prepayment', 0),
            'overpayment': totals.get('overpayment', 0)
        })
    except (ValidationError, NotFoundError) as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except DatabaseError as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    except Exception as e:
        logger.error(f"Ошибка при обновлении товара {order_part_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@bp.route('/api/payments/<int:payment_id>', methods=['DELETE'])
@login_required
def api_delete_payment(payment_id):
    """API для удаления оплаты - ЗАПРЕЩЕНО. Используйте возврат (refund) вместо удаления."""
    # Глобальный запрет на удаление платежей - используйте только возврат
    return jsonify({
        'success': False, 
        'error': 'Удаление платежей запрещено. Используйте функцию возврата (refund) для корректного оформления возврата средств.'
    }), 403


@bp.route('/api/payments/<int:payment_id>/receipts', methods=['GET', 'POST'])
@login_required
def api_payment_receipts(payment_id: int):
    """API для чеков по оплате (пока manual)."""
    try:
        # Роль: чеки создаёт manager/admin (обычно кассир/менеджер)
        from app.services.user_service import UserService
        user_role = getattr(current_user, 'role', 'viewer')
        if request.method == 'POST' and not UserService.check_role_permission(user_role, 'manager'):
            return jsonify({'success': False, 'error': 'Недостаточно прав для создания чека'}), 403

        if request.method == 'GET':
            receipts = ReceiptService.get_payment_receipts(payment_id)
            return jsonify({'success': True, 'receipts': receipts})

        data = request.get_json(silent=True) or {}
        receipt_type = (data.get('receipt_type') or 'sell').strip()
        receipt_id = ReceiptService.create_manual_receipt(
            payment_id=payment_id,
            receipt_type=receipt_type,
            created_by_id=current_user.id,
            created_by_username=current_user.username,
        )
        receipts = ReceiptService.get_payment_receipts(payment_id)
        return jsonify({'success': True, 'receipt_id': receipt_id, 'receipts': receipts}), 201
    except (ValidationError, NotFoundError) as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except DatabaseError as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/payments/<int:payment_id>/refund', methods=['POST'])
@login_required
def api_refund_payment(payment_id: int):
    """API для возврата по оплате."""
    try:
        from app.services.user_service import UserService
        user_role = getattr(current_user, 'role', 'viewer')
        if not UserService.check_role_permission(user_role, 'manager'):
            return jsonify({'success': False, 'error': 'Недостаточно прав для возврата'}), 403

        data = request.get_json(silent=True) or {}
        amount = float(data.get('amount', 0) or 0)
        reason = (data.get('reason') or '').strip()
        create_receipt = bool(data.get('create_receipt', True))

        refund_payment_id = PaymentService.refund_payment(
            original_payment_id=payment_id,
            amount=amount,
            reason=reason,
            user_id=current_user.id,
            username=current_user.username,
            create_cash_transaction=True,
        )

        receipt_id = None
        if create_receipt:
            receipt_id = ReceiptService.create_manual_receipt(
                payment_id=refund_payment_id,
                receipt_type='refund',
                created_by_id=current_user.id,
                created_by_username=current_user.username,
            )

        # Возвращаем обновлённые оплаты и totals (для UI)
        # payment_id -> исходная оплата, достаём order_id
        from app.database.connection import get_db_connection
        import sqlite3
        order_id = None
        with get_db_connection(row_factory=sqlite3.Row) as conn:
            cur = conn.cursor()
            cur.execute("SELECT order_id FROM payments WHERE id = ?", (payment_id,))
            row = cur.fetchone()
            if row:
                order_id = int(row["order_id"])

        payments = PaymentService.get_order_payments(order_id) if order_id else []
        # OrderService уже импортирован в начале файла
        totals = OrderService.get_order_totals(order_id) if order_id else {}

        return jsonify({
            'success': True,
            'refund_payment_id': refund_payment_id,
            'receipt_id': receipt_id,
            'payments': payments,
            'order_total': float(totals.get('total', 0) or 0),
            'order_paid': float(totals.get('paid', 0) or 0),
            'order_debt': float(totals.get('debt', 0) or 0),
            'prepayment': totals.get('prepayment', 0),
            'overpayment': totals.get('overpayment', 0),
        }), 201
    except (ValidationError, NotFoundError) as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except DatabaseError as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/orders/<int:order_id>/wallet', methods=['GET', 'POST'])
@login_required
def api_order_wallet(order_id: int):
    return jsonify({
        "success": False,
        "error": "Функционал депозита в заявках отключен"
    }), 410


@bp.route('/api/payments/<int:payment_id>/refund_to_wallet', methods=['POST'])
@login_required
def api_refund_to_wallet(payment_id: int):
    return jsonify({
        "success": False,
        "error": "Функционал депозита в заявках отключен"
    }), 410


@bp.route('/api/orders/<int:order_id>/overpayment_to_wallet', methods=['POST'])
@login_required
def api_overpayment_to_wallet(order_id: int):
    return jsonify({
        "success": False,
        "error": "Функционал депозита в заявках отключен"
    }), 410


@bp.route('/receipts/<int:receipt_id>/print', methods=['GET'])
@login_required
def print_receipt(receipt_id: int):
    """Печать (HTML) чека по оплате."""
    receipt = ReceiptService.get_receipt(receipt_id)

    # Получаем оплату + базовую информацию о заявке
    from app.database.connection import get_db_connection
    import sqlite3
    with get_db_connection(row_factory=sqlite3.Row) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT p.*, o.order_id AS order_number, o.id AS order_db_id,
                   c.name AS customer_name, c.phone AS customer_phone
            FROM payment_receipts pr
            JOIN payments p ON p.id = pr.payment_id
            LEFT JOIN orders o ON o.id = p.order_id
            LEFT JOIN customers c ON c.id = o.customer_id
            WHERE pr.id = ?
            """,
            (receipt_id,),
        )
        row = cur.fetchone()
        payment = dict(row) if row else {}

    # Позиции заявки (для печати "товарного/работ")
    # OrderService уже импортирован в начале файла
    order_services = []
    order_parts = []
    if payment.get("order_id"):
        try:
            order_services = OrderService.get_order_services(int(payment["order_id"]))
        except Exception:
            order_services = []
        try:
            order_parts = OrderService.get_order_parts(int(payment["order_id"]))
        except Exception:
            order_parts = []

    return render_template(
        "finance/payment_receipt_print.html",
        receipt=receipt,
        payment=payment,
        order_services=order_services,
        order_parts=order_parts,
    )

@bp.route('/api/orders/<int:order_id>/sell', methods=['POST'])
@login_required
def api_sell_items(order_id):
    """API для объединенной продажи услуг и товаров."""
    try:
        data = request.get_json(silent=True) or {}
        services = data.get('services', [])
        parts = data.get('parts', [])
        payment = data.get('payment')
        
        if not services and not parts:
            return jsonify({'success': False, 'error': 'Должна быть хотя бы одна услуга или запчасть'}), 400
        
        user_id = current_user.id if current_user.is_authenticated else None
        
        result = OrderService.sell_items(
            order_id=order_id,
            services=services,
            parts=parts,
            payment=payment,
            user_id=user_id
        )
        
        # Логируем продажу
        try:
            from app.services.action_log_service import ActionLogService
            username = current_user.username if current_user.is_authenticated else None
            
            # Формируем человекочитаемое описание
            description_parts = []
            if len(services) > 0:
                service_word = "услуга" if len(services) == 1 else ("услуги" if len(services) < 5 else "услуг")
                description_parts.append(f"{len(services)} {service_word}")
            if len(parts) > 0:
                part_word = "запчасть" if len(parts) == 1 else ("запчасти" if len(parts) < 5 else "запчастей")
                description_parts.append(f"{len(parts)} {part_word}")
            
            description = "Продажа в заявке: " + ", ".join(description_parts) if description_parts else "Продажа в заявке"
            if result.get('payment_id'):
                description += " (с оплатой)"
            
            ActionLogService.log_action(
                user_id=user_id,
                username=username,
                action_type='sell',
                entity_type='order',
                entity_id=order_id,
                description=description,
                details={
                    'Услуг': len(services),
                    'Товаров': len(parts),
                    'ID оплаты': result.get('payment_id')
                }
            )
        except Exception as e:
            logger.warning(f"Не удалось залогировать продажу: {e}")
        
        return jsonify({
            'success': True,
            'services_added': result['services_added'],
            'parts_added': result['parts_added'],
            'payment_id': result['payment_id']
        }), 201
    except (ValidationError, NotFoundError) as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except DatabaseError as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    except Exception as e:
        logger.error(f"Ошибка при объединенной продаже для заявки {order_id}: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


@bp.route('/api/search/items', methods=['GET'])
@login_required
def search_items():
    """API для поиска услуг и товаров (единый полнотекстовый поиск)."""
    try:
        query = request.args.get('q', '').strip()
        
        if not query:
            return jsonify({
                'success': True,
                'items': [],
                'count': 0
            })
        
        query_lower = query.lower()
        # Разбиваем запрос на слова для полнотекстового поиска
        query_words = [w.strip() for w in query_lower.split() if w.strip()]
        
        if not query_words:
            return jsonify({
                'success': True,
                'items': [],
                'count': 0
            })
        
        results = []
        
        # Получаем услуги и товары из базы напрямую для полнотекстового поиска
        with get_db_connection() as conn:
            cursor = conn.cursor()
            price_col = WarehouseQueries._part_price_column(cursor)
            price_sel = f"COALESCE(p.{price_col}, 0)"
            
            # Поиск услуг - ищем по любому из слов в названии (OR логика)
            # Создаем условие для поиска по любому слову
            service_conditions = []
            service_params = []
            for word in query_words:
                service_conditions.append("LOWER(name) LIKE ?")
                service_params.append(f'%{word}%')
            
            service_sql = f"""
                SELECT id, name, price
                FROM services
                WHERE {' OR '.join(service_conditions)}
                ORDER BY 
                    CASE 
                        WHEN LOWER(name) = ? THEN 1
                        WHEN LOWER(name) LIKE ? THEN 2
                        WHEN LOWER(name) LIKE ? THEN 3
                        ELSE 4
                    END,
                    name
                LIMIT 50
            """
            # Добавляем параметры для сортировки (точное совпадение, затем начинается с запроса, затем содержит)
            service_params.extend([query_lower, f'{query_lower}%', f'%{query_lower}%'])
            
            cursor.execute(service_sql, service_params)
            for row in cursor.fetchall():
                results.append({
                    'id': row[0],
                    'name': row[1],
                    'price': float(row[2] or 0),
                    'type': 'service',
                    'icon': 'fas fa-wrench',
                    'stock': None
                })
            
            # Поиск товаров - полнотекстовый поиск по названию, артикулу, описанию
            # Ищем по любому из слов в любом из полей (OR логика)
            part_conditions = []
            part_params = []
            for word in query_words:
                # Ищем в названии, артикуле (part_number), описании
                part_conditions.append("""
                    (LOWER(p.name) LIKE ? 
                     OR LOWER(COALESCE(p.part_number, '')) LIKE ? 
                     OR LOWER(COALESCE(p.description, '')) LIKE ?)
                """)
                part_params.extend([f'%{word}%', f'%{word}%', f'%{word}%'])
            
            # Запрос для поиска товаров (retail_price или price — как в справочнике склада)
            part_sql = f"""
                SELECT p.id, p.name, p.part_number, 
                       {price_sel} as price,
                       COALESCE(p.stock_quantity, 0) as stock
                FROM parts p
                WHERE ({' OR '.join(part_conditions)})
                  AND (p.is_deleted IS NULL OR p.is_deleted = 0)
                ORDER BY 
                    CASE 
                        WHEN LOWER(p.name) = ? THEN 1
                        WHEN LOWER(p.name) LIKE ? THEN 2
                        WHEN LOWER(COALESCE(p.part_number, '')) LIKE ? THEN 3
                        WHEN LOWER(p.name) LIKE ? THEN 4
                        ELSE 5
                    END,
                    p.name
                LIMIT 50
            """
            # Добавляем параметры для сортировки
            part_params.extend([
                query_lower,  # Точное совпадение названия
                f'{query_lower}%',  # Начинается с запроса
                f'%{query_lower}%',  # Содержит в артикуле
                f'%{query_lower}%'   # Содержит в названии
            ])
            
            cursor.execute(part_sql, part_params)
            for row in cursor.fetchall():
                st = int(row[4] or 0)
                results.append({
                    'id': row[0],
                    'name': row[1],
                    'sku': row[2] or '',  # part_number
                    'price': float(row[3] or 0),
                    'purchase_price': 0,  # Можно добавить если нужно
                    'type': 'part',
                    'icon': 'fas fa-box',
                    'stock': st,
                    'stock_quantity': st,
                })
        
        # Сортируем: сначала услуги, потом товары, внутри по релевантности (уже отсортировано в SQL)
        results.sort(key=lambda x: (0 if x['type'] == 'service' else 1))
        
        resp = jsonify({'success': True, 'items': results, 'count': len(results)})
        resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        resp.headers['Pragma'] = 'no-cache'
        return resp
    except Exception as e:
        logger.error(f"Ошибка при поиске товаров и услуг: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


@bp.route('/add_order/customers/search', methods=['GET'])
@login_required
@permission_required('create_orders')
def api_search_customers_for_order():
    """Поиск клиентов для формы /add_order по ФИО/названию и телефону."""
    query = (request.args.get('q') or '').strip()
    if len(query) < 2:
        return jsonify({'success': True, 'customers': []})

    q_lower = query.lower()
    digits = ''.join(ch for ch in query if ch.isdigit())

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            sql = """
                SELECT id, name, phone, email
                FROM customers
                WHERE LOWER(COALESCE(name, '')) LIKE ?
                   OR LOWER(COALESCE(name, '')) LIKE ?
            """
            params = [f"{q_lower}%", f"%{q_lower}%"]

            # Если в запросе есть цифры — добавляем поиск по телефону.
            if digits:
                norm_digits = normalize_phone(digits)
                phone_patterns = {digits, norm_digits}
                if len(norm_digits) >= 10:
                    phone_patterns.add(norm_digits[-10:])
                if norm_digits.startswith('7') and len(norm_digits) == 11:
                    phone_patterns.add('8' + norm_digits[1:])

                for _ in phone_patterns:
                    sql += " OR COALESCE(phone, '') LIKE ?"
                params.extend([f"%{p}%" for p in phone_patterns])

            sql += """
                ORDER BY
                    CASE
                        WHEN LOWER(COALESCE(name, '')) = ? THEN 1
                        WHEN LOWER(COALESCE(name, '')) LIKE ? THEN 2
                        ELSE 3
                    END,
                    name
                LIMIT 20
            """
            params.extend([q_lower, f"{q_lower}%"])

            cursor.execute(sql, params)
            customers = []
            for row in cursor.fetchall():
                phone = row[2] or ''
                customers.append({
                    'id': row[0],
                    'name': row[1] or '',
                    'phone': phone,
                    'phone_display': format_phone_display(phone),
                    'email': row[3] or '',
                })

            _enrich_add_order_customer_search_rows(cursor, customers)

            return jsonify({'success': True, 'customers': customers})
    except Exception as e:
        logger.error(f"Ошибка при поиске клиентов в add_order: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

