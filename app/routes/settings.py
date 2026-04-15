"""
Blueprint для работы со справочниками (settings API).
"""
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from app.services.reference_service import ReferenceService
from app.services.action_log_service import ActionLogService
from app.utils.exceptions import ValidationError, NotFoundError, DatabaseError
from app.utils.cache_helpers import clear_reference_cache
import logging

logger = logging.getLogger(__name__)


def log_settings_action(action_type: str, entity_type: str, entity_id: int = None, description: str = None, details: dict = None):
    """Логирует действие в настройках."""
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
        logger.warning(f"Не удалось записать лог действия: {e}")

bp = Blueprint('settings', __name__)

# Получаем csrf и limiter из текущего приложения
def get_csrf():
    """Получает CSRFProtect из текущего приложения."""
    return current_app.extensions.get('csrf')

# Глобальная переменная для limiter (устанавливается через init_limiter)
limiter = None

def init_limiter(app_limiter):
    """Инициализирует limiter для этого blueprint."""
    global limiter
    limiter = app_limiter

def rate_limit_if_available(limit_str):
    """Декоратор для rate limiting, если limiter доступен."""
    def decorator(f):
        from functools import wraps
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Проверяем limiter во время выполнения, а не во время декорирования
            if limiter:
                return limiter.limit(limit_str)(f)(*args, **kwargs)
            return f(*args, **kwargs)
        return wrapper
    return decorator

# Device Types
@bp.route('/device-types', methods=['GET', 'POST'])
@login_required
def api_device_types():
    """API для типов устройств."""
    if request.method == 'GET':
        device_types = ReferenceService.get_device_types()
        return jsonify(device_types)
    
    if request.method == 'POST':
        try:
            data = request.get_json(silent=True) or {}
            name = data.get('name', '').strip()
            sort_order = data.get('sort_order')
            
            if not name:
                return jsonify({'success': False, 'error': 'Название обязательно'}), 400
            
            # Проверяем, существует ли уже такой тип устройства
            from app.database.queries.reference_queries import ReferenceQueries
            existing_types = ReferenceQueries.get_device_types()
            for existing_type in existing_types:
                if existing_type['name'].lower() == name.lower():
                    # Возвращаем существующий ID
                    clear_reference_cache('device_types')
                    return jsonify({'success': True, 'id': existing_type['id']}), 200
            
            type_id = ReferenceService.create_device_type(name, sort_order)
            clear_reference_cache('device_types')
            log_settings_action('create', 'device_type', type_id, 
                f'Добавлен тип устройства: {name}', {'name': name})
            return jsonify({'success': True, 'id': type_id}), 201
        except (ValidationError, DatabaseError) as e:
            # Если это ошибка дубликата, пытаемся найти существующий элемент
            error_msg = str(e)
            if 'уже существует' in error_msg.lower() or 'already exists' in error_msg.lower():
                try:
                    from app.database.queries.reference_queries import ReferenceQueries
                    existing_types = ReferenceQueries.get_device_types()
                    for existing_type in existing_types:
                        if existing_type['name'].lower() == name.lower():
                            clear_reference_cache('device_types')
                            return jsonify({'success': True, 'id': existing_type['id']}), 200
                except Exception:
                    pass
            return jsonify({'success': False, 'error': str(e)}), 400
        except Exception as e:
            logger.error(f"Ошибка при создании типа устройства: {e}")
            return jsonify({'success': False, 'error': 'Internal server error'}), 500

@bp.route('/device-types/<int:type_id>', methods=['PUT', 'DELETE'])
@login_required
def api_device_type_detail(type_id):
    """API для типа устройства."""
    if request.method == 'PUT':
        try:
            data = request.get_json(silent=True) or {}
            name = data.get('name', '').strip()
            sort_order = data.get('sort_order')
            
            if not name:
                return jsonify({'success': False, 'error': 'Название обязательно'}), 400
            
            success = ReferenceService.update_device_type(type_id, name, sort_order)
            clear_reference_cache('device_types')
            
            if success:
                log_settings_action('update', 'device_type', type_id,
                    f'Изменён тип устройства: {name}', {'name': name})
                return jsonify({'success': True})
            return jsonify({'success': False, 'error': 'Тип устройства не найден'}), 404
        except (ValidationError, NotFoundError) as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        except DatabaseError as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    if request.method == 'DELETE':
        try:
            # Получаем название перед удалением для лога
            from app.database.queries.reference_queries import ReferenceQueries
            existing_types = ReferenceQueries.get_device_types()
            type_name = None
            for t in existing_types:
                if t['id'] == type_id:
                    type_name = t['name']
                    break
            
            success = ReferenceService.delete_device_type(type_id)
            clear_reference_cache('device_types')
            
            if success:
                log_settings_action('delete', 'device_type', type_id,
                    f'Удалён тип устройства: {type_name or type_id}', {'name': type_name})
                return jsonify({'success': True})
            return jsonify({'success': False, 'error': 'Тип устройства не найден'}), 404
        except (ValidationError, NotFoundError) as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        except DatabaseError as e:
            return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/device-types/update-sort-order', methods=['POST'])
@login_required
def api_update_device_types_sort_order():
    """API для обновления порядка сортировки типов устройств."""
    try:
        data = request.get_json(silent=True) or {}
        items = data.get('items', [])
        
        if not items:
            return jsonify({'success': False, 'error': 'items required'}), 400
        
        ReferenceService.update_device_types_sort_order(items)
        clear_reference_cache('device_types')
        return jsonify({'success': True})
    except (ValidationError, DatabaseError) as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Ошибка при обновлении порядка сортировки: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

# Device Brands
@bp.route('/device-brands', methods=['GET', 'POST'])
@login_required
def api_device_brands():
    """API для брендов устройств."""
    if request.method == 'GET':
        device_brands = ReferenceService.get_device_brands()
        return jsonify(device_brands)
    
    if request.method == 'POST':
        try:
            data = request.get_json(silent=True) or {}
            name = data.get('name', '').strip()
            sort_order = data.get('sort_order')
            
            if not name:
                return jsonify({'success': False, 'error': 'Название обязательно'}), 400
            
            # Проверяем, существует ли уже такой бренд устройства
            from app.database.queries.reference_queries import ReferenceQueries
            existing_brands = ReferenceQueries.get_device_brands()
            for existing_brand in existing_brands:
                if existing_brand['name'].lower() == name.lower():
                    # Возвращаем существующий ID
                    clear_reference_cache('device_brands')
                    return jsonify({'success': True, 'id': existing_brand['id']}), 200
            
            brand_id = ReferenceService.create_device_brand(name, sort_order)
            clear_reference_cache('device_brands')
            log_settings_action('create', 'device_brand', brand_id,
                f'Добавлен бренд устройства: {name}', {'name': name})
            return jsonify({'success': True, 'id': brand_id}), 201
        except (ValidationError, DatabaseError) as e:
            # Если это ошибка дубликата, пытаемся найти существующий элемент
            error_msg = str(e)
            if 'уже существует' in error_msg.lower() or 'already exists' in error_msg.lower():
                try:
                    from app.database.queries.reference_queries import ReferenceQueries
                    existing_brands = ReferenceQueries.get_device_brands()
                    for existing_brand in existing_brands:
                        if existing_brand['name'].lower() == name.lower():
                            clear_reference_cache('device_brands')
                            return jsonify({'success': True, 'id': existing_brand['id']}), 200
                except Exception:
                    pass
            return jsonify({'success': False, 'error': str(e)}), 400
        except Exception as e:
            logger.error(f"Ошибка при создании бренда: {e}")
            return jsonify({'success': False, 'error': 'Internal server error'}), 500

@bp.route('/device-brands/<int:brand_id>', methods=['PUT', 'DELETE'])
@login_required
def api_device_brand_detail(brand_id):
    """API для бренда устройства."""
    if request.method == 'PUT':
        try:
            data = request.get_json(silent=True) or {}
            name = data.get('name', '').strip()
            sort_order = data.get('sort_order')
            
            if not name:
                return jsonify({'success': False, 'error': 'Название обязательно'}), 400
            
            success = ReferenceService.update_device_brand(brand_id, name, sort_order)
            clear_reference_cache('device_brands')
            
            if success:
                log_settings_action('update', 'device_brand', brand_id,
                    f'Изменён бренд устройства: {name}', {'name': name})
                return jsonify({'success': True})
            return jsonify({'success': False, 'error': 'Бренд не найден'}), 404
        except (ValidationError, NotFoundError) as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        except DatabaseError as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    if request.method == 'DELETE':
        try:
            # Получаем название перед удалением для лога
            from app.database.queries.reference_queries import ReferenceQueries
            existing_brands = ReferenceQueries.get_device_brands()
            brand_name = None
            for b in existing_brands:
                if b['id'] == brand_id:
                    brand_name = b['name']
                    break
            
            success = ReferenceService.delete_device_brand(brand_id)
            clear_reference_cache('device_brands')
            
            if success:
                log_settings_action('delete', 'device_brand', brand_id,
                    f'Удалён бренд устройства: {brand_name or brand_id}', {'name': brand_name})
                return jsonify({'success': True})
            return jsonify({'success': False, 'error': 'Бренд не найден'}), 404
        except (ValidationError, NotFoundError) as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        except DatabaseError as e:
            return jsonify({'success': False, 'error': str(e)}), 500

# Order Models
@bp.route('/order-tags', methods=['GET'])
@login_required
def api_order_tags():
    """API для получения уникальных симптомов и тегов внешнего вида из всех заявок."""
    try:
        from app.database.connection import get_db_connection
        import sqlite3
        
        with get_db_connection(row_factory=sqlite3.Row) as conn:
            cursor = conn.cursor()
            
            # Получаем уникальные симптомы из всех заявок
            cursor.execute('''
                SELECT DISTINCT symptom_tags
                FROM orders
                WHERE symptom_tags IS NOT NULL AND symptom_tags != ''
            ''')
            symptom_rows = cursor.fetchall()
            
            symptoms_set = set()
            for row in symptom_rows:
                if row['symptom_tags']:
                    tags = row['symptom_tags'].split(',')
                    for tag in tags:
                        tag_trimmed = tag.strip()
                        if tag_trimmed:
                            symptoms_set.add(tag_trimmed)
            
            # Получаем уникальные теги внешнего вида из всех заявок
            cursor.execute('''
                SELECT DISTINCT appearance
                FROM orders
                WHERE appearance IS NOT NULL AND appearance != ''
            ''')
            appearance_rows = cursor.fetchall()
            
            appearance_set = set()
            for row in appearance_rows:
                if row['appearance']:
                    tags = row['appearance'].split(',')
                    for tag in tags:
                        tag_trimmed = tag.strip()
                        if tag_trimmed:
                            appearance_set.add(tag_trimmed)
            
            return jsonify({
                'success': True,
                'symptoms': sorted(list(symptoms_set)),
                'appearance': sorted(list(appearance_set))
            })
    except Exception as e:
        logger.error(f"Ошибка при получении тегов из заявок: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@bp.route('/order-models', methods=['GET', 'POST'])
@login_required
def api_order_models():
    """API для моделей устройств."""
    if request.method == 'GET':
        try:
            from app.database.connection import get_db_connection
            import sqlite3
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT id, name FROM order_models ORDER BY name')
                models = [{'id': row['id'], 'name': row['name']} for row in cursor.fetchall()]
            return jsonify(models)
        except Exception as e:
            logger.error(f"Ошибка при получении моделей: {e}")
            return jsonify({'success': False, 'error': 'Internal server error'}), 500
    
    if request.method == 'POST':
        try:
            data = request.get_json(silent=True) or {}
            name = data.get('name', '').strip()
            
            if not name:
                return jsonify({'success': False, 'error': 'Название обязательно'}), 400
            
            # Нормализуем название (первая буква заглавная)
            normalized = name[0].upper() + name[1:] if name else ''
            
            from app.database.connection import get_db_connection
            import sqlite3
            with get_db_connection() as conn:
                cursor = conn.cursor()
                # Проверяем, существует ли уже такая модель
                cursor.execute('SELECT id FROM order_models WHERE name = ?', (normalized,))
                existing = cursor.fetchone()
                if existing:
                    return jsonify({'success': True, 'id': existing[0], 'name': normalized})
                
                # Создаем новую модель
                cursor.execute('INSERT INTO order_models (name) VALUES (?)', (normalized,))
                conn.commit()
                model_id = cursor.lastrowid
                log_settings_action('create', 'order_model', model_id,
                    f'Добавлена модель устройства: {normalized}', {'name': normalized})
                return jsonify({'success': True, 'id': model_id, 'name': normalized}), 201
        except sqlite3.IntegrityError:
            # Модель уже существует
            from app.database.connection import get_db_connection
            import sqlite3
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT id FROM order_models WHERE name = ?', (normalized,))
                existing = cursor.fetchone()
                if existing:
                    return jsonify({'success': True, 'id': existing[0], 'name': normalized})
            return jsonify({'success': False, 'error': 'Модель уже существует'}), 400
        except Exception as e:
            logger.error(f"Ошибка при создании модели: {e}")
            return jsonify({'success': False, 'error': 'Internal server error'}), 500

@bp.route('/order-models/<int:model_id>', methods=['PUT', 'DELETE'])
@login_required
def api_order_model_detail(model_id):
    """API для управления конкретной моделью устройства."""
    from app.database.connection import get_db_connection
    import sqlite3
    
    if request.method == 'PUT':
        try:
            data = request.get_json(silent=True) or {}
            name = data.get('name', '').strip()
            
            if not name:
                return jsonify({'success': False, 'error': 'Название обязательно'}), 400
            
            # Нормализуем название
            normalized = name[0].upper() + name[1:] if name else ''
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                # Проверяем существование модели
                cursor.execute('SELECT id FROM order_models WHERE id = ?', (model_id,))
                if not cursor.fetchone():
                    return jsonify({'success': False, 'error': 'Модель не найдена'}), 404
                
                # Проверяем дубликат
                cursor.execute('SELECT id FROM order_models WHERE name = ? AND id != ?', (normalized, model_id))
                if cursor.fetchone():
                    return jsonify({'success': False, 'error': 'Модель с таким названием уже существует'}), 400
                
                # Обновляем
                cursor.execute('UPDATE order_models SET name = ? WHERE id = ?', (normalized, model_id))
                conn.commit()
                
                clear_reference_cache('order_models')
                log_settings_action('update', 'order_model', model_id,
                    f'Изменена модель устройства: {normalized}', {'name': normalized})
                return jsonify({'success': True, 'name': normalized})
        except Exception as e:
            logger.error(f"Ошибка при обновлении модели: {e}")
            return jsonify({'success': False, 'error': 'Internal server error'}), 500
    
    if request.method == 'DELETE':
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                # Получаем название перед удалением
                cursor.execute('SELECT name FROM order_models WHERE id = ?', (model_id,))
                row = cursor.fetchone()
                if not row:
                    return jsonify({'success': False, 'error': 'Модель не найдена'}), 404
                
                model_name = row[0]
                
                # Проверяем использование в заявках
                cursor.execute('SELECT COUNT(*) FROM orders WHERE model_id = ?', (model_id,))
                usage_count = cursor.fetchone()[0]
                if usage_count > 0:
                    return jsonify({
                        'success': False, 
                        'error': f'Модель используется в {usage_count} заявке(ах) и не может быть удалена'
                    }), 400
                
                # Удаляем
                cursor.execute('DELETE FROM order_models WHERE id = ?', (model_id,))
                conn.commit()
                
                clear_reference_cache('order_models')
                log_settings_action('delete', 'order_model', model_id,
                    f'Удалена модель устройства: {model_name}', {'name': model_name})
                return jsonify({'success': True})
        except Exception as e:
            logger.error(f"Ошибка при удалении модели: {e}")
            return jsonify({'success': False, 'error': 'Internal server error'}), 500

@bp.route('/order-models/<int:model_id>/usage', methods=['GET'])
@login_required
def api_order_model_usage(model_id):
    """API для получения информации об использовании модели устройства."""
    try:
        from app.database.connection import get_db_connection
        import sqlite3
        
        with get_db_connection(row_factory=sqlite3.Row) as conn:
            cursor = conn.cursor()
            
            # Получаем заявки с этой моделью
            cursor.execute('''
                SELECT o.id, o.order_id, c.id as customer_id, c.name as customer_name, c.phone, o.created_at
                FROM orders o
                JOIN customers c ON c.id = o.customer_id
                WHERE o.model_id = ?
                ORDER BY o.created_at DESC
                LIMIT 50
            ''', (model_id,))
            orders = [dict(row) for row in cursor.fetchall()]
            
            # Подсчитываем общее количество
            cursor.execute('SELECT COUNT(*) FROM orders WHERE model_id = ?', (model_id,))
            total_count = cursor.fetchone()[0]
            
            return jsonify({
                'success': True,
                'orders': orders,
                'total_count': total_count,
                'type': 'order_model'
            })
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"Ошибка при получении информации об использовании модели {model_id}: {e}\n{error_trace}")
        error_msg = str(e) if current_app.debug else 'Internal server error'
        return jsonify({'success': False, 'error': error_msg}), 500

@bp.route('/device-brands/update-sort-order', methods=['POST'])
@login_required
def api_update_device_brands_sort_order():
    """API для обновления порядка сортировки брендов."""
    try:
        data = request.get_json(silent=True) or {}
        items = data.get('items', [])
        
        if not items:
            return jsonify({'success': False, 'error': 'items required'}), 400
        
        ReferenceService.update_device_brands_sort_order(items)
        clear_reference_cache('device_brands')
        return jsonify({'success': True})
    except (ValidationError, DatabaseError) as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Ошибка при обновлении порядка сортировки: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

# Symptoms
@bp.route('/symptoms', methods=['GET', 'POST'])
@login_required
def api_symptoms():
    """API для симптомов."""
    if request.method == 'GET':
        symptoms = ReferenceService.get_symptoms()
        return jsonify(symptoms)
    
    if request.method == 'POST':
        try:
            data = request.get_json(silent=True) or {}
            name = data.get('name', '').strip()
            sort_order = data.get('sort_order')
            
            if not name:
                return jsonify({'success': False, 'error': 'Название обязательно'}), 400
            
            symptom_id = ReferenceService.create_symptom(name, sort_order)
            clear_reference_cache('symptoms')
            log_settings_action('create', 'symptom', symptom_id,
                f'Добавлен тег неисправности: {name}', {'name': name})
            return jsonify({'success': True, 'id': symptom_id}), 201
        except (ValidationError, DatabaseError) as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        except Exception as e:
            logger.error(f"Ошибка при создании симптома: {e}")
            return jsonify({'success': False, 'error': 'Internal server error'}), 500

@bp.route('/symptoms/<int:symptom_id>', methods=['PUT', 'DELETE'])
@login_required
def api_symptom_detail(symptom_id):
    """API для симптома."""
    if request.method == 'PUT':
        try:
            data = request.get_json(silent=True) or {}
            name = data.get('name', '').strip()
            sort_order = data.get('sort_order')
            
            if not name:
                return jsonify({'success': False, 'error': 'Название обязательно'}), 400
            
            success = ReferenceService.update_symptom(symptom_id, name, sort_order)
            clear_reference_cache('symptoms')
            
            if success:
                log_settings_action('update', 'symptom', symptom_id,
                    f'Изменён тег неисправности: {name}', {'name': name})
                return jsonify({'success': True})
            return jsonify({'success': False, 'error': 'Симптом не найден'}), 404
        except (ValidationError, NotFoundError) as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        except DatabaseError as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    if request.method == 'DELETE':
        try:
            # Получаем название перед удалением для лога
            symptoms = ReferenceService.get_symptoms()
            symptom_name = None
            for s in symptoms:
                # ReferenceService.get_symptoms() возвращает список словарей
                if s.get('id') == symptom_id:
                    symptom_name = s.get('name')
                    break
            
            success = ReferenceService.delete_symptom(symptom_id)
            clear_reference_cache('symptoms')
            
            if success:
                log_settings_action('delete', 'symptom', symptom_id,
                    f'Удалён тег неисправности: {symptom_name or symptom_id}', {'name': symptom_name})
                return jsonify({'success': True})
            return jsonify({'success': False, 'error': 'Симптом не найден'}), 404
        except (ValidationError, NotFoundError) as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        except DatabaseError as e:
            return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/symptoms/update-sort-order', methods=['POST'])
@login_required
def api_update_symptoms_sort_order():
    """API для обновления порядка сортировки симптомов."""
    try:
        data = request.get_json(silent=True) or {}
        items = data.get('items', [])
        
        if not items:
            return jsonify({'success': False, 'error': 'items required'}), 400
        
        ReferenceService.update_symptoms_sort_order(items)
        clear_reference_cache('symptoms')
        return jsonify({'success': True})
    except (ValidationError, DatabaseError) as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Ошибка при обновлении порядка сортировки: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

# Appearance Tags
@bp.route('/appearance-tags', methods=['GET', 'POST'])
@login_required
def api_appearance_tags():
    """API для тегов внешнего вида."""
    if request.method == 'GET':
        appearance_tags = ReferenceService.get_appearance_tags()
        return jsonify(appearance_tags)
    
    if request.method == 'POST':
        try:
            data = request.get_json(silent=True) or {}
            name = data.get('name', '').strip()
            sort_order = data.get('sort_order')
            
            if not name:
                return jsonify({'success': False, 'error': 'Название обязательно'}), 400
            
            tag_id = ReferenceService.create_appearance_tag(name, sort_order)
            clear_reference_cache('appearance_tags')
            log_settings_action('create', 'appearance_tag', tag_id,
                f'Добавлен тег внешнего вида: {name}', {'name': name})
            return jsonify({'success': True, 'id': tag_id}), 201
        except (ValidationError, DatabaseError) as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        except Exception as e:
            logger.error(f"Ошибка при создании тега: {e}")
            return jsonify({'success': False, 'error': 'Internal server error'}), 500

@bp.route('/appearance-tags/<int:tag_id>', methods=['PUT', 'DELETE'])
@login_required
def api_appearance_tag_detail(tag_id):
    """API для тега внешнего вида."""
    if request.method == 'PUT':
        try:
            data = request.get_json(silent=True) or {}
            name = data.get('name', '').strip()
            sort_order = data.get('sort_order')
            
            if not name:
                return jsonify({'success': False, 'error': 'Название обязательно'}), 400
            
            success = ReferenceService.update_appearance_tag(tag_id, name, sort_order)
            clear_reference_cache('appearance_tags')
            
            if success:
                log_settings_action('update', 'appearance_tag', tag_id,
                    f'Изменён тег внешнего вида: {name}', {'name': name})
                return jsonify({'success': True})
            return jsonify({'success': False, 'error': 'Тег не найден'}), 404
        except (ValidationError, NotFoundError) as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        except DatabaseError as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    if request.method == 'DELETE':
        try:
            # Получаем название перед удалением для лога
            tags = ReferenceService.get_appearance_tags()
            tag_name = None
            for t in tags:
                # ReferenceService.get_appearance_tags() возвращает список словарей
                if t.get('id') == tag_id:
                    tag_name = t.get('name')
                    break
            
            success = ReferenceService.delete_appearance_tag(tag_id)
            clear_reference_cache('appearance_tags')
            
            if success:
                log_settings_action('delete', 'appearance_tag', tag_id,
                    f'Удалён тег внешнего вида: {tag_name or tag_id}', {'name': tag_name})
                return jsonify({'success': True})
            return jsonify({'success': False, 'error': 'Тег не найден'}), 404
        except (ValidationError, NotFoundError) as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        except DatabaseError as e:
            return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/appearance-tags/update-sort-order', methods=['POST'])
@login_required
def api_update_appearance_tags_sort_order():
    """API для обновления порядка сортировки тегов."""
    try:
        data = request.get_json(silent=True) or {}
        items = data.get('items', [])
        
        if not items:
            return jsonify({'success': False, 'error': 'items required'}), 400
        
        ReferenceService.update_appearance_tags_sort_order(items)
        clear_reference_cache('appearance_tags')
        return jsonify({'success': True})
    except (ValidationError, DatabaseError) as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Ошибка при обновлении порядка сортировки: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

# Services
@bp.route('/services', methods=['GET', 'POST'])
@login_required
def api_services():
    """API для услуг."""
    if request.method == 'GET':
        services = ReferenceService.get_services()
        # One-time self-heal for stale cache payloads created before salary fields were returned.
        if services and any('salary_rule_type' not in s or 'salary_rule_value' not in s for s in services):
            clear_reference_cache('services')
            services = ReferenceService.get_services()
        return jsonify(services)
    
    if request.method == 'POST':
        try:
            data = request.get_json(silent=True) or {}
            name = data.get('name', '').strip()
            price = float(data.get('price', 0))
            is_default = int(data.get('is_default', 0))
            sort_order = data.get('sort_order')
            
            if not name:
                return jsonify({'success': False, 'error': 'Название обязательно'}), 400
            
            salary_rule_type = data.get('salary_rule_type')
            salary_rule_value = data.get('salary_rule_value')
            service_id = ReferenceService.create_service(
                name, price, is_default, sort_order,
                salary_rule_type=salary_rule_type,
                salary_rule_value=float(salary_rule_value) if salary_rule_value is not None else None
            )
            clear_reference_cache('services')
            log_settings_action('create', 'service', service_id,
                f'Добавлена услуга: {name} ({price} ₽)', {'name': name, 'price': price, 'is_default': is_default})
            return jsonify({'success': True, 'id': service_id}), 201
        except (ValidationError, DatabaseError) as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        except Exception as e:
            logger.error(f"Ошибка при создании услуги: {e}")
            return jsonify({'success': False, 'error': 'Internal server error'}), 500

@bp.route('/services/<int:service_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def api_service_detail(service_id):
    """API для услуги."""
    if request.method == 'GET':
        services = ReferenceService.get_services()
        svc = next((s for s in services if s.get('id') == service_id), None)
        if not svc:
            return jsonify({'success': False, 'error': 'Услуга не найдена'}), 404
        return jsonify({'success': True, 'id': svc['id'], 'name': svc.get('name'), 'price': float(svc.get('price') or 0)})
    if request.method == 'PUT':
        try:
            data = request.get_json(silent=True) or {}
            name = data.get('name', '').strip() if data.get('name') else None
            price = float(data.get('price')) if data.get('price') is not None else None
            is_default = int(data.get('is_default')) if data.get('is_default') is not None else None
            sort_order = data.get('sort_order')
            
            salary_rule_type = data.get('salary_rule_type')
            salary_rule_value = data.get('salary_rule_value')
            success = ReferenceService.update_service(
                service_id, name, price, is_default, sort_order,
                salary_rule_type=salary_rule_type,
                salary_rule_value=float(salary_rule_value) if salary_rule_value is not None else None
            )
            clear_reference_cache('services')
            
            if success:
                log_settings_action('update', 'service', service_id,
                    f'Изменена услуга: {name}', {'name': name, 'price': price, 'is_default': is_default})
                return jsonify({'success': True})
            return jsonify({'success': False, 'error': 'Услуга не найдена'}), 404
        except (ValidationError, NotFoundError) as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        except DatabaseError as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    if request.method == 'DELETE':
        try:
            # Получаем название перед удалением для лога
            services = ReferenceService.get_services()
            service_name = None
            for s in services:
                if s['id'] == service_id:
                    service_name = s['name']
                    break
            
            success = ReferenceService.delete_service(service_id)
            clear_reference_cache('services')
            
            if success:
                log_settings_action('delete', 'service', service_id,
                    f'Удалена услуга: {service_name or service_id}', {'name': service_name})
                return jsonify({'success': True})
            return jsonify({'success': False, 'error': 'Услуга не найдена'}), 404
        except (ValidationError, NotFoundError) as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        except DatabaseError as e:
            return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/services/update-sort-order', methods=['POST'])
@login_required
def api_update_services_sort_order():
    """API для обновления порядка сортировки услуг."""
    try:
        data = request.get_json(silent=True) or {}
        items = data.get('items', [])
        
        if not items:
            return jsonify({'success': False, 'error': 'items required'}), 400
        
        ReferenceService.update_services_sort_order(items)
        clear_reference_cache('services')
        return jsonify({'success': True})
    except (ValidationError, DatabaseError) as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Ошибка при обновлении порядка сортировки: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

# API для получения информации об использовании справочников
@bp.route('/device-types/<int:type_id>/usage', methods=['GET'])
@login_required
@rate_limit_if_available("1000 per hour")  # Увеличенный лимит для usage endpoints
def api_device_type_usage(type_id):
    """API для получения информации об использовании типа устройства."""
    try:
        from app.database.connection import get_db_connection
        import sqlite3
        
        with get_db_connection(row_factory=sqlite3.Row) as conn:
            cursor = conn.cursor()
            
            # Получаем устройства с этим типом
            cursor.execute('''
                SELECT d.id, d.serial_number, c.id as customer_id, c.name as customer_name, c.phone
                FROM devices d
                JOIN customers c ON c.id = d.customer_id
                WHERE d.device_type_id = ?
                ORDER BY d.created_at DESC
                LIMIT 50
            ''', (type_id,))
            devices = [dict(row) for row in cursor.fetchall()]
            
            # Получаем заявки, которые используют устройства с этим типом
            cursor.execute('''
                SELECT o.id, o.order_id, c.id as customer_id, c.name as customer_name, c.phone, o.created_at
                FROM orders o
                JOIN devices d ON d.id = o.device_id
                JOIN customers c ON c.id = o.customer_id
                WHERE d.device_type_id = ?
                ORDER BY o.created_at DESC
                LIMIT 50
            ''', (type_id,))
            orders = [dict(row) for row in cursor.fetchall()]
            
            # Подсчитываем общее количество устройств
            cursor.execute('SELECT COUNT(*) FROM devices WHERE device_type_id = ?', (type_id,))
            devices_count = cursor.fetchone()[0]
            
            # Подсчитываем общее количество заявок
            cursor.execute('''
                SELECT COUNT(*) FROM orders o
                JOIN devices d ON d.id = o.device_id
                WHERE d.device_type_id = ?
            ''', (type_id,))
            orders_count = cursor.fetchone()[0]
            
            return jsonify({
                'success': True,
                'devices': devices,
                'orders': orders,
                'devices_count': devices_count,
                'orders_count': orders_count,
                'total_count': devices_count + orders_count,
                'type': 'device_type'
            })
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"Ошибка при получении информации об использовании типа устройства {type_id}: {e}\n{error_trace}")
        error_msg = str(e) if current_app.debug else 'Internal server error'
        return jsonify({'success': False, 'error': error_msg}), 500

@bp.route('/device-brands/<int:brand_id>/usage', methods=['GET'])
@login_required
@rate_limit_if_available("1000 per hour")
def api_device_brand_usage(brand_id):
    """API для получения информации об использовании бренда устройства."""
    try:
        from app.database.connection import get_db_connection
        import sqlite3
        
        with get_db_connection(row_factory=sqlite3.Row) as conn:
            cursor = conn.cursor()
            
            # Получаем устройства с этим брендом
            cursor.execute('''
                SELECT d.id, d.serial_number, c.id as customer_id, c.name as customer_name, c.phone
                FROM devices d
                JOIN customers c ON c.id = d.customer_id
                WHERE d.device_brand_id = ?
                ORDER BY d.created_at DESC
                LIMIT 50
            ''', (brand_id,))
            devices = [dict(row) for row in cursor.fetchall()]
            
            # Получаем заявки, которые используют устройства с этим брендом
            cursor.execute('''
                SELECT o.id, o.order_id, c.id as customer_id, c.name as customer_name, c.phone, o.created_at
                FROM orders o
                JOIN devices d ON d.id = o.device_id
                JOIN customers c ON c.id = o.customer_id
                WHERE d.device_brand_id = ?
                ORDER BY o.created_at DESC
                LIMIT 50
            ''', (brand_id,))
            orders = [dict(row) for row in cursor.fetchall()]
            
            # Подсчитываем общее количество устройств
            cursor.execute('SELECT COUNT(*) FROM devices WHERE device_brand_id = ?', (brand_id,))
            devices_count = cursor.fetchone()[0]
            
            # Подсчитываем общее количество заявок
            cursor.execute('''
                SELECT COUNT(*) FROM orders o
                JOIN devices d ON d.id = o.device_id
                WHERE d.device_brand_id = ?
            ''', (brand_id,))
            orders_count = cursor.fetchone()[0]
            
            return jsonify({
                'success': True,
                'devices': devices,
                'orders': orders,
                'devices_count': devices_count,
                'orders_count': orders_count,
                'total_count': devices_count + orders_count,
                'type': 'device_brand'
            })
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"Ошибка при получении информации об использовании бренда устройства {brand_id}: {e}\n{error_trace}")
        error_msg = str(e) if current_app.debug else 'Internal server error'
        return jsonify({'success': False, 'error': error_msg}), 500

@bp.route('/symptoms/<int:symptom_id>/usage', methods=['GET'])
@login_required
@rate_limit_if_available("1000 per hour")
def api_symptom_usage(symptom_id):
    """API для получения информации об использовании симптома."""
    try:
        from app.database.connection import get_db_connection
        import sqlite3
        
        with get_db_connection(row_factory=sqlite3.Row) as conn:
            cursor = conn.cursor()
            
            # Получаем заявки с этим симптомом
            cursor.execute('''
                SELECT o.id, o.order_id, c.id as customer_id, c.name as customer_name, c.phone, o.created_at
                FROM orders o
                JOIN order_symptoms os ON os.order_id = o.id
                JOIN customers c ON c.id = o.customer_id
                WHERE os.symptom_id = ?
                ORDER BY o.created_at DESC
                LIMIT 50
            ''', (symptom_id,))
            orders = [dict(row) for row in cursor.fetchall()]
            
            # Подсчитываем общее количество
            cursor.execute('SELECT COUNT(*) FROM order_symptoms WHERE symptom_id = ?', (symptom_id,))
            total_count = cursor.fetchone()[0]
            
            return jsonify({
                'success': True,
                'orders': orders,
                'total_count': total_count,
                'type': 'symptom'
            })
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"Ошибка при получении информации об использовании симптома {symptom_id}: {e}\n{error_trace}")
        error_msg = str(e) if current_app.debug else 'Internal server error'
        return jsonify({'success': False, 'error': error_msg}), 500

@bp.route('/appearance-tags/<int:tag_id>/usage', methods=['GET'])
@login_required
@rate_limit_if_available("1000 per hour")
def api_appearance_tag_usage(tag_id):
    """API для получения информации об использовании тега внешнего вида."""
    try:
        from app.database.connection import get_db_connection
        import sqlite3
        
        with get_db_connection(row_factory=sqlite3.Row) as conn:
            cursor = conn.cursor()
            
            # Получаем заявки с этим тегом
            cursor.execute('''
                SELECT o.id, o.order_id, c.id as customer_id, c.name as customer_name, c.phone, o.created_at
                FROM orders o
                JOIN order_appearance_tags oat ON oat.order_id = o.id
                JOIN customers c ON c.id = o.customer_id
                WHERE oat.appearance_tag_id = ?
                ORDER BY o.created_at DESC
                LIMIT 50
            ''', (tag_id,))
            orders = [dict(row) for row in cursor.fetchall()]
            
            # Подсчитываем общее количество
            cursor.execute('SELECT COUNT(*) FROM order_appearance_tags WHERE appearance_tag_id = ?', (tag_id,))
            total_count = cursor.fetchone()[0]
            
            return jsonify({
                'success': True,
                'orders': orders,
                'total_count': total_count,
                'type': 'appearance_tag'
            })
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"Ошибка при получении информации об использовании тега {tag_id}: {e}\n{error_trace}")
        error_msg = str(e) if current_app.debug else 'Internal server error'
        return jsonify({'success': False, 'error': error_msg}), 500

@bp.route('/services/<int:service_id>/usage', methods=['GET'])
@login_required
@rate_limit_if_available("1000 per hour")
def api_service_usage(service_id):
    """API для получения информации об использовании услуги."""
    try:
        from app.database.connection import get_db_connection
        import sqlite3
        
        with get_db_connection(row_factory=sqlite3.Row) as conn:
            cursor = conn.cursor()
            
            # Получаем заявки с этой услугой
            cursor.execute('''
                SELECT o.id, o.order_id, c.id as customer_id, c.name as customer_name, c.phone, os.quantity, os.price, o.created_at
                FROM orders o
                JOIN order_services os ON os.order_id = o.id
                JOIN customers c ON c.id = o.customer_id
                WHERE os.service_id = ?
                ORDER BY o.created_at DESC
                LIMIT 50
            ''', (service_id,))
            orders = [dict(row) for row in cursor.fetchall()]
            
            # Подсчитываем общее количество
            cursor.execute('SELECT COUNT(*) FROM order_services WHERE service_id = ?', (service_id,))
            total_count = cursor.fetchone()[0]
            
            return jsonify({
                'success': True,
                'orders': orders,
                'total_count': total_count,
                'type': 'service'
            })
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"Ошибка при получении информации об использовании услуги {service_id}: {e}\n{error_trace}")
        error_msg = str(e) if current_app.debug else 'Internal server error'
        return jsonify({'success': False, 'error': error_msg}), 500


