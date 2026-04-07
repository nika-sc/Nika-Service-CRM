"""
Маршруты для раздела Магазин.
Быстрые продажи услуг и товаров без создания заявки.
"""
from flask import Blueprint, render_template, request, jsonify, url_for
from flask_login import login_required, current_user
import html as _html
import re
from urllib.parse import urljoin
from app.routes.main import permission_required
from app.utils.print_template_renderer import render_print_template
from app.services.finance_service import FinanceService
from app.services.action_log_service import ActionLogService
from app.services.user_service import UserService
from app.services.settings_service import SettingsService
from app.database.connection import get_db_connection
from app.database.queries.warehouse_queries import WarehouseQueries
from app.utils.exceptions import ValidationError
from datetime import timedelta

bp = Blueprint('shop', __name__, url_prefix='/shop')


@bp.before_request
def _shop_api_permission_gate():
    """Единый RBAC-гейт для /shop/api/*."""
    if not request.path.startswith('/shop/api/'):
        return None

    if not current_user.is_authenticated:
        return jsonify({'success': False, 'error': 'auth_required'}), 401

    permission_name = 'view_shop' if request.method in ('GET', 'HEAD', 'OPTIONS') else 'manage_shop'
    if not UserService.check_permission(current_user.id, permission_name):
        return jsonify({
            'success': False,
            'error': 'forbidden',
            'required_permission': permission_name
        }), 403

    return None


@bp.route('/')
@login_required
@permission_required('view_shop')
def index():
    """Главная страница магазина с фильтрами по периодам."""
    import logging
    from datetime import timedelta
    
    # Определяем период на основе preset или дат
    preset = request.args.get('preset', 'today')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    show_refunds = request.args.get('show_refunds', 'all')  # all, only, exclude
    
    # «Сегодня» по московскому времени, чтобы совпадало с датой у пользователя
    from app.utils.datetime_utils import get_moscow_now
    today = get_moscow_now().date()
    
    # Если указаны конкретные даты, используем их
    if date_from and date_to:
        pass  # Используем переданные даты
    else:
        # Определяем период по preset
        if preset == 'today':
            date_from = today.isoformat()
            date_to = today.isoformat()
        elif preset == 'yesterday':
            yesterday = today - timedelta(days=1)
            date_from = yesterday.isoformat()
            date_to = yesterday.isoformat()
        elif preset == 'day_before_yesterday':
            day_before = today - timedelta(days=2)
            date_from = day_before.isoformat()
            date_to = day_before.isoformat()
        elif preset == 'month':
            # Текущий месяц
            date_from = today.replace(day=1).isoformat()
            date_to = today.isoformat()
        elif preset == 'quarter':
            # Текущий квартал
            quarter = (today.month - 1) // 3
            quarter_start_month = quarter * 3 + 1
            date_from = today.replace(month=quarter_start_month, day=1).isoformat()
            date_to = today.isoformat()
        elif preset == 'year':
            # Текущий год
            date_from = today.replace(month=1, day=1).isoformat()
            date_to = today.isoformat()
        else:
            # По умолчанию - сегодня
            date_from = today.isoformat()
            date_to = today.isoformat()
    
    # Инициализируем все переменные значениями по умолчанию
    statistics = {
        'sales_count': 0,
        'total_amount': 0.0,
        'total_discount': 0.0,
        'total_paid': 0.0,
        'avg_amount': 0.0
    }
    sales = []
    
    try:
        # Получаем продажи за период
        sales = FinanceService.get_shop_sales(
            date_from=date_from,
            date_to=date_to,
            limit=1000  # Увеличиваем лимит для отображения всех продаж за период
        )
        
        # Фильтруем по типу (возвраты/продажи)
        if show_refunds == 'only':
            sales = [s for s in sales if s.get('final_amount', 0) < 0]
        elif show_refunds == 'exclude':
            sales = [s for s in sales if s.get('final_amount', 0) >= 0]
        # 'all' - показываем все
    except Exception as e:
        logging.error(f"Ошибка при получении продаж: {e}")
        sales = []
    
    try:
        # Получаем статистику за период
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Статистика продаж
            cursor.execute("""
                SELECT 
                    SUM(CASE WHEN final_amount > 0 THEN 1 ELSE 0 END) as sales_count,
                    COALESCE(SUM(CASE WHEN final_amount > 0 THEN final_amount ELSE 0 END), 0) as total_amount,
                    COALESCE(SUM(CASE WHEN final_amount > 0 THEN discount ELSE 0 END), 0) as total_discount,
                    COALESCE(SUM(CASE WHEN final_amount > 0 THEN paid_amount ELSE 0 END), 0) as total_paid,
                    COALESCE(AVG(CASE WHEN final_amount > 0 THEN final_amount END), 0) as avg_amount,
                    COALESCE(SUM(CASE WHEN final_amount < 0 THEN ABS(final_amount) ELSE 0 END), 0) as refunds_amount,
                    SUM(CASE WHEN final_amount < 0 THEN 1 ELSE 0 END) as refunds_count
                FROM shop_sales
                WHERE DATE(sale_date) >= DATE(?) AND DATE(sale_date) <= DATE(?)
            """, (date_from, date_to))
            
            stats_row = cursor.fetchone()
            if stats_row:
                total_amount = float(stats_row[1] or 0)
                refunds_amount = float(stats_row[5] or 0)
                statistics = {
                    'sales_count': stats_row[0] if stats_row[0] is not None else 0,
                    'total_amount': total_amount,
                    'total_discount': float(stats_row[2] or 0),
                    'total_paid': float(stats_row[3] or 0),
                    'avg_amount': float(stats_row[4] or 0),
                    'refunds_amount': refunds_amount,
                    'refunds_count': stats_row[6] if stats_row[6] is not None else 0,
                    'net_amount': total_amount - refunds_amount
                }
    except Exception as e:
        logging.error(f"Ошибка при получении статистики: {e}")
    
    # Список только мастеров для выбора исполнителя (shop_sales.master_id = users.id)
    masters = []
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT u.id, COALESCE(NULLIF(TRIM(m.name), ''), u.display_name, u.username) AS display_name
                FROM users u
                INNER JOIN masters m ON m.user_id = u.id
                WHERE u.is_active = 1 AND (m.active = 1 OR m.active IS NULL)
                ORDER BY COALESCE(NULLIF(TRIM(m.name), ''), u.username)
            """)
            masters = [{'id': row[0], 'name': row[1] or 'Мастер'} for row in cursor.fetchall()]
    except Exception as e:
        logging.error(f"Ошибка при получении списка мастеров: {e}")
    
    # Пресеты для фильтров
    period_presets = [
        ('today', 'Сегодня'),
        ('yesterday', 'Вчера'),
        ('day_before_yesterday', 'Позавчера'),
        ('month', 'Месяц'),
        ('quarter', 'Квартал'),
        ('year', 'Год'),
    ]
    
    # Способы оплаты из настроек (Общие настройки → Названия способов оплаты)
    payment_method_options = []
    try:
        pm_settings = SettingsService.get_payment_method_settings()
        cash_label = (pm_settings.get('cash_label') or '').strip()
        transfer_label = (pm_settings.get('transfer_label') or '').strip()
        custom_methods = pm_settings.get('custom_methods') or []
        if cash_label:
            payment_method_options.append({'value': 'cash', 'label': cash_label})
        if transfer_label:
            payment_method_options.append({'value': 'transfer', 'label': transfer_label})
        for name in custom_methods:
            name = str(name).strip()
            if name:
                payment_method_options.append({'value': name, 'label': name})
        if not payment_method_options:
            payment_method_options = [{'value': 'cash', 'label': 'Наличные'}]
    except Exception as e:
        logging.error(f"Ошибка при получении способов оплаты: {e}")
        payment_method_options = [{'value': 'cash', 'label': 'Наличные'}]
    
    return render_template(
        'shop/index.html',
        sales=sales,
        date_from=date_from,
        date_to=date_to,
        preset=preset,
        period_presets=period_presets,
        statistics=statistics,
        masters=masters,
        payment_method_options=payment_method_options,
        show_refunds=show_refunds
    )


@bp.route('/sale/<int:sale_id>')
@login_required
@permission_required('view_shop')
def sale_detail(sale_id):
    """Детали продажи. Печать чека — по шаблону «Товарный чек» из настроек."""
    sale = FinanceService.get_shop_sale(sale_id)
    if not sale:
        return render_template('errors/404.html'), 404

    settings = SettingsService.get_general_settings() or {}
    sales_receipt_template_rendered = None
    try:
        sales_tpl = SettingsService.get_print_template_fresh('sales_receipt')
        sales_html = (sales_tpl or {}).get('html_content') if isinstance(sales_tpl, dict) else None
        if sales_html and isinstance(sales_html, str) and sales_html.strip():
            def _safe(v):
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
            if raw_logo_url and re.match(r'^https?://', raw_logo_url, flags=re.IGNORECASE):
                logo_url = url_for('orders.print_logo_proxy', _external=True)
            elif raw_logo_url:
                logo_url = urljoin(request.url_root, raw_logo_url.lstrip('/'))
            else:
                logo_url = raw_logo_url or ''

            sale_date = sale.get('sale_date') or sale.get('created_at')
            created_at_str = ''
            if sale_date:
                from datetime import datetime as _dt
                date_str = str(sale_date).strip()
                for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d']:
                    try:
                        dt = _dt.strptime(date_str[:19] if len(date_str) >= 19 else date_str, fmt)
                        created_at_str = dt.strftime('%d.%m.%Y %H:%M:%S') if ' ' in date_str or 'T' in date_str else dt.strftime('%d.%m.%Y')
                        break
                    except ValueError:
                        continue
                if not created_at_str and len(date_str) >= 10:
                    try:
                        dt = _dt.strptime(date_str[:10], '%Y-%m-%d')
                        created_at_str = dt.strftime('%d.%m.%Y')
                    except ValueError:
                        created_at_str = date_str

            client_name = (sale.get('customer_full_name') or sale.get('customer_name') or '').strip() or '—'
            values = {
                'COMPANY_NAME': _safe(settings.get('org_name') or ''),
                'branch.address': _safe(settings.get('address') or ''),
                'branch.phone': _safe(settings.get('phone') or ''),
                'COMPANY_REQUISITES': _safe(" ".join([p for p in [
                    f"ИНН: {settings.get('inn')}" if settings.get('inn') else "",
                    f"ОГРН: {settings.get('ogrn')}" if settings.get('ogrn') else "",
                ] if p]).strip()),
                'ORDER_NUMBER': _safe(f"#{sale.get('id')}"),
                'ORDER_ID': _safe(str(sale.get('id') or '')),
                'ORDER_UUID': _safe(str(sale.get('id') or '')),
                'STATUS_NAME': _safe('Продажа'),
                'CLIENT_NAME': _safe(client_name),
                'CLIENT_PHONE1': _safe(sale.get('customer_phone') or ''),
                'CLIENT_PHONE': _safe(sale.get('customer_phone') or ''),
                'CLIENT_EMAIL': _safe(''),
                'TOTAL_PAID': _safe(f"{(sale.get('final_amount') or 0):.2f}"),
                'ENGINEER_NAME': _safe(sale.get('master_name') or ''),
                'MASTER_NAME': _safe(sale.get('master_name') or ''),
                'MANAGER_NAME': _safe(sale.get('manager_name') or ''),
                'CURRENCY': _safe('₽'),
                'EMPLOYEE_NAME': _safe(sale.get('master_name') or sale.get('manager_name') or sale.get('created_by_username') or ''),
                'COMPANY_LOGO_URL': _safe(logo_url),
                'COMPANY_LOGO_STYLE': _safe(f"max-width: {logo_max_width}px; max-height: {logo_max_height}px; width: auto; height: auto;"),
                'CREATED_AT': _safe(created_at_str),
            }
            from datetime import datetime as _dt
            now = _dt.now()
            values['DATE_TODAY'] = _safe(now.strftime('%d.%m.%Y'))
            values['TIME_NOW'] = _safe(now.strftime('%H:%M'))

            print_items = []
            total_items_sum = 0.0
            for idx, it in enumerate(sale.get('items') or [], 1):
                qty = int(it.get('quantity') or 1)
                price = float(it.get('price') or 0)
                row_sum = float(it.get('total') or price * qty)
                total_items_sum += row_sum
                name = (it.get('service_name') or it.get('part_name') or 'Позиция').strip()
                sku = (it.get('part_sku') or '').strip()
                print_items.append({
                    'INDEX': _safe(str(idx)),
                    'ITEM_NAME': _safe(name),
                    'ITEM_SKU': _safe(sku),
                    'ITEM_WARRANTY': _safe(''),
                    'ITEM_PRICE': _safe(f"{price:.2f}"),
                    'ITEM_DISCOUNT': _safe('0.00'),
                    'ITEM_QUANTITY': _safe(str(qty)),
                    'ITEM_SUM': _safe(f"{row_sum:.2f}"),
                })
            values['TOTAL_ITEMS'] = _safe(f"{total_items_sum:.2f}")

            for uuid_tag in [
                '701809f9-23dc-4346-aff4-0aef32523aef', 'b6a8f943-e1b0-46e8-a321-b25fcfaf6976',
                'c5286c7d-44aa-4579-8258-935b003998cf', 'c76b5bc7-7a68-4672-9542-cabaf2962600',
                'bc1ae9b1-7b8b-4da6-add5-26982865629e', 'f93f4677-15b5-4e57-97e7-a345cb5b0e21',
                'dfd7aa33-fd89-462a-bbbc-39c1550415da',
            ]:
                values[uuid_tag] = _safe('')

            sales_receipt_template_rendered = render_print_template(sales_html, values, print_items)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Не удалось отрендерить шаблон товарного чека для продажи: %s", e)

    return render_template(
        'shop/sale_detail.html',
        sale=sale,
        settings=settings,
        sales_receipt_template_rendered=sales_receipt_template_rendered,
    )


@bp.route('/api/sales', methods=['POST'])
@login_required
@permission_required('manage_shop')
def api_create_sale():
    """Создать продажу."""
    data = request.get_json()
    
    items = data.get('items', [])
    if not items:
        return jsonify({'success': False, 'error': 'Добавьте хотя бы одну позицию'}), 400
    
    # Валидация позиций
    for item in items:
        if not item.get('price') or float(item.get('price', 0)) <= 0:
            return jsonify({'success': False, 'error': 'Укажите цену для всех позиций'}), 400
    
    try:
        sale_id, sale_info = FinanceService.create_shop_sale(
            items=items,
            customer_id=data.get('customer_id'),
            customer_name=data.get('customer_name'),
            customer_phone=data.get('customer_phone'),
            manager_id=data.get('manager_id'),
            master_id=data.get('master_id'),
            discount=float(data.get('discount', 0)),
            payment_method=data.get('payment_method', 'cash'),
            paid_amount=float(data.get('paid_amount')) if data.get('paid_amount') else None,
            comment=data.get('comment'),
            created_by_id=current_user.id,
            created_by_username=current_user.username
        )
        
        ActionLogService.log_action(
            user_id=current_user.id,
            username=current_user.username,
            action_type='create_shop_sale',
            entity_type='shop_sale',
            entity_id=sale_id,
            description=f"Продажа в магазине на сумму {sale_info['final_amount']:.2f} руб.",
            details={
                'final_amount': sale_info.get('final_amount'),
                'total_amount': sale_info.get('total_amount'),
                'items_count': len(items),
                'customer_name': data.get('customer_name'),
                'payment_method': data.get('payment_method', 'cash')
            }
        )
        
        return jsonify({
            'success': True, 
            'id': sale_id,
            'sale': sale_info
        })
        
    except (ValidationError, ValueError) as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': 'Ошибка при создании продажи'}), 500


@bp.route('/api/sales/<int:sale_id>/refund', methods=['POST'])
@login_required
@permission_required('manage_shop')
def api_refund_sale(sale_id: int):
    """Возврат продажи в магазине."""
    data = request.get_json(silent=True) or {}
    reason = data.get('reason')
    try:
        result = FinanceService.refund_shop_sale(
            sale_id=sale_id,
            user_id=current_user.id,
            username=current_user.username,
            reason=reason
        )
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@bp.route('/api/sales/<int:sale_id>', methods=['DELETE'])
@login_required
@permission_required('manage_shop')
def api_delete_sale(sale_id: int):
    """Удаление продажи из магазина (с возвратом средств и остатков)."""
    data = request.get_json(silent=True) or {}
    reason = data.get('reason')
    try:
        FinanceService.delete_shop_sale(
            sale_id=sale_id,
            user_id=current_user.id,
            username=current_user.username,
            reason=reason
        )
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@bp.route('/api/sales/<int:sale_id>/recalculate-salary', methods=['POST'])
@login_required
@permission_required('manage_shop')
def api_recalculate_shop_sale_salary(sale_id: int):
    """Пересчитать зарплату по продаже магазина (для уже созданных продаж)."""
    sale = FinanceService.get_shop_sale(sale_id)
    if not sale:
        return jsonify({'success': False, 'error': 'Продажа не найдена'}), 404
    try:
        from app.services.salary_service import SalaryService
        created_ids = SalaryService.accrue_salary_for_shop_sale(sale_id)
        return jsonify({'success': True, 'accruals_count': len(created_ids)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/catalog')
@login_required
@permission_required('view_shop')
def api_catalog():
    """Каталог услуг и товаров для выбора вручную (без поиска)."""
    limit_services = min(int(request.args.get('limit_services', 100)), 500)
    limit_parts = min(int(request.args.get('limit_parts', 100)), 500)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, price FROM services ORDER BY name LIMIT ?
        """, (limit_services,))
        services = [{
            'id': row[0],
            'name': row[1],
            'price': row[2] or 0,
            'type': 'service',
            'label': f"🔧 {row[1]} - {(row[2] or 0):.2f} ₽"
        } for row in cursor.fetchall()]
        cursor.execute("""
            SELECT id, name, part_number, price, purchase_price, COALESCE(stock_quantity, 0)
            FROM parts
            WHERE (is_deleted = 0 OR is_deleted IS NULL)
            ORDER BY name LIMIT ?
        """, (limit_parts,))
        parts = []
        for row in cursor.fetchall():
            sku = row[2] or ''
            price = row[3] or 0
            qty = row[5] or 0
            sku_part = f" ({sku})" if sku else ""
            parts.append({
                'id': row[0],
                'name': row[1],
                'sku': sku,
                'price': price,
                'purchase_price': row[4] or 0,
                'type': 'part',
                'label': f"📦 {row[1]}{sku_part} - {price:.2f} ₽ [ост: {qty}]"
            })
        return jsonify({'success': True, 'services': services, 'parts': parts})


@bp.route('/api/search')
@login_required
@permission_required('view_shop')
def api_search():
    """Поиск товаров и услуг."""
    query = request.args.get('q', '').strip()
    
    if not query:
        return jsonify({'success': True, 'results': []})
    
    query_lower = query.lower()
    query_start = f'{query_lower}%'
    query_anywhere = f'%{query_lower}%'
    query_first_word = f'% {query_lower}%'
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        price_col = WarehouseQueries._part_price_column(cursor)
        price_expr = f"COALESCE(p.{price_col}, 0)"
        
        results = []
        
        # LOWER(...) LIKE — работает и в SQLite, и в PostgreSQL (COLLATE NOCASE только в SQLite).
        cursor.execute(
            """
            SELECT id, name, price, 'service' as type
            FROM services
            WHERE (
                LOWER(name) LIKE ? OR LOWER(name) LIKE ? OR LOWER(name) LIKE ?
            )
            ORDER BY
                CASE
                    WHEN LOWER(name) = ? THEN 1
                    WHEN LOWER(name) LIKE ? THEN 2
                    WHEN LOWER(name) LIKE ? THEN 3
                    WHEN LOWER(name) LIKE ? THEN 4
                    ELSE 5
                END,
                name
            LIMIT 20
            """,
            (
                query_start,
                query_anywhere,
                query_first_word,
                query_lower,
                query_start,
                query_first_word,
                query_anywhere,
            ),
        )
        
        for row in cursor.fetchall():
            results.append({
                'id': row[0],
                'name': row[1],
                'price': row[2] or 0,
                'type': 'service',
                'label': f"🔧 {row[1]} - {(row[2] or 0):.2f} ₽"
            })
        
        cursor.execute(
            f"""
            SELECT p.id, p.name, p.part_number, {price_expr}, p.purchase_price, p.stock_quantity, 'part' as type
            FROM parts p
            WHERE (p.is_deleted = 0 OR p.is_deleted IS NULL)
              AND (
                LOWER(p.name) LIKE ? OR LOWER(p.name) LIKE ? OR LOWER(p.name) LIKE ?
                OR LOWER(COALESCE(p.part_number, '')) LIKE ?
                OR LOWER(COALESCE(p.part_number, '')) LIKE ?
                OR LOWER(COALESCE(p.part_number, '')) LIKE ?
              )
            ORDER BY
                CASE
                    WHEN LOWER(p.name) = ? THEN 1
                    WHEN LOWER(p.name) LIKE ? THEN 2
                    WHEN LOWER(p.name) LIKE ? THEN 3
                    WHEN LOWER(COALESCE(p.part_number, '')) LIKE ? THEN 4
                    WHEN LOWER(p.name) LIKE ? THEN 5
                    WHEN LOWER(COALESCE(p.part_number, '')) LIKE ? THEN 6
                    ELSE 7
                END,
                p.name
            LIMIT 20
            """,
            (
                query_start,
                query_anywhere,
                query_first_word,
                query_start,
                query_anywhere,
                query_first_word,
                query_lower,
                query_start,
                query_first_word,
                query_start,
                query_anywhere,
                query_anywhere,
            ),
        )
        
        for row in cursor.fetchall():
            sku = row[2] or ''
            price = row[3] or 0
            qty = row[5] or 0
            sku_part = f" ({sku})" if sku else ""
            results.append({
                'id': row[0],
                'name': row[1],
                'sku': sku,
                'price': price,
                'purchase_price': row[4] or 0,
                'quantity': qty,
                'stock_quantity': qty,  # Добавляем stock_quantity для совместимости
                'type': 'part',
                'label': f"📦 {row[1]}{sku_part} - {price:.2f} ₽ [ост: {qty}]"
            })
        
        return jsonify({'success': True, 'results': results})


@bp.route('/api/customers/search')
@login_required
@permission_required('view_shop')
def api_search_customers():
    """Поиск клиентов."""
    from app.utils.validators import normalize_phone
    import re
    
    query = request.args.get('q', '').strip()
    query_lower = query.lower()
    
    # Проверяем, является ли запрос номером телефона (содержит цифры)
    is_phone_query = bool(re.search(r'\d', query))
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        if is_phone_query:
            # Нормализуем номер телефона для поиска
            normalized_phone = normalize_phone(query)
            
            # Создаем варианты для поиска:
            # 1. Нормализованный (79006579534)
            # 2. С 8 вместо 7 (89006579534)
            # 3. Без первой цифры (9006579534)
            # 4. Оригинальный запрос
            search_patterns = [normalized_phone]
            
            # Если нормализованный начинается с 7, добавляем вариант с 8
            if normalized_phone.startswith('7') and len(normalized_phone) > 1:
                search_patterns.append('8' + normalized_phone[1:])
            
            # Добавляем вариант без первой цифры (если длина >= 10)
            if len(normalized_phone) >= 10:
                search_patterns.append(normalized_phone[1:])
            
            # Добавляем оригинальный запрос (на случай, если он уже нормализован)
            if query != normalized_phone:
                search_patterns.append(query)
            
            # Убираем дубликаты
            search_patterns = list(set(search_patterns))
            
            # Формируем SQL с несколькими вариантами поиска
            phone_conditions = ' OR '.join(['phone LIKE ?'] * len(search_patterns))
            phone_params = [f'%{pattern}%' for pattern in search_patterns]
            
            cursor.execute(f"""
                SELECT id, name, phone, email
                FROM customers 
                WHERE LOWER(name) LIKE ? OR LOWER(name) LIKE ? OR ({phone_conditions})
                ORDER BY 
                    CASE 
                        WHEN LOWER(name) LIKE ? THEN 1
                        WHEN LOWER(name) LIKE ? THEN 2
                        ELSE 3
                    END,
                    name
                LIMIT 20
            """, ([f'{query_lower}%', f'%{query_lower}%'] + phone_params + [f'{query_lower}%', f'%{query_lower}%']))
        else:
            # Обычный поиск по имени - сначала по началу, затем по любому месту
            cursor.execute("""
                SELECT id, name, phone, email
                FROM customers 
                WHERE LOWER(name) LIKE ? OR LOWER(name) LIKE ?
                ORDER BY 
                    CASE 
                        WHEN LOWER(name) LIKE ? THEN 1
                        WHEN LOWER(name) LIKE ? THEN 2
                        ELSE 3
                    END,
                    name
                LIMIT 20
            """, (f'{query_lower}%', f'%{query_lower}%', f'{query_lower}%', f'%{query_lower}%'))
        
        customers = [{
            'id': row[0],
            'name': row[1],
            'phone': row[2],
            'email': row[3],
            'label': f"{row[1]} ({row[2]})" if row[2] else row[1]
        } for row in cursor.fetchall()]
        
        return jsonify({'success': True, 'customers': customers})


