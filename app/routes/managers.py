"""
Роуты для управления менеджерами (только API, без старых HTML-страниц).
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.services.manager_service import ManagerService
from app.services.action_log_service import ActionLogService
from app.utils.exceptions import ValidationError, NotFoundError
import logging

logger = logging.getLogger(__name__)

# Только API blueprint. Старый страничный blueprint (managers_page) удалён как неиспользуемый.
bp = Blueprint('managers', __name__, url_prefix='/api/managers')


@bp.route('', methods=['GET'])
@login_required
def get_managers():
    """Получает список менеджеров."""
    try:
        active_only = request.args.get('active_only', '1') == '1'
        managers = ManagerService.get_all_managers(active_only=active_only)
        return jsonify({'success': True, 'managers': managers})
    except Exception as e:
        logger.error(f"Ошибка при получении менеджеров: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/<int:manager_id>', methods=['GET'])
@login_required
def get_manager(manager_id):
    """Получает менеджера по ID."""
    try:
        manager = ManagerService.get_manager_by_id(manager_id)
        if not manager:
            return jsonify({'success': False, 'error': 'Менеджер не найден'}), 404
        return jsonify({'success': True, 'manager': manager})
    except Exception as e:
        logger.error(f"Ошибка при получении менеджера {manager_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('', methods=['POST'])
@login_required
def create_manager():
    """Создает нового менеджера и автоматически создает пользователя."""
    try:
        # Проверяем права на создание менеджера (только admin)
        from app.services.user_service import UserService
        user = UserService.get_user_by_id(current_user.id)
        if not user:
            return jsonify({'success': False, 'error': 'Пользователь не найден'}), 404
        
        user_role = user.get('role', '')
        # Только admin может создавать менеджеров
        if user_role != 'admin':
            return jsonify({'success': False, 'error': 'Недостаточно прав для создания менеджера. Только администратор может создавать менеджеров.'}), 403
        
        data = request.get_json() or {}
        name = data.get('name')  # ФИО
        login = data.get('login') or data.get('username')  # Email для входа
        password = data.get('password')
        
        if not name:
            return jsonify({'success': False, 'error': 'ФИО обязательно'}), 400
        
        if not login:
            return jsonify({'success': False, 'error': 'Логин (Email) обязателен'}), 400
        
        if not password:
            return jsonify({'success': False, 'error': 'Пароль обязателен'}), 400
        
        def _float_or_none(val):
            if val is None or val == '':
                return None
            try:
                return float(val)
            except (TypeError, ValueError):
                return None
        # Создаем менеджера
        manager_id = ManagerService.create_manager(
            name=name,
            salary_rule_type=data.get('salary_rule_type'),
            salary_rule_value=_float_or_none(data.get('salary_rule_value')),
            salary_percent_services=_float_or_none(data.get('salary_percent_services')),
            salary_percent_parts=_float_or_none(data.get('salary_percent_parts')),
            salary_percent_shop_parts=_float_or_none(data.get('salary_percent_shop_parts')),
            active=int(data.get('active', 1)),
            comment=data.get('comment')
        )
        
        # Получаем права по умолчанию для роли manager
        from app.services.user_service import UserService
        permission_ids = UserService.get_default_permission_ids_for_role('manager')
        
        logger.info(f"Создание менеджера {manager_id} с правами по умолчанию: {permission_ids}")
        
        # Создаем кастомную роль для этого менеджера с правами по умолчанию
        custom_role_name = f'manager_{manager_id}'
        
        try:
            # Создаем кастомную роль с правами по умолчанию
            UserService.create_role(custom_role_name, permission_ids)
            logger.info(f"Создана кастомная роль {custom_role_name} с правами: {permission_ids}")
            
            # Создаем пользователя с логином (email) и стандартной ролью (чтобы обойти валидацию)
            user_id = UserService.create_user(username=login, password=password, role='manager')
            
            # Обновляем роль на кастомную
            from app.database.connection import get_db_connection
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET role = ? WHERE id = ?", (custom_role_name, user_id))
                conn.commit()
            logger.info(f"Роль пользователя обновлена на: {custom_role_name}")
            
            # Связываем менеджера с пользователем
            ManagerService.update_manager(manager_id, user_id=user_id)
        except ValidationError as e:
            # Невалидные права / запрещенные права — откатываем создание менеджера
            try:
                ManagerService.delete_manager(manager_id)
            except Exception:
                pass
            try:
                UserService.delete_role(custom_role_name)
            except Exception:
                pass
            return jsonify({'success': False, 'error': str(e)}), 400
        except Exception as e:
            logger.warning(f"Не удалось создать пользователя для менеджера {manager_id}: {e}")
            # Удаляем менеджера, если не удалось создать пользователя
            ManagerService.delete_manager(manager_id)
            # Удаляем кастомную роль, если она была создана
            try:
                UserService.delete_role(custom_role_name)
            except Exception:
                pass
            return jsonify({'success': False, 'error': f'Не удалось создать пользователя: {str(e)}'}), 400

        # Логируем создание менеджера
        try:
            ActionLogService.log_action(
                user_id=current_user.id if current_user.is_authenticated else None,
                username=current_user.username if current_user.is_authenticated else None,
                action_type='create',
                entity_type='manager',
                entity_id=manager_id,
                description=f'Создан менеджер: {data.get("name", "Без имени")}',
                details={
                    'name': data.get('name'),
                    'salary_rule_type': data.get('salary_rule_type'),
                    'salary_rule_value': data.get('salary_rule_value'),
                    'active': data.get('active', 1)
                }
            )
        except Exception as e:
            logger.warning(f"Не удалось залогировать создание менеджера {manager_id}: {e}")

        return jsonify({'success': True, 'manager_id': manager_id}), 201
    except ValidationError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Ошибка при создании менеджера: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/<int:manager_id>', methods=['PATCH'])
@login_required
def update_manager(manager_id):
    """Обновляет менеджера и связанного пользователя."""
    try:
        data = request.get_json() or {}
        name = data.get('name')
        
        manager = ManagerService.get_manager_by_id(manager_id)
        if not manager:
            return jsonify({'success': False, 'error': 'Менеджер не найден'}), 404
        
        # Если изменилось имя менеджера, обновляем username связанного пользователя
        if name and manager.get('user_id'):
            from app.services.user_service import UserService
            from app.database.connection import get_db_connection
            import sqlite3
            
            try:
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    # Обновляем username пользователя
                    cursor.execute(
                        'UPDATE users SET username = ? WHERE id = ?',
                        (name.strip(), manager['user_id'])
                    )
                    conn.commit()
            except Exception as e:
                logger.warning(f"Не удалось обновить username для пользователя {manager['user_id']}: {e}")
        
        # Обновляем права кастомной роли, если они указаны
        permission_ids = data.get('permission_ids')
        logger.info(f"Обновление менеджера {manager_id}: permission_ids = {permission_ids}, user_id = {manager.get('user_id')}")
        
        # Всегда обновляем права, если есть user_id (даже если permission_ids = [])
        if 'permission_ids' in data and manager.get('user_id'):
            from app.services.user_service import UserService
            from app.database.connection import get_db_connection
            
            # Нормализуем permission_ids
            if not isinstance(permission_ids, list):
                permission_ids = []
            
            logger.info(f"Обновление прав для менеджера {manager_id}: {permission_ids}")
            
            try:
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    # Получаем роль пользователя
                    cursor.execute('SELECT role FROM users WHERE id = ?', (manager['user_id'],))
                    user_role = cursor.fetchone()
                    
                    if user_role:
                        current_role = user_role[0]
                        
                        # Если роль стандартная, создаем кастомную
                        if current_role == 'manager':
                            custom_role_name = f'manager_{manager_id}'
                            UserService.create_role(custom_role_name, permission_ids)
                            # Обновляем роль пользователя
                            cursor.execute("UPDATE users SET role = ? WHERE id = ?", (custom_role_name, manager['user_id']))
                            conn.commit()
                            logger.info(f"Создана кастомная роль {custom_role_name} и обновлена роль пользователя")
                        elif current_role.startswith('manager_'):
                            # Обновляем права существующей кастомной роли
                            UserService.update_role(current_role, permission_ids)
                            logger.info(f"Обновлены права кастомной роли {current_role}")
            except ValidationError as e:
                return jsonify({'success': False, 'error': str(e)}), 400
            except Exception as e:
                logger.error(f"Не удалось обновить права для менеджера {manager_id}: {e}", exc_info=True)
        
        def _float_or_none(val):
            if val is None or val == '':
                return None
            try:
                return float(val)
            except (TypeError, ValueError):
                return None
        update_kw = dict(
            manager_id=manager_id,
            name=name,
            salary_rule_type=data.get('salary_rule_type'),
            salary_rule_value=_float_or_none(data.get('salary_rule_value')),
            active=data.get('active'),
            comment=data.get('comment')
        )
        if 'salary_percent_services' in data:
            update_kw['salary_percent_services'] = _float_or_none(data.get('salary_percent_services'))
        if 'salary_percent_parts' in data:
            update_kw['salary_percent_parts'] = _float_or_none(data.get('salary_percent_parts'))
        if 'salary_percent_shop_parts' in data:
            update_kw['salary_percent_shop_parts'] = _float_or_none(data.get('salary_percent_shop_parts'))
        success = ManagerService.update_manager(**update_kw)

        if success:
            # Логируем обновление менеджера
            try:
                ActionLogService.log_action(
                    user_id=current_user.id if current_user.is_authenticated else None,
                    username=current_user.username if current_user.is_authenticated else None,
                    action_type='update',
                    entity_type='manager',
                    entity_id=manager_id,
                    description=f'Обновлен менеджер: {data.get("name", "Без имени")}',
                    details={
                        'name': data.get('name'),
                        'salary_rule_type': data.get('salary_rule_type'),
                        'salary_rule_value': data.get('salary_rule_value'),
                        'active': data.get('active'),
                        'comment': data.get('comment')
                    }
                )
            except Exception as e:
                logger.warning(f"Не удалось залогировать обновление менеджера {manager_id}: {e}")

        return jsonify({'success': success})
    except NotFoundError as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except ValidationError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Ошибка при обновлении менеджера {manager_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/<int:manager_id>', methods=['DELETE'])
@login_required
def delete_manager(manager_id):
    """Удаляет менеджера."""
    try:
        # Получаем данные менеджера перед удалением для лога
        manager_data = ManagerService.get_manager_by_id(manager_id)
        manager_name = manager_data.get('name', 'Без имени') if manager_data else 'Неизвестен'

        success = ManagerService.delete_manager(manager_id)

        if success:
            # Логируем удаление менеджера
            try:
                ActionLogService.log_action(
                    user_id=current_user.id if current_user.is_authenticated else None,
                    username=current_user.username if current_user.is_authenticated else None,
                    action_type='delete',
                    entity_type='manager',
                    entity_id=manager_id,
                    description=f'Удален менеджер: {manager_name}',
                    details={'name': manager_name}
                )
            except Exception as e:
                logger.warning(f"Не удалось залогировать удаление менеджера {manager_id}: {e}")

        return jsonify({'success': success})
    except NotFoundError as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except ValidationError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Ошибка при удалении менеджера {manager_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500



