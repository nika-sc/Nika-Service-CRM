"""
Blueprint для работы со складом.
"""
from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash
from flask_login import login_required, current_user
from app.routes.main import permission_required
from app.services.warehouse_service import WarehouseService
from app.services.reference_service import ReferenceService
from app.services.action_log_service import ActionLogService
from app.services.user_service import UserService
from app.utils.exceptions import ValidationError, NotFoundError, DatabaseError
from app.utils.datetime_utils import get_moscow_now
import logging

bp = Blueprint('warehouse', __name__)
logger = logging.getLogger(__name__)


@bp.before_request
def _warehouse_api_permission_gate():
    """Единый RBAC-гейт для складских API endpoint-ов."""
    is_api_endpoint = request.path.startswith('/api/warehouse/') or request.path.startswith('/warehouse/api/')
    if not is_api_endpoint:
        return None

    if not current_user.is_authenticated:
        return jsonify({'success': False, 'error': 'auth_required'}), 401

    permission_name = 'view_warehouse' if request.method in ('GET', 'HEAD', 'OPTIONS') else 'manage_warehouse'
    if not UserService.check_permission(current_user.id, permission_name):
        return jsonify({
            'success': False,
            'error': 'forbidden',
            'required_permission': permission_name
        }), 403

    return None


@bp.route('/warehouse')
@bp.route('/warehouse/')
@bp.route('/warehouse/parts')
@login_required
@permission_required('view_warehouse')
def parts_list():
    """Страница списка товаров на складе."""
    from urllib.parse import unquote_plus
    
    search_query = request.args.get('q', '').strip()
    category_raw = request.args.get('category')
    # Декодируем категорию из URL (плюсы заменяются на пробелы)
    category = unquote_plus(category_raw) if category_raw else None
    low_stock_only = request.args.get('low_stock', '0') == '1'
    sort_by = request.args.get('sort_by', 'name')
    sort_order = request.args.get('sort_order', 'ASC').upper()
    page = int(request.args.get('page', 1))
    per_page = 50
    
    # Валидация sort_order
    if sort_order not in ('ASC', 'DESC'):
        sort_order = 'ASC'
    
    paginator = WarehouseService.get_stock_levels(
        search_query=search_query if search_query else None,
        category=category,
        low_stock_only=low_stock_only,
        page=page,
        per_page=per_page,
        sort_by=sort_by,
        sort_order=sort_order
    )
    
    # Получаем категории для фильтра (иерархические)
    categories = WarehouseService.get_categories()
    # Получаем плоский список для выпадающего списка
    all_categories_flat = WarehouseService.get_all_categories_flat()
    
    return render_template('warehouse/parts_list.html',
        items=paginator.items,
        search_query=search_query,
        category=category,
        low_stock_only=low_stock_only,
        sort_by=sort_by,
        sort_order=sort_order,
        categories=categories,
        all_categories_flat=all_categories_flat,
        page=paginator.page,
        pages=paginator.pages,
        total=paginator.total
    )


# ========== Роуты для товаров ==========

@bp.route('/warehouse/parts/new', methods=['GET', 'POST'])
@login_required
@permission_required('manage_warehouse')
def new_part():
    """Создание нового товара."""
    if request.method == 'GET':
        # Используем иерархическую структуру категорий
        categories = WarehouseService.get_categories()
        # Также получаем плоский список для удобства работы в шаблоне
        all_categories_flat = WarehouseService.get_all_categories_flat()
        return render_template('warehouse/part_form.html', 
                             categories=categories,
                             all_categories_flat=all_categories_flat,
                             is_edit=False)
    
    if request.method == 'POST':
        try:
            data = request.get_json(silent=True) or {}
            
            part_id = WarehouseService.create_part(
                name=(data.get('name') or '').strip(),
                part_number=(data.get('part_number') or '').strip(),
                category=data.get('category'),
                category_id=int(data.get('category_id')) if data.get('category_id') else None,
                unit=data.get('unit', 'шт'),
                stock_quantity=int(data.get('stock_quantity', 0)),
                retail_price=float(data.get('retail_price', 0)),
                purchase_price=float(data.get('purchase_price', 0)) if data.get('purchase_price') else None,
                warranty_days=int(data.get('warranty_days')) if data.get('warranty_days') else None,
                comment=(data.get('comment') or '').strip() or None,
                description=(data.get('description') or '').strip() or None,
                min_quantity=int(data.get('min_quantity', 0)),
                salary_rule_type=data.get('salary_rule_type'),
                salary_rule_value=float(data.get('salary_rule_value')) if data.get('salary_rule_value') is not None else None
            )
            
            # Логируем создание товара
            try:
                part = WarehouseService.get_part_by_id(part_id)
                part_name = part.get('name', '')
                part_number = part.get('part_number', '')
                stock_qty = part.get('stock_quantity', 0)
                price = part.get('retail_price', 0)
                category = part.get('category', '')
                
                # Формируем естественное описание
                description_parts = []
                description_parts.append(f"Добавлен товар «{part_name}»")
                if part_number:
                    description_parts.append(f"артикул {part_number}")
                if category:
                    description_parts.append(f"категория: {category}")
                if stock_qty > 0:
                    description_parts.append(f"остаток: {stock_qty} шт.")
                if price > 0:
                    description_parts.append(f"цена: {price:.2f} ₽")
                
                description = ", ".join(description_parts)
                
                ActionLogService.log_action(
                    user_id=current_user.id if current_user.is_authenticated else None,
                    username=current_user.username if current_user.is_authenticated else None,
                    action_type='create',
                    entity_type='part',
                    entity_id=part_id,
                    description=description,
                    details={
                        'name': part_name,
                        'Артикул': part_number,
                        'Категория': category,
                        'Остаток': f"{stock_qty} шт." if stock_qty > 0 else "0 шт.",
                        'Цена': f"{price:.2f} ₽" if price > 0 else "0 ₽"
                    }
                )
            except Exception as e:
                logger.warning(f"Не удалось залогировать создание товара: {e}")
            
            return jsonify({'success': True, 'part_id': part_id}), 201
        except ValidationError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        except Exception as e:
            logger.error(f"Ошибка при создании товара: {e}", exc_info=True)
            return jsonify({'success': False, 'error': f'Internal server error: {str(e)}'}), 500


@bp.route('/warehouse/parts/<int:part_id>')
@login_required
@permission_required('view_warehouse')
def part_detail(part_id):
    """Детали товара."""
    part = WarehouseService.get_part_by_id(part_id)
    if not part:
        flash('Товар не найден', 'error')
        return redirect(url_for('warehouse.parts_list'))
    
    # Получаем историю движений
    movements = WarehouseService.get_stock_movements(part_id=part_id, limit=50)
    
    return render_template('warehouse/part_detail.html', 
                         part=part,
                         movements=movements)


@bp.route('/warehouse/parts/<int:part_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('manage_warehouse')
def edit_part(part_id):
    """Редактирование товара."""
    part = WarehouseService.get_part_by_id(part_id)
    if not part:
        flash('Товар не найден', 'error')
        return redirect(url_for('warehouse.parts_list'))
    
    if request.method == 'GET':
        # Используем иерархическую структуру категорий
        categories = WarehouseService.get_categories()
        # Также получаем плоский список для удобства работы в шаблоне
        all_categories_flat = WarehouseService.get_all_categories_flat()
        return render_template('warehouse/part_form.html', 
                             part=part,
                             categories=categories,
                             all_categories_flat=all_categories_flat,
                             is_edit=True)
    
    if request.method == 'POST':
        try:
            data = request.get_json(silent=True) or {}
            
            # Получаем старые данные для логирования изменений
            old_part = WarehouseService.get_part_by_id(part_id)
            
            WarehouseService.update_part(
                part_id=part_id,
                name=(data.get('name') or '').strip() if data.get('name') is not None else None,
                category=data.get('category'),
                category_id=int(data.get('category_id')) if data.get('category_id') else None,
                unit=data.get('unit'),
                stock_quantity=int(data.get('stock_quantity')) if data.get('stock_quantity') is not None else None,
                retail_price=float(data.get('retail_price')) if data.get('retail_price') is not None else None,
                purchase_price=float(data.get('purchase_price')) if data.get('purchase_price') is not None else None,
                warranty_days=int(data.get('warranty_days')) if data.get('warranty_days') else None,
                comment=(data.get('comment') or '').strip() or None if 'comment' in data else None,
                description=(data.get('description') or '').strip() or None if 'description' in data else None,
                min_quantity=int(data.get('min_quantity')) if data.get('min_quantity') is not None else None,
                salary_rule_type=data.get('salary_rule_type'),
                salary_rule_value=float(data.get('salary_rule_value')) if data.get('salary_rule_value') is not None else None
            )
            
            # Логируем обновление товара
            try:
                new_part = WarehouseService.get_part_by_id(part_id)
                changes = {}
                if old_part and new_part:
                    for key in ['name', 'part_number', 'category', 'stock_quantity', 'retail_price']:
                        if old_part.get(key) != new_part.get(key):
                            changes[key] = {
                                'old': old_part.get(key),
                                'new': new_part.get(key)
                            }
                
                part_name = new_part.get('name', '')
                part_number = new_part.get('part_number', '')
                description = f"Изменен товар «{part_name}»"
                if part_number:
                    description += f" (артикул: {part_number})"
                
                # Форматируем изменения с русскими названиями полей
                formatted_changes = {}
                if changes:
                    change_labels = {
                        'name': 'Название',
                        'part_number': 'Артикул',
                        'category': 'Категория',
                        'stock_quantity': 'Остаток',
                        'retail_price': 'Цена'
                    }
                    for key, change in changes.items():
                        label = change_labels.get(key, key)
                        old_val = change.get('old')
                        new_val = change.get('new')
                        
                        # Форматируем значения
                        if key == 'stock_quantity':
                            old_val = f"{old_val} шт." if old_val is not None else None
                            new_val = f"{new_val} шт." if new_val is not None else None
                        elif key == 'retail_price':
                            old_val = f"{old_val:.2f} ₽" if old_val is not None else None
                            new_val = f"{new_val:.2f} ₽" if new_val is not None else None
                        
                        formatted_changes[label] = {
                            'old': old_val,
                            'new': new_val
                        }
                
                ActionLogService.log_action(
                    user_id=current_user.id if current_user.is_authenticated else None,
                    username=current_user.username if current_user.is_authenticated else None,
                    action_type='update',
                    entity_type='part',
                    entity_id=part_id,
                    description=description,
                    details={
                        'name': part_name,
                        'Артикул': part_number,
                        'Изменения': formatted_changes if formatted_changes else None
                    }
                )
            except Exception as e:
                logger.warning(f"Не удалось залогировать обновление товара: {e}")
            
            return jsonify({'success': True, 'part_id': part_id}), 200
        except (ValidationError, NotFoundError) as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        except Exception as e:
            logger.error(f"Ошибка при обновлении товара: {e}", exc_info=True)
            return jsonify({'success': False, 'error': f'Internal server error: {str(e)}'}), 500


@bp.route('/warehouse/parts/<int:part_id>/delete', methods=['POST'])
@login_required
@permission_required('manage_warehouse')
def delete_part(part_id):
    """Мягкое удаление товара."""
    try:
        # Получаем данные товара перед удалением для логирования
        part = WarehouseService.get_part_by_id(part_id)
        
        WarehouseService.delete_part(part_id)
        
        # Логируем удаление товара
        try:
            if part:
                part_name = part.get('name', '')
                part_number = part.get('part_number', '')
                description = f"Удален товар «{part_name}»"
                if part_number:
                    description += f" (артикул: {part_number})"
            else:
                description = f"Удален товар (ID: {part_id})"
            
            ActionLogService.log_action(
                user_id=current_user.id if current_user.is_authenticated else None,
                username=current_user.username if current_user.is_authenticated else None,
                action_type='delete',
                entity_type='part',
                entity_id=part_id,
                description=description,
                details={
                    'name': part.get('name') if part else None,
                    'Артикул': part.get('part_number') if part else None
                }
            )
        except Exception as e:
            logger.warning(f"Не удалось залогировать удаление товара: {e}")
        
        return jsonify({'success': True, 'message': 'Товар успешно удален'}), 200
    except (ValidationError, NotFoundError) as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Ошибка при удалении товара: {e}", exc_info=True)
        return jsonify({'success': False, 'error': f'Internal server error: {str(e)}'}), 500


@bp.route('/warehouse/parts/<int:part_id>/restore', methods=['POST'])
@login_required
@permission_required('manage_warehouse')
def restore_part(part_id):
    """Восстановление удаленного товара."""
    try:
        WarehouseService.restore_part(part_id)
        return jsonify({'success': True, 'message': 'Товар успешно восстановлен'}), 200
    except (ValidationError, NotFoundError) as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Ошибка при восстановлении товара: {e}", exc_info=True)
        return jsonify({'success': False, 'error': f'Internal server error: {str(e)}'}), 500


# ========== Роуты для категорий ==========

@bp.route('/warehouse/categories', methods=['GET'])
@login_required
@permission_required('view_warehouse')
def get_categories():
    """API: Получение списка категорий."""
    try:
        categories = WarehouseService.get_categories()
        return jsonify(categories), 200
    except Exception as e:
        logger.error(f"Ошибка при получении категорий: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@bp.route('/warehouse/api/part/<int:part_id>/stock', methods=['GET'])
@login_required
@permission_required('view_warehouse')
def api_part_stock(part_id):
    """API: актуальный остаток товара (для обновления при выборе из кеша)."""
    try:
        part = WarehouseService.get_part_by_id(part_id)
        if not part:
            return jsonify({'success': False, 'error': 'Товар не найден'}), 404
        price = part.get('retail_price') or part.get('price') or 0
        purchase_price = part.get('purchase_price')
        return jsonify({
            'success': True,
            'part_id': part_id,
            'stock_quantity': int(part.get('stock_quantity') or 0),
            'price': float(price),
            'purchase_price': float(purchase_price) if purchase_price is not None and purchase_price != '' else None
        })
    except Exception as e:
        logger.error(f"Ошибка получения остатка товара {part_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/warehouse/api/parts', methods=['GET'])
@login_required
@permission_required('view_warehouse')
def api_parts_for_modal():
    """
    API: Получение списка товаров для модальных окон (JSON).
    Использует WarehouseService.get_stock_levels, чтобы корректно учитывать part_categories (иерархия).
    """
    try:
        search_query = (request.args.get('q') or '').strip() or None
        category = (request.args.get('category') or '').strip() or None  # category name (как в UI/складе)

        paginator = WarehouseService.get_stock_levels(
            search_query=search_query,
            category=category,
            low_stock_only=False,
            page=1,
            per_page=2000,
            sort_by='name',
            sort_order='ASC'
        )

        resp = jsonify({'success': True, 'items': paginator.items})
        resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        resp.headers['Pragma'] = 'no-cache'
        return resp, 200
    except Exception as e:
        logger.error(f"Ошибка при получении товаров для модального окна: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


@bp.route('/warehouse/categories', methods=['POST'])
@login_required
@permission_required('manage_warehouse')
def create_category():
    """API: Создание категории."""
    try:
        data = request.get_json(silent=True) or {}
        parent_id = data.get('parent_id')
        if parent_id:
            try:
                parent_id = int(parent_id)
            except (ValueError, TypeError):
                parent_id = None
        
        category_id = WarehouseService.create_category(
            name=data.get('name', '').strip(),
            description=(data.get('description') or '').strip() or None,
            parent_id=parent_id
        )
        return jsonify({'success': True, 'id': category_id}), 201
    except ValidationError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Ошибка при создании категории: {e}", exc_info=True)
        return jsonify({'success': False, 'error': f'Internal server error: {str(e)}'}), 500


@bp.route('/warehouse/categories/<int:category_id>', methods=['PUT'])
@login_required
@permission_required('manage_warehouse')
def update_category(category_id):
    """API: Обновление категории."""
    try:
        data = request.get_json(silent=True) or {}
        parent_id = data.get('parent_id')
        if parent_id:
            try:
                parent_id = int(parent_id)
            except (ValueError, TypeError):
                parent_id = None
        elif 'parent_id' in data and data['parent_id'] is None:
            parent_id = None
        
        WarehouseService.update_category(
            category_id=category_id,
            name=data.get('name', '').strip(),
            description=(data.get('description') or '').strip() or None,
            parent_id=parent_id
        )
        return jsonify({'success': True}), 200
    except (ValidationError, NotFoundError) as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Ошибка при обновлении категории: {e}", exc_info=True)
        return jsonify({'success': False, 'error': f'Internal server error: {str(e)}'}), 500


@bp.route('/warehouse/categories/<int:category_id>', methods=['DELETE'])
@login_required
@permission_required('manage_warehouse')
def delete_category(category_id):
    """API: Удаление категории."""
    try:
        WarehouseService.delete_category(category_id)
        return jsonify({'success': True}), 200
    except NotFoundError as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Ошибка при удалении категории: {e}", exc_info=True)
        return jsonify({'success': False, 'error': f'Internal server error: {str(e)}'}), 500


# ========== Роуты для приходов/расходов ==========

@bp.route('/warehouse/parts/<int:part_id>/income', methods=['POST'])
@login_required
@permission_required('manage_warehouse')
def part_income(part_id):
    """Приход товара на склад."""
    try:
        data = request.get_json(silent=True) or {}
        
        WarehouseService.add_part_income(
            part_id=part_id,
            quantity=int(data.get('quantity', 0)),
            purchase_price=float(data.get('purchase_price')) if data.get('purchase_price') else None,
            notes=(data.get('notes') or '').strip() or None,
            user_id=current_user.id if current_user.is_authenticated else None
        )
        
        return jsonify({'success': True, 'message': 'Приход товара успешно зарегистрирован'}), 200
    except (ValidationError, NotFoundError) as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Ошибка при приходе товара: {e}", exc_info=True)
        return jsonify({'success': False, 'error': f'Internal server error: {str(e)}'}), 500


@bp.route('/warehouse/parts/<int:part_id>/expense', methods=['POST'])
@login_required
@permission_required('manage_warehouse')
def part_expense(part_id):
    """Расход товара со склада."""
    try:
        data = request.get_json(silent=True) or {}
        
        WarehouseService.add_part_expense(
            part_id=part_id,
            quantity=int(data.get('quantity', 0)),
            reason=(data.get('reason') or '').strip(),
            notes=(data.get('notes') or '').strip() or None,
            user_id=current_user.id if current_user.is_authenticated else None
        )
        
        return jsonify({'success': True, 'message': 'Расход товара успешно зарегистрирован'}), 200
    except (ValidationError, NotFoundError) as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Ошибка при расходе товара: {e}", exc_info=True)
        return jsonify({'success': False, 'error': f'Internal server error: {str(e)}'}), 500


# ========== Роут для логов ==========

@bp.route('/warehouse/logs')
@login_required
@permission_required('view_warehouse')
def warehouse_logs():
    """Страница логов операций со складом."""
    operation_type = request.args.get('operation_type')
    part_id = request.args.get('part_id')
    user_id = request.args.get('user_id')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    try:
        page = int(request.args.get('page', 1))
        if page < 1:
            page = 1
    except (ValueError, TypeError):
        page = 1
    
    per_page = 50
    
    # Получаем логи
    paginator = WarehouseService.get_warehouse_logs(
        operation_type=operation_type,
        part_id=int(part_id) if part_id else None,
        user_id=int(user_id) if user_id else None,
        date_from=date_from,
        date_to=date_to,
        page=page,
        per_page=per_page
    )
    
    # Получаем список товаров для фильтра
    stock_levels = WarehouseService.get_stock_levels(page=1, per_page=1000)
    parts = stock_levels.items
    
    return render_template('warehouse/logs.html',
        logs=paginator.items,
        operation_type=operation_type,
        part_id=part_id,
        user_id=user_id,
        date_from=date_from,
        date_to=date_to,
        page=paginator.page,
        pages=paginator.pages,
        total=paginator.total,
        parts=parts
    )


# ========== Роуты для закупок (оставляем для истории, но скрываем из меню) ==========

@bp.route('/warehouse/purchases')
@login_required
@permission_required('view_warehouse')
def purchases():
    """Список закупок."""
    supplier_id = request.args.get('supplier_id', type=int)
    status = request.args.get('status')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    page = int(request.args.get('page', 1))
    per_page = 50
    
    paginator = WarehouseService.get_purchases(
        supplier_id=supplier_id,
        status=status,
        date_from=date_from,
        date_to=date_to,
        page=page,
        per_page=per_page
    )
    
    return render_template('warehouse/purchases.html',
        purchases=paginator.items,
        supplier_id=supplier_id,
        status=status,
        date_from=date_from,
        date_to=date_to,
        page=paginator.page,
        pages=paginator.pages,
        total=paginator.total
    )


@bp.route('/warehouse/purchases/new', methods=['GET', 'POST'])
@login_required
@permission_required('manage_warehouse')
def new_purchase():
    """Создание новой закупки."""
    if request.method == 'GET':
        parts = ReferenceService.get_parts()
        suppliers = WarehouseService.get_all_suppliers()
        return render_template('warehouse/purchase_form.html', parts=parts, suppliers=suppliers)
    
    if request.method == 'POST':
        try:
            # Логирование входящего запроса
            logger.info(f"POST /warehouse/purchases/new - Content-Type: {request.content_type}")
            logger.info(f"POST /warehouse/purchases/new - Raw data: {request.get_data(as_text=True)}")
            
            data = request.get_json(silent=True) or {}
            logger.info(f"POST /warehouse/purchases/new - Parsed JSON: {data}")
            
            supplier_id = data.get('supplier_id')
            supplier_name = data.get('supplier_name', '').strip()
            purchase_date = data.get('purchase_date', '')
            items = data.get('items', [])
            notes = data.get('notes', '').strip()
            
            # Если передан supplier_id, получаем название поставщика
            if supplier_id and not supplier_name:
                try:
                    supplier = WarehouseService.get_supplier_by_id(supplier_id)
                    supplier_name = supplier['name']
                except NotFoundError:
                    return jsonify({'success': False, 'error': f'Поставщик с ID {supplier_id} не найден'}), 400
            
            logger.info(f"POST /warehouse/purchases/new - supplier_id: {supplier_id}, supplier_name: '{supplier_name}', purchase_date: '{purchase_date}', items count: {len(items) if items else 0}")
            
            if not supplier_name:
                logger.warning("POST /warehouse/purchases/new - Отсутствует supplier_name")
                return jsonify({'success': False, 'error': 'Поставщик обязателен'}), 400
            
            if not purchase_date:
                logger.warning("POST /warehouse/purchases/new - Отсутствует purchase_date")
                return jsonify({'success': False, 'error': 'Дата закупки обязательна'}), 400
            
            if not items or len(items) == 0:
                logger.warning("POST /warehouse/purchases/new - Отсутствуют items")
                return jsonify({'success': False, 'error': 'Должна быть хотя бы одна позиция'}), 400
            
            purchase_id = WarehouseService.create_purchase(
                supplier_id=supplier_id if supplier_id else None,
                supplier_name=supplier_name,
                purchase_date=purchase_date,
                items=items,
                user_id=current_user.id if current_user.is_authenticated else None,
                notes=notes if notes else None
            )
            
            logger.info(f"POST /warehouse/purchases/new - Закупка создана успешно, ID: {purchase_id}")
            return jsonify({'success': True, 'purchase_id': purchase_id}), 201
        except ValidationError as e:
            logger.error(f"POST /warehouse/purchases/new - ValidationError: {e}")
            return jsonify({'success': False, 'error': str(e)}), 400
        except Exception as e:
            logger.error(f"POST /warehouse/purchases/new - Ошибка при создании закупки: {e}", exc_info=True)
            return jsonify({'success': False, 'error': f'Internal server error: {str(e)}'}), 500


@bp.route('/warehouse/purchases/<int:purchase_id>')
@login_required
@permission_required('view_warehouse')
def purchase_detail(purchase_id):
    """Детали закупки."""
    purchase = WarehouseService.get_purchase_by_id(purchase_id)
    if not purchase:
        flash('Закупка не найдена', 'error')
        return redirect(url_for('warehouse.purchases'))
    
    return render_template('warehouse/purchase_detail.html', purchase=purchase)


@bp.route('/warehouse/purchases/<int:purchase_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('manage_warehouse')
def edit_purchase(purchase_id):
    """Редактирование закупки (только черновики)."""
    purchase = WarehouseService.get_purchase_by_id(purchase_id)
    if not purchase:
        flash('Закупка не найдена', 'error')
        return redirect(url_for('warehouse.purchases'))
    
    if purchase['status'] != 'draft':
        flash('Можно редактировать только черновики закупок', 'error')
        return redirect(url_for('warehouse.purchase_detail', purchase_id=purchase_id))
    
    # Получаем список товаров для формы
    parts = ReferenceService.get_parts()
    suppliers = WarehouseService.get_all_suppliers()
    
    if request.method == 'POST':
        try:
            data = request.get_json(silent=True) or {}
            supplier_id = data.get('supplier_id')
            supplier_name = data.get('supplier_name', '').strip()
            purchase_date = data.get('purchase_date', '')
            items = data.get('items', [])
            notes = data.get('notes', '').strip()
            
            # Если передан supplier_id, получаем название поставщика
            if supplier_id and not supplier_name:
                try:
                    supplier = WarehouseService.get_supplier_by_id(supplier_id)
                    supplier_name = supplier['name']
                except NotFoundError:
                    return jsonify({'success': False, 'error': f'Поставщик с ID {supplier_id} не найден'}), 400
            
            logger.info(f"POST /warehouse/purchases/{purchase_id}/edit - supplier_id: {supplier_id}, supplier_name: '{supplier_name}', items count: {len(items) if items else 0}")
            
            WarehouseService.update_purchase(
                purchase_id=purchase_id,
                supplier_id=supplier_id if supplier_id else None,
                supplier_name=supplier_name,
                purchase_date=purchase_date,
                items=items,
                user_id=current_user.id if current_user.is_authenticated else None,
                notes=notes if notes else None
            )
            
            logger.info(f"POST /warehouse/purchases/{purchase_id}/edit - Закупка обновлена успешно")
            return jsonify({'success': True, 'purchase_id': purchase_id}), 200
        except ValidationError as e:
            logger.error(f"POST /warehouse/purchases/{purchase_id}/edit - ValidationError: {e}")
            return jsonify({'success': False, 'error': str(e)}), 400
        except NotFoundError as e:
            logger.error(f"POST /warehouse/purchases/{purchase_id}/edit - NotFoundError: {e}")
            return jsonify({'success': False, 'error': str(e)}), 404
        except Exception as e:
            logger.error(f"POST /warehouse/purchases/{purchase_id}/edit - Ошибка при обновлении закупки: {e}", exc_info=True)
            return jsonify({'success': False, 'error': f'Internal server error: {str(e)}'}), 500
    
    # GET запрос - показываем форму редактирования
    parts = ReferenceService.get_parts()
    suppliers = WarehouseService.get_all_suppliers()
    return render_template('warehouse/purchase_form.html', 
                         purchase=purchase, 
                         parts=parts,
                         suppliers=suppliers,
                         is_edit=True)


@bp.route('/warehouse/purchases/<int:purchase_id>/delete', methods=['POST'])
@login_required
@permission_required('manage_warehouse')
def delete_purchase(purchase_id):
    """Удаление закупки (только черновики)."""
    try:
        logger.info(f"POST /warehouse/purchases/{purchase_id}/delete - Попытка удалить закупку")
        
        WarehouseService.delete_purchase(
            purchase_id=purchase_id,
            user_id=current_user.id if current_user.is_authenticated else None
        )
        
        logger.info(f"POST /warehouse/purchases/{purchase_id}/delete - Закупка удалена успешно")
        return jsonify({'success': True, 'message': 'Закупка успешно удалена'}), 200
    except ValidationError as e:
        logger.warning(f"POST /warehouse/purchases/{purchase_id}/delete - ValidationError: {e}")
        return jsonify({'success': False, 'error': str(e)}), 400
    except NotFoundError as e:
        logger.warning(f"POST /warehouse/purchases/{purchase_id}/delete - NotFoundError: {e}")
        return jsonify({'success': False, 'error': str(e)}), 404
    except Exception as e:
        logger.error(f"POST /warehouse/purchases/{purchase_id}/delete - Ошибка при удалении закупки: {e}", exc_info=True)
        return jsonify({'success': False, 'error': f'Внутренняя ошибка сервера: {str(e)}'}), 500


@bp.route('/warehouse/purchases/<int:purchase_id>/complete', methods=['POST'])
@login_required
@permission_required('manage_warehouse')
def complete_purchase(purchase_id):
    """Завершение закупки (обновление остатков)."""
    try:
        logger.info(f"Попытка завершить закупку {purchase_id}, пользователь: {current_user.id if current_user.is_authenticated else 'не авторизован'}")
        
        # Проверяем, существует ли закупка
        try:
            purchase = WarehouseService.get_purchase_by_id(purchase_id)
        except Exception as e:
            logger.error(f"Ошибка при получении закупки {purchase_id}: {e}", exc_info=True)
            return jsonify({'success': False, 'error': f'Ошибка при получении данных закупки: {str(e)}'}), 500
        
        if not purchase:
            logger.warning(f"Закупка {purchase_id} не найдена")
            return jsonify({'success': False, 'error': f'Закупка с ID {purchase_id} не найдена'}), 404
        
        logger.info(f"Закупка {purchase_id} найдена, статус: {purchase.get('status')}, ключи: {list(purchase.keys())}")
        
        # Проверяем статус
        purchase_status = purchase.get('status')
        if purchase_status == 'completed':
            logger.warning(f"Закупка {purchase_id} уже завершена")
            return jsonify({'success': False, 'error': 'Закупка уже завершена'}), 400
        
        # Проверяем наличие позиций
        items = purchase.get('items', [])
        logger.info(f"Закупка {purchase_id}: items = {items}, тип: {type(items)}, длина: {len(items) if items else 0}")
        
        if not items or len(items) == 0:
            logger.warning(f"Закупка {purchase_id} не содержит позиций (items: {items})")
            return jsonify({'success': False, 'error': 'Закупка не содержит позиций. Добавьте хотя бы одну позицию перед завершением.'}), 400
        
        logger.info(f"Закупка {purchase_id} содержит {len(items)} позиций: {[item.get('part_name', 'N/A') for item in items]}")
        
        # Завершаем закупку
        try:
            WarehouseService.complete_purchase(
                purchase_id=purchase_id,
                user_id=current_user.id if current_user.is_authenticated else None
            )
        except ValidationError as e:
            logger.warning(f"Ошибка валидации в complete_purchase для закупки {purchase_id}: {e}")
            return jsonify({'success': False, 'error': str(e)}), 400
        except NotFoundError as e:
            logger.warning(f"Закупка {purchase_id} не найдена в complete_purchase: {e}")
            return jsonify({'success': False, 'error': str(e)}), 404
        except Exception as e:
            logger.error(f"Ошибка в complete_purchase для закупки {purchase_id}: {e}", exc_info=True)
            return jsonify({'success': False, 'error': f'Ошибка при завершении закупки: {str(e)}'}), 500
        
        logger.info(f"Закупка {purchase_id} успешно завершена")
        return jsonify({'success': True, 'message': 'Закупка успешно завершена'})
    except Exception as e:
        logger.error(f"Неожиданная ошибка при завершении закупки {purchase_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'error': f'Внутренняя ошибка сервера: {str(e)}'}), 500


@bp.route('/warehouse/movements')
@login_required
@permission_required('view_warehouse')
def movements():
    """Движения товаров."""
    part_id = request.args.get('part_id', type=int)
    movement_type = request.args.get('movement_type')
    operation_type = request.args.get('operation_type')  # 'manual' или 'auto'
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    limit = int(request.args.get('limit', 100))
    
    movements = WarehouseService.get_stock_movements(
        part_id=part_id,
        movement_type=movement_type,
        operation_type=operation_type if operation_type else None,
        date_from=date_from,
        date_to=date_to,
        limit=limit
    )
    
    return render_template('warehouse/movements.html',
        movements=movements,
        part_id=part_id,
        movement_type=movement_type,
        operation_type=operation_type,
        date_from=date_from,
        date_to=date_to
    )


@bp.route('/api/warehouse/adjust-stock', methods=['POST'])
@login_required
@permission_required('manage_warehouse')
def api_adjust_stock():
    """API для корректировки остатка товара."""
    try:
        data = request.get_json(silent=True) or {}
        part_id = data.get('part_id')
        quantity = data.get('quantity')
        reason = data.get('reason', '').strip()
        
        if not part_id:
            return jsonify({'success': False, 'error': 'ID товара обязателен'}), 400
        
        if not quantity or quantity == 0:
            return jsonify({'success': False, 'error': 'Количество не может быть нулевым'}), 400
        
        if not reason:
            return jsonify({'success': False, 'error': 'Причина корректировки обязательна'}), 400
        
        WarehouseService.adjust_stock(
            part_id=int(part_id),
            quantity=int(quantity),
            reason=reason,
            user_id=current_user.id if current_user.is_authenticated else None
        )
        
        return jsonify({'success': True})
    except (ValidationError, NotFoundError) as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Ошибка при корректировке остатка: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


# ========== Роуты для поставщиков ==========

@bp.route('/warehouse/suppliers')
@login_required
@permission_required('view_warehouse')
def suppliers_list():
    """Список поставщиков."""
    suppliers = WarehouseService.get_all_suppliers(include_inactive=False)
    return render_template('warehouse/suppliers_list.html', suppliers=suppliers)


@bp.route('/warehouse/suppliers/new', methods=['GET', 'POST'])
@login_required
@permission_required('manage_warehouse')
def new_supplier():
    """Создание нового поставщика."""
    if request.method == 'GET':
        return render_template('warehouse/supplier_form.html', is_edit=False)
    
    try:
        # Логируем входящий запрос для отладки
        logger.info(f"POST /warehouse/suppliers/new - Content-Type: {request.content_type}")
        logger.info(f"POST /warehouse/suppliers/new - Raw data: {request.get_data(as_text=True)}")
        
        data = request.get_json(silent=True) or {}
        logger.info(f"POST /warehouse/suppliers/new - Parsed JSON: {data}")
        
        if not data.get('name'):
            return jsonify({'success': False, 'error': 'Название поставщика обязательно'}), 400
        
        supplier_id = WarehouseService.create_supplier(
            name=data.get('name', '').strip(),
            contact_person=data.get('contact_person', '').strip() or None,
            phone=data.get('phone', '').strip() or None,
            email=data.get('email', '').strip() or None,
            address=data.get('address', '').strip() or None,
            inn=data.get('inn', '').strip() or None,
            comment=data.get('comment', '').strip() or None
        )
        logger.info(f"POST /warehouse/suppliers/new - Поставщик создан успешно, ID: {supplier_id}")
        return jsonify({'success': True, 'supplier_id': supplier_id}), 201
    except ValidationError as e:
        logger.warning(f"POST /warehouse/suppliers/new - ValidationError: {e}")
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"POST /warehouse/suppliers/new - Ошибка при создании поставщика: {e}", exc_info=True)
        return jsonify({'success': False, 'error': f'Internal server error: {str(e)}'}), 500


@bp.route('/warehouse/suppliers/<int:supplier_id>')
@login_required
@permission_required('view_warehouse')
def supplier_detail(supplier_id):
    """Детали поставщика."""
    supplier = WarehouseService.get_supplier_by_id(supplier_id)
    return render_template('warehouse/supplier_detail.html', supplier=supplier)


@bp.route('/warehouse/suppliers/<int:supplier_id>/edit', methods=['GET', 'POST'])
@login_required
@permission_required('manage_warehouse')
def edit_supplier(supplier_id):
    """Редактирование поставщика."""
    if request.method == 'GET':
        supplier = WarehouseService.get_supplier_by_id(supplier_id)
        return render_template('warehouse/supplier_form.html', supplier=supplier, is_edit=True)
    
    try:
        data = request.get_json(silent=True) or {}
        WarehouseService.update_supplier(
            supplier_id=supplier_id,
            name=data.get('name', '').strip(),
            contact_person=data.get('contact_person', '').strip() or None,
            phone=data.get('phone', '').strip() or None,
            email=data.get('email', '').strip() or None,
            address=data.get('address', '').strip() or None,
            inn=data.get('inn', '').strip() or None,
            comment=data.get('comment', '').strip() or None,
            is_active=data.get('is_active', True)
        )
        return jsonify({'success': True})
    except (ValidationError, NotFoundError) as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Ошибка при обновлении поставщика: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


@bp.route('/warehouse/suppliers/<int:supplier_id>/delete', methods=['POST'])
@login_required
@permission_required('manage_warehouse')
def delete_supplier(supplier_id):
    """Удаление поставщика."""
    try:
        WarehouseService.delete_supplier(supplier_id)
        return jsonify({'success': True})
    except NotFoundError as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Ошибка при удалении поставщика: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


# ========== Роуты для инвентаризации ==========

@bp.route('/warehouse/inventory')
@login_required
@permission_required('view_warehouse')
def inventory_list():
    """Список инвентаризаций."""
    status = request.args.get('status')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    inventories = WarehouseService.get_all_inventories(
        status=status,
        date_from=date_from,
        date_to=date_to,
        limit=100
    )
    return render_template('warehouse/inventory_list.html', 
                         inventories=inventories, 
                         status=status,
                         date_from=date_from,
                         date_to=date_to)


@bp.route('/warehouse/inventory/new', methods=['GET', 'POST'])
@login_required
@permission_required('manage_warehouse')
def new_inventory():
    """Создание новой инвентаризации."""
    if request.method == 'GET':
        parts = ReferenceService.get_parts()
        return render_template('warehouse/inventory_form.html', 
                             parts=parts, 
                             is_edit=False,
                             date_today=get_moscow_now().date().isoformat())
    
    try:
        data = request.get_json(silent=True) or {}
        inventory_id = WarehouseService.create_inventory(
            name=data.get('name', '').strip(),
            inventory_date=data.get('inventory_date', ''),
            items=data.get('items', []),
            notes=data.get('notes', '').strip() or None,
            user_id=current_user.id if current_user.is_authenticated else None
        )
        return jsonify({'success': True, 'inventory_id': inventory_id}), 201
    except ValidationError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Ошибка при создании инвентаризации: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500


@bp.route('/warehouse/inventory/<int:inventory_id>')
@login_required
@permission_required('view_warehouse')
def inventory_detail(inventory_id):
    """Детали инвентаризации."""
    inventory = WarehouseService.get_inventory_by_id(inventory_id)
    return render_template('warehouse/inventory_detail.html', inventory=inventory)


@bp.route('/warehouse/inventory/<int:inventory_id>/complete', methods=['POST'])
@login_required
@permission_required('manage_warehouse')
def complete_inventory(inventory_id):
    """Завершение инвентаризации (применение корректировок)."""
    try:
        WarehouseService.complete_inventory(
            inventory_id=inventory_id,
            user_id=current_user.id if current_user.is_authenticated else None
        )
        return jsonify({'success': True})
    except (ValidationError, NotFoundError) as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Ошибка при завершении инвентаризации: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

