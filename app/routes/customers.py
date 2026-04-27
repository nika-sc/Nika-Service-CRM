"""
Blueprint для работы с клиентами.
"""
from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash, current_app
from flask_login import login_required
from app.routes.main import permission_required
from flask_wtf.csrf import CSRFError
from app.services.customer_service import CustomerService
from app.services.device_service import DeviceService
from app.services.reference_service import ReferenceService
from app.utils.validators import normalize_phone
from app.utils.exceptions import ValidationError, NotFoundError, DatabaseError
import logging
import html as _html
import json as _json
import re as _re
import sqlite3
from app.database.connection import get_db_connection
from app.database.queries.customer_queries import CustomerQueries

bp = Blueprint('customers', __name__)
logger = logging.getLogger(__name__)

def format_phone_display(phone: str) -> str:
    """Форматирует телефон для отображения."""
    if not phone:
        return ''
    digits = normalize_phone(phone)
    if len(digits) == 11 and digits.startswith('7'):
        return f"+{digits[0]}({digits[1:4]}){digits[4:7]}-{digits[7:9]}-{digits[9:]}"
    return phone

@bp.route('/clients')
@login_required
@permission_required('view_customers')
def clients():
    """Список всех клиентов."""
    search_query = request.args.get('q', '').strip()
    # Страница использует server-side DataTables, данные подгружаются через AJAX.
    return render_template('clients.html',
        customers=[],
        search_query=search_query,
        page=1,
        pages=1,
        total=0
    )

def _format_date_ddmmyyyy(dt_str: str) -> str:
    if not dt_str:
        return ''
    # ожидаем 'YYYY-MM-DD ...'
    try:
        date_part = dt_str.split(' ')[0]
        y, m, d = date_part.split('-')
        return f"{d}.{m}.{y}"
    except Exception:
        return dt_str

def _phone_digits(s: str) -> str:
    if not s:
        return ''
    return _re.sub(r'[^0-9]', '', str(s))

@bp.route('/api/datatables/clients')
@login_required
@permission_required('view_customers')
def api_datatables_clients():
    """Server-side DataTables источник данных для /clients."""
    draw = int(request.args.get('draw', 1))
    start = int(request.args.get('start', 0))
    length = int(request.args.get('length', 25))
    if length <= 0:
        length = 25
    if length > 200:
        length = 200
    page = (start // length) + 1

    search_value = (request.args.get('search[value]', '') or '').strip()

    # Сортировка (поддерживаем только базовые поля, остальное — по имени)
    order_col = int(request.args.get('order[0][column]', 0) or 0)
    order_dir = (request.args.get('order[0][dir]', 'asc') or 'asc').upper()
    sort_order = 'DESC' if order_dir == 'DESC' else 'ASC'
    sort_by = {0: 'name', 1: 'phone', 2: 'email'}.get(order_col, 'name')

    # Нормализация поиска по телефону: если запрос "похож на телефон", ищем по цифрам
    search_q = None
    if search_value:
        digits = _phone_digits(search_value)
        if digits and len(digits) >= 6 and not _re.search(r'[A-Za-zА-Яа-я]', search_value):
            search_q = digits
        else:
            search_q = search_value

    result = CustomerQueries.get_customers_with_details(
        search_query=search_q,
        page=page,
        per_page=length,
        sort_by=sort_by,
        sort_order=sort_order
    )

    # recordsTotal: без search
    with get_db_connection(row_factory=sqlite3.Row) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) AS cnt FROM customers")
        records_total = int(cursor.fetchone()['cnt'])

    records_filtered = int(result['total'])

    data = []
    for c in result['items']:
        cid = c.get('id')
        name = c.get('name') or '—'
        phone = c.get('phone') or ''
        email = c.get('email') or ''
        devices_count = int(c.get('devices_count') or 0)
        orders_count = int(c.get('orders_count') or 0)
        last_order_date = c.get('last_order_date')

        name_html = (
            f'<a href="/clients/{cid}" class="text-primary fw-bold text-decoration-none" '
            f'onclick="event.stopPropagation();">{_html.escape(str(name))}</a>'
        )

        # Телефон + меню
        phone_digits = _phone_digits(phone)
        if phone_digits:
            phone_formatted = phone_digits
            if len(phone_digits) == 11 and phone_digits.startswith('7'):
                phone_formatted = f"+{phone_digits[0]}({phone_digits[1:4]}){phone_digits[4:7]}-{phone_digits[7:9]}-{phone_digits[9:]}"
            phone_html = (
                '<div class="contact-item">'
                f'<span class="contact-value" data-phone="{phone_digits}" '
                f'onclick="showPhoneMenu(event, \'{phone_digits}\')">{_html.escape(phone_formatted)}</span>'
                f'<div class="contact-dropdown" id="phoneMenu-{phone_digits}">'
                f'<a href="tel:{phone_digits}" class="contact-dropdown-item" onclick="event.stopPropagation();">'
                '<i class="fas fa-phone"></i> Позвонить</a>'
                f'<a href="https://wa.me/{phone_digits}" class="contact-dropdown-item" onclick="event.stopPropagation();">'
                '<i class="fab fa-whatsapp"></i> WhatsApp</a>'
                f'<a href="viber://chat?number={phone_digits}" class="contact-dropdown-item" onclick="event.stopPropagation();">'
                '<i class="fab fa-viber"></i> Viber</a>'
                f'<a href="https://t.me/+{(phone_digits if phone_digits.startswith("7") else ("7" + phone_digits[1:] if len(phone_digits) == 11 and phone_digits.startswith("8") else phone_digits))}" class="contact-dropdown-item" onclick="event.stopPropagation();">'
                '<i class="fab fa-telegram"></i> Написать в Телеграмм</a>'
                f'<a href="#" class="contact-dropdown-item" onclick="copyToClipboard(\'{phone_digits}\', event)">'
                '<i class="fas fa-copy"></i> Копировать</a>'
                '</div>'
                f'<button class="contact-btn" onclick="copyToClipboard(\'{phone_digits}\', event)" title="Копировать">'
                '<i class="fas fa-copy"></i></button>'
                '</div>'
            )
        else:
            phone_html = '<span class="text-muted">—</span>'

        if email:
            email_esc = _html.escape(str(email))
            email_html = (
                '<div class="contact-item">'
                f'<a href="mailto:{email_esc}" class="contact-value" onclick="event.stopPropagation();">{email_esc}</a>'
                f'<button class="contact-btn" onclick="copyToClipboard({_json.dumps(str(email))}, event)" title="Копировать">'
                '<i class="fas fa-copy"></i></button>'
                '</div>'
            )
        else:
            email_html = '<span class="text-muted">—</span>'

        devices_html = f'<span class="badge bg-info" data-order="{devices_count}">{devices_count}</span>'
        orders_html = f'<span class="badge bg-primary" data-order="{orders_count}">{orders_count}</span>'

        if last_order_date:
            last_order_html = f'<span data-order="{_html.escape(str(last_order_date))}">{_html.escape(_format_date_ddmmyyyy(str(last_order_date)))}</span>'
        else:
            last_order_html = '<span class="text-muted" data-order="0">—</span>'

        actions_html = (
            '<div class="btn-group" role="group">'
            f'<a href="/clients/{cid}" class="btn btn-sm btn-primary" title="Просмотр" onclick="event.stopPropagation();">'
            '<i class="fas fa-eye"></i></a>'
            f'<a href="/add_order?customer_id={cid}" class="btn btn-sm btn-success" title="Создать заявку" onclick="event.stopPropagation();">'
            '<i class="fas fa-file-alt"></i></a>'
            f'<button type="button" class="btn btn-sm btn-info" onclick="event.stopPropagation(); editCustomer({cid})" title="Редактировать">'
            '<i class="fas fa-edit"></i></button>'
            f'<button type="button" class="btn btn-sm btn-warning" onclick="event.stopPropagation(); viewCustomerHistory({cid})" title="История">'
            '<i class="fas fa-history"></i></button>'
            f'<button type="button" class="btn btn-sm btn-danger" onclick="event.stopPropagation(); deleteCustomer({cid}, {_json.dumps(str(name))})" title="Удалить">'
            '<i class="fas fa-trash"></i></button>'
            '</div>'
        )

        data.append({
            "client": name_html,
            "phone": phone_html,
            "email": email_html,
            "devices": devices_html,
            "orders": orders_html,
            "last_order": last_order_html,
            "actions": actions_html,
        })

    return jsonify({
        "draw": draw,
        "recordsTotal": records_total,
        "recordsFiltered": records_filtered,
        "data": data
    })

@bp.route('/clients/<int:client_id>')
@login_required
@permission_required('view_customers')
def client_detail(client_id):
    """Детали клиента."""
    customer = CustomerService.get_customer(client_id)
    if not customer:
        return redirect(url_for('customers.clients'))

    devices = DeviceService.get_customer_devices(client_id)
    orders = CustomerService.get_customer_orders(client_id)
    all_sales = CustomerService.get_customer_all_sales(client_id)
    device_types = ReferenceService.get_device_types()
    device_brands = ReferenceService.get_device_brands()
    symptoms = ReferenceService.get_symptoms()
    appearance_tags = ReferenceService.get_appearance_tags()
    stats = CustomerService.get_customer_statistics(client_id)
    
    customer_dict = customer.to_dict()
    customer_dict['orders_count'] = len(orders) if orders else 0
    customer_dict['devices_count'] = len(devices) if devices else 0
    
    # Получаем дополнительную информацию о заявках для каждого устройства
    devices_list = []
    for device in devices:
        device_dict = device.to_dict()
        # Получаем заявки устройства
        device_orders = DeviceService.get_device_orders(device.id)
        device_dict['orders_count'] = len(device_orders) if device_orders else 0
        
        # Получаем данные последней заявки
        if device_orders and len(device_orders) > 0:
            last_order = device_orders[0]  # Уже отсортированы по дате DESC
            device_dict['last_order_symptom_tags'] = last_order.get('symptom_tags')
            device_dict['last_order_appearance'] = last_order.get('appearance')
            device_dict['last_order_date'] = last_order.get('created_at')
            device_dict['last_order_status'] = last_order.get('status_name')
        else:
            device_dict['last_order_symptom_tags'] = None
            device_dict['last_order_appearance'] = None
            device_dict['last_order_date'] = None
            device_dict['last_order_status'] = None
        
        devices_list.append(device_dict)
    
    return render_template('client_detail.html',
        customer=customer_dict,
        devices=devices_list,
        orders=orders,
        all_sales=all_sales,
        device_types=device_types,
        device_brands=device_brands,
        symptoms=symptoms,
        appearance_tags=appearance_tags,
        stats=stats
    )

@bp.route('/clients/<int:client_id>/create_order')
@login_required
@permission_required('create_orders')
def create_order_from_client(client_id):
    """Создание заявки из клиента."""
    customer = CustomerService.get_customer(client_id)
    if not customer:
        return redirect(url_for('customers.clients'))
    return redirect(url_for('orders.add_order', customer_id=client_id))

# API endpoints для клиентов
@bp.route('/api/customers/lookup')
@login_required
@permission_required('view_customers')
def api_lookup_customer():
    """Поиск клиента по телефону."""
    phone = request.args.get('phone', '')
    if not phone.strip():
        return jsonify({'success': False, 'error': 'phone_required'}), 400
    
    try:
        phone = normalize_phone(phone)
        customer = CustomerService.get_customer_by_phone(phone)
        
        if not customer:
            return jsonify({'success': True, 'found': False})
        
        devices = DeviceService.get_customer_devices(customer.id)
        customer_dict = customer.to_dict()
        devices_list = [d.to_dict() for d in devices]
        
        return jsonify({
            'success': True,
            'found': True,
            'customer': customer_dict,
            'devices': devices_list
        })
    except ValidationError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@bp.route('/api/customers', methods=['POST'])
@login_required
@permission_required('create_customers')
def api_create_customer():
    """API для создания нового клиента."""
    try:
        data = request.get_json(silent=True) or {}
        
        customer = CustomerService.create_customer(data)
        
        return jsonify({
            'success': True, 
            'customer': customer.to_dict(),
            'message': 'Клиент успешно создан'
        }), 201
    except (ValidationError, NotFoundError) as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except DatabaseError as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    except Exception as e:
        logger.exception("Ошибка при создании клиента")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@bp.route('/api/customers/<int:client_id>', methods=['GET'])
@login_required
@permission_required('view_customers')
def api_get_customer(client_id):
    """API для получения данных клиента."""
    try:
        customer = CustomerService.get_customer(client_id)
        if not customer:
            return jsonify({'success': False, 'error': 'Клиент не найден'}), 404
        
        return jsonify({'success': True, 'customer': customer.to_dict()})
    except Exception as e:
        logger.exception("Ошибка при получении клиента")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@bp.route('/api/customers/<int:client_id>', methods=['PUT'])
@login_required
@permission_required('edit_customers')
def api_update_client(client_id):
    """API для обновления данных клиента."""
    try:
        data = request.get_json(silent=True) or {}
        
        CustomerService.update_customer(client_id, data)
        
        customer = CustomerService.get_customer(client_id)
        if not customer:
            return jsonify({'success': False, 'error': 'Клиент не найден'}), 404
        
        return jsonify({'success': True, 'customer': customer.to_dict()})
    except (ValidationError, NotFoundError) as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except DatabaseError as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    except Exception as e:
        logger.exception("Ошибка при обновлении клиента")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@bp.route('/api/customers/<int:client_id>', methods=['DELETE'])
@login_required
@permission_required('delete_customers')
def api_delete_client(client_id):
    """API для удаления клиента."""
    try:
        # Проверяем, есть ли у клиента заявки или устройства
        customer = CustomerService.get_customer(client_id)
        if not customer:
            return jsonify({'success': False, 'error': 'Клиент не найден'}), 404
        
        # Проверяем наличие связанных данных
        if customer.orders_count and customer.orders_count > 0:
            return jsonify({
                'success': False, 
                'error': 'Невозможно удалить клиента с существующими заявками'
            }), 400
        
        if customer.devices_count and customer.devices_count > 0:
            return jsonify({
                'success': False, 
                'error': 'Невозможно удалить клиента с существующими устройствами'
            }), 400
        
        # Удаляем клиента
        from app.database.connection import get_db_connection
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM customers WHERE id = ?', (client_id,))
            conn.commit()
        
        return jsonify({'success': True, 'message': 'Клиент успешно удален'})
    except Exception as e:
        logger.exception("Ошибка при удалении клиента")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@bp.route('/api/customers/<int:client_id>/portal-password', methods=['POST'])
@login_required
@permission_required('edit_customers')
def api_set_portal_password(client_id):
    """API для установки пароля портала клиента (администратором)."""
    try:
        data = request.get_json(silent=True) or {}
        password = data.get('password', '').strip()
        
        if not password:
            return jsonify({'success': False, 'error': 'Пароль обязателен'}), 400
        
        if len(password) < 6:
            return jsonify({'success': False, 'error': 'Пароль должен быть не менее 6 символов'}), 400
        
        from app.services.customer_portal_service import CustomerPortalService
        # Администратор устанавливает пароль - сбрасываем флаг смены пароля
        success = CustomerPortalService.set_portal_password(client_id, password, reset_change_flag=True)
        
        if success:
            return jsonify({'success': True, 'message': 'Пароль портала установлен'})
        else:
            return jsonify({'success': False, 'error': 'Не удалось установить пароль'}), 500
    except Exception as e:
        logger.exception("Ошибка при установке пароля портала")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@bp.route('/api/customers/<int:client_id>/portal-password', methods=['DELETE'])
@login_required
@permission_required('edit_customers')
def api_remove_portal_password(client_id):
    """API для удаления пароля портала клиента."""
    try:
        from app.services.customer_portal_service import CustomerPortalService
        success = CustomerPortalService.disable_portal(client_id)
        
        if success:
            return jsonify({'success': True, 'message': 'Пароль портала удален'})
        else:
            return jsonify({'success': False, 'error': 'Не удалось удалить пароль'}), 500
    except Exception as e:
        logger.exception("Ошибка при удалении пароля портала")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@bp.route('/api/customers/<int:client_id>/portal-password/show', methods=['GET'])
@login_required
@permission_required('view_customers')
def api_show_portal_password(client_id):
    """API для получения сгенерированного пароля из action_logs."""
    try:
        # Проверяем, что пароль не был изменен клиентом
        customer = CustomerService.get_customer(client_id)
        if not customer:
            return jsonify({'success': False, 'error': 'Клиент не найден'}), 404
        
        if customer.portal_password_changed:
            return jsonify({
                'success': False, 
                'error': 'Пароль был изменен клиентом. Невозможно показать оригинальный пароль.'
            }), 400
        
        # Ищем пароль в action_logs
        from app.services.action_log_service import ActionLogService
        from app.database.connection import get_db_connection
        import sqlite3
        import json
        
        with get_db_connection(row_factory=sqlite3.Row) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT details, created_at
                FROM action_logs
                WHERE entity_type = 'customer_portal_password'
                AND entity_id = ?
                ORDER BY created_at DESC
                LIMIT 1
            ''', (client_id,))
            
            row = cursor.fetchone()
            if row and row['details']:
                try:
                    details = json.loads(row['details']) if isinstance(row['details'], str) else row['details']
                    password = details.get('generated_password')
                    if password:
                        return jsonify({
                            'success': True,
                            'password': password,
                            'generated_at': row['created_at'],
                            'note': 'Этот пароль был автоматически сгенерирован при создании клиента. При первом входе клиент должен сменить его.'
                        })
                except (json.JSONDecodeError, KeyError):
                    pass
        
        return jsonify({
            'success': False,
            'error': 'Пароль не найден в истории. Возможно, клиент был создан до внедрения этой функции.'
        }), 404
    except Exception as e:
        logger.exception("Ошибка при получении пароля портала")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@bp.route('/api/clients/<int:client_id>/devices', methods=['POST'])
@login_required
@permission_required('edit_customers')
def api_add_device_to_client(client_id):
    """API для добавления устройства клиенту."""
    try:
        data = request.get_json(silent=True) or {}
        device_type_id = int(data.get('device_type_id'))
        device_brand_id = int(data.get('device_brand_id'))
        serial_number = (data.get('serial_number') or '').strip() or None
        password = (data.get('password') or '').strip() or None
        symptom_tags = (data.get('symptom_tags') or '').strip() or None
        appearance_tags = (data.get('appearance_tags') or '').strip() or None
        comment = (data.get('comment') or '').strip() or None
        
        device = DeviceService.create_device(
            client_id, device_type_id, device_brand_id, serial_number,
            password=password, symptom_tags=symptom_tags, appearance_tags=appearance_tags,
            comment=comment
        )
        
        if not device:
            return jsonify({'success': False, 'error': 'Failed to create device'}), 500
        
        devices = DeviceService.get_customer_devices(client_id)
        devices_list = [d.to_dict() for d in devices]
        
        return jsonify({'success': True, 'devices': devices_list}), 201
    except (ValidationError, NotFoundError) as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except DatabaseError as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/clients/<int:client_id>/devices/<int:device_id>', methods=['PUT', 'DELETE'])
@login_required
@permission_required('edit_customers')
def api_device_detail(client_id, device_id):
    """API для обновления и удаления устройства."""
    if request.method == 'PUT':
        try:
            data = request.get_json(silent=True) or {}
            device_type_id = data.get('device_type_id')
            device_brand_id = data.get('device_brand_id')
            serial_number = data.get('serial_number')
            password = (data.get('password') or '').strip() or None
            symptom_tags = (data.get('symptom_tags') or '').strip() or None
            appearance_tags = (data.get('appearance_tags') or '').strip() or None
            comment = (data.get('comment') or '').strip() or None
            
            # Проверяем, что устройство принадлежит клиенту
            device = DeviceService.get_device(device_id)
            if not device:
                return jsonify({'success': False, 'error': 'Устройство не найдено'}), 404
            if device.customer_id != client_id:
                return jsonify({'success': False, 'error': 'Устройство не принадлежит этому клиенту'}), 403
            
            DeviceService.update_device(
                device_id,
                device_type_id=int(device_type_id) if device_type_id else None,
                device_brand_id=int(device_brand_id) if device_brand_id else None,
                serial_number=serial_number,
                password=password,
                symptom_tags=symptom_tags,
                appearance_tags=appearance_tags,
                comment=comment
            )
            
            device = DeviceService.get_device(device_id)
            if not device:
                return jsonify({'success': False, 'error': 'Устройство не найдено'}), 404
            
            return jsonify({'success': True, 'device': device.to_dict()})
        except (ValidationError, NotFoundError) as e:
            logger.error(f"Ошибка при обновлении устройства {device_id}: {e}")
            return jsonify({'success': False, 'error': str(e)}), 400
        except DatabaseError as e:
            logger.error(f"Ошибка БД при обновлении устройства {device_id}: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
        except Exception as e:
            logger.exception(f"Неожиданная ошибка при обновлении устройства {device_id}")
            return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500
    
    if request.method == 'DELETE':
        try:
            # Проверяем, что устройство принадлежит клиенту
            device = DeviceService.get_device(device_id)
            if not device:
                logger.warning(f"Попытка удалить несуществующее устройство {device_id} для клиента {client_id}")
                return jsonify({'success': False, 'error': 'Устройство не найдено'}), 404
            
            if device.customer_id != client_id:
                logger.warning(f"Попытка удалить устройство {device_id} клиента {device.customer_id} от имени клиента {client_id}")
                return jsonify({'success': False, 'error': 'Устройство не принадлежит этому клиенту'}), 403
            
            DeviceService.delete_device(device_id)
            logger.info(f"Устройство {device_id} успешно удалено для клиента {client_id}")
            return jsonify({'success': True}), 200
        except ValidationError as e:
            logger.error(f"Ошибка валидации при удалении устройства {device_id}: {e}")
            return jsonify({'success': False, 'error': str(e)}), 400
        except NotFoundError as e:
            logger.error(f"Устройство {device_id} не найдено при удалении: {e}")
            return jsonify({'success': False, 'error': str(e)}), 404
        except DatabaseError as e:
            logger.error(f"Ошибка БД при удалении устройства {device_id}: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
        except Exception as e:
            logger.exception(f"Неожиданная ошибка при удалении устройства {device_id}: {e}")
            return jsonify({'success': False, 'error': f'Внутренняя ошибка сервера: {str(e)}'}), 500

