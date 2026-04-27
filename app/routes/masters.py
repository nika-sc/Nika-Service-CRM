"""
Роуты для управления мастерами (только API, без старых HTML-страниц).
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.routes.main import permission_required
from app.services.master_service import MasterService
from app.services.action_log_service import ActionLogService
from app.utils.exceptions import ValidationError, NotFoundError
import logging

logger = logging.getLogger(__name__)

# Только API blueprint. Старый страничный blueprint (masters_page) удалён как неиспользуемый.
bp = Blueprint('masters', __name__, url_prefix='/api/masters')


@bp.route('', methods=['GET'])
@login_required
@permission_required('manage_users')
def get_masters():
    """Получает список мастеров."""
    try:
        active_only = request.args.get('active_only', '1') == '1'
        masters = MasterService.get_all_masters(active_only=active_only)
        return jsonify({'success': True, 'masters': masters})
    except Exception as e:
        logger.error(f"Ошибка при получении мастеров: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/<int:master_id>', methods=['GET'])
@login_required
@permission_required('manage_users')
def get_master(master_id):
    """Получает мастера по ID."""
    try:
        master = MasterService.get_master_by_id(master_id)
        if not master:
            return jsonify({'success': False, 'error': 'Мастер не найден'}), 404
        return jsonify({'success': True, 'master': master})
    except Exception as e:
        logger.error(f"Ошибка при получении мастера {master_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('', methods=['POST'])
@login_required
@permission_required('manage_users')
def create_master():
    """Создает нового мастера и автоматически создает пользователя."""
    try:
        # Проверяем права на создание мастера
        from app.services.user_service import UserService
        user = UserService.get_user_by_id(current_user.id)
        if not user:
            return jsonify({'success': False, 'error': 'Пользователь не найден'}), 404
        
        user_role = user.get('role', '')
        # Admin может создавать мастеров, менеджеры тоже могут создавать мастеров
        if user_role != 'admin' and not user_role.startswith('manager_'):
            return jsonify({'success': False, 'error': 'Недостаточно прав для создания мастера. Только администратор или менеджер может создавать мастеров.'}), 403
        
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
        
        # Создаем мастера
        def _float_or_none(val):
            if val is None or val == '':
                return None
            try:
                return float(val)
            except (TypeError, ValueError):
                return None
        master_id = MasterService.create_master(
            name=name,
            salary_rule_type=data.get('salary_rule_type'),
            salary_rule_value=_float_or_none(data.get('salary_rule_value')),
            salary_percent_services=_float_or_none(data.get('salary_percent_services')),
            salary_percent_parts=_float_or_none(data.get('salary_percent_parts')),
            salary_percent_shop_parts=_float_or_none(data.get('salary_percent_shop_parts')),
            active=int(data.get('active', 1)),
            comment=data.get('comment')
        )
        
        # Получаем права по умолчанию для роли master
        from app.services.user_service import UserService
        permission_ids = UserService.get_default_permission_ids_for_role('master')
        
        logger.info(f"Создание мастера {master_id} с правами по умолчанию: {permission_ids}")
        
        # Создаем кастомную роль для этого мастера с правами по умолчанию
        custom_role_name = f'master_{master_id}'
        
        try:
            # Создаем кастомную роль с правами по умолчанию
            UserService.create_role(custom_role_name, permission_ids)
            logger.info(f"Создана кастомная роль {custom_role_name} с правами: {permission_ids}")
            
            # Создаем пользователя с логином (email) и стандартной ролью (чтобы обойти валидацию)
            user_id = UserService.create_user(username=login, password=password, role='master')
            
            # Обновляем роль на кастомную
            from app.database.connection import get_db_connection
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET role = ? WHERE id = ?", (custom_role_name, user_id))
                conn.commit()
            logger.info(f"Роль пользователя обновлена на: {custom_role_name}")
            
            # Связываем мастера с пользователем
            MasterService.update_master(master_id, user_id=user_id)
        except ValidationError as e:
            # Невалидные права / запрещенные права — откатываем создание мастера
            try:
                MasterService.delete_master(master_id)
            except Exception:
                pass
            try:
                UserService.delete_role(custom_role_name)
            except Exception:
                pass
            return jsonify({'success': False, 'error': str(e)}), 400
        except Exception as e:
            logger.warning(f"Не удалось создать пользователя для мастера {master_id}: {e}")
            # Удаляем мастера, если не удалось создать пользователя
            MasterService.delete_master(master_id)
            # Удаляем кастомную роль, если она была создана
            try:
                UserService.delete_role(custom_role_name)
            except Exception:
                pass
            return jsonify({'success': False, 'error': f'Не удалось создать пользователя: {str(e)}'}), 400

        # Логируем создание мастера
        try:
            ActionLogService.log_action(
                user_id=current_user.id if current_user.is_authenticated else None,
                username=current_user.username if current_user.is_authenticated else None,
                action_type='create',
                entity_type='master',
                entity_id=master_id,
                description=f'Создан мастер: {data.get("name", "Без имени")}',
                details={
                    'name': data.get('name'),
                    'salary_rule_type': data.get('salary_rule_type'),
                    'salary_rule_value': data.get('salary_rule_value'),
                    'active': data.get('active', 1)
                }
            )
        except Exception as e:
            logger.warning(f"Не удалось залогировать создание мастера {master_id}: {e}")

        return jsonify({'success': True, 'master_id': master_id}), 201
    except ValidationError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Ошибка при создании мастера: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/<int:master_id>', methods=['PATCH'])
@login_required
@permission_required('manage_users')
def update_master(master_id):
    """Обновляет мастера и связанного пользователя."""
    try:
        data = request.get_json() or {}
        name = data.get('name')
        
        master = MasterService.get_master_by_id(master_id)
        if not master:
            return jsonify({'success': False, 'error': 'Мастер не найден'}), 404
        
        # Если изменилось имя мастера, обновляем username связанного пользователя
        if name and master.get('user_id'):
            from app.services.user_service import UserService
            from app.database.connection import get_db_connection
            import sqlite3
            
            try:
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    # Обновляем username пользователя
                    cursor.execute(
                        'UPDATE users SET username = ? WHERE id = ?',
                        (name.strip(), master['user_id'])
                    )
                    conn.commit()
            except Exception as e:
                logger.warning(f"Не удалось обновить username для пользователя {master['user_id']}: {e}")
        
        # Обновляем права кастомной роли, если они указаны
        permission_ids = data.get('permission_ids')
        logger.info(f"Обновление мастера {master_id}: permission_ids = {permission_ids}, user_id = {master.get('user_id')}")
        
        # Всегда обновляем права, если есть user_id (даже если permission_ids = [])
        if 'permission_ids' in data and master.get('user_id'):
            from app.services.user_service import UserService
            from app.database.connection import get_db_connection
            
            # Нормализуем permission_ids
            if not isinstance(permission_ids, list):
                permission_ids = []
            
            logger.info(f"Обновление прав для мастера {master_id}: {permission_ids}")
            
            try:
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    # Получаем роль пользователя
                    cursor.execute('SELECT role FROM users WHERE id = ?', (master['user_id'],))
                    user_role = cursor.fetchone()
                    
                    if user_role:
                        current_role = user_role[0]
                        
                        # Если роль стандартная, создаем кастомную
                        if current_role == 'master':
                            custom_role_name = f'master_{master_id}'
                            UserService.create_role(custom_role_name, permission_ids)
                            # Обновляем роль пользователя
                            cursor.execute("UPDATE users SET role = ? WHERE id = ?", (custom_role_name, master['user_id']))
                            conn.commit()
                            logger.info(f"Создана кастомная роль {custom_role_name} и обновлена роль пользователя")
                        elif current_role.startswith('master_'):
                            # Обновляем права существующей кастомной роли
                            UserService.update_role(current_role, permission_ids)
                            logger.info(f"Обновлены права кастомной роли {current_role}")
            except ValidationError as e:
                return jsonify({'success': False, 'error': str(e)}), 400
            except Exception as e:
                logger.error(f"Не удалось обновить права для мастера {master_id}: {e}", exc_info=True)
        
        def _float_or_none(val):
            if val is None or val == '':
                return None
            try:
                return float(val)
            except (TypeError, ValueError):
                return None
        update_kw = dict(
            master_id=master_id,
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
        success = MasterService.update_master(**update_kw)

        if success:
            # Логируем обновление мастера
            try:
                ActionLogService.log_action(
                    user_id=current_user.id if current_user.is_authenticated else None,
                    username=current_user.username if current_user.is_authenticated else None,
                    action_type='update',
                    entity_type='master',
                    entity_id=master_id,
                    description=f'Обновлен мастер: {data.get("name", "Без имени")}',
                    details={
                        'name': data.get('name'),
                        'salary_rule_type': data.get('salary_rule_type'),
                        'salary_rule_value': data.get('salary_rule_value'),
                        'active': data.get('active'),
                        'comment': data.get('comment')
                    }
                )
            except Exception as e:
                logger.warning(f"Не удалось залогировать обновление мастера {master_id}: {e}")

        return jsonify({'success': success})
    except NotFoundError as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except ValidationError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Ошибка при обновлении мастера {master_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/<int:master_id>', methods=['DELETE'])
@login_required
@permission_required('manage_users')
def delete_master(master_id):
    """Удаляет мастера."""
    try:
        # Получаем данные мастера перед удалением для лога
        master_data = MasterService.get_master_by_id(master_id)
        master_name = master_data.get('name', 'Без имени') if master_data else 'Неизвестен'

        success = MasterService.delete_master(master_id)

        if success:
            # Логируем удаление мастера
            try:
                ActionLogService.log_action(
                    user_id=current_user.id if current_user.is_authenticated else None,
                    username=current_user.username if current_user.is_authenticated else None,
                    action_type='delete',
                    entity_type='master',
                    entity_id=master_id,
                    description=f'Удален мастер: {master_name}',
                    details={'name': master_name}
                )
            except Exception as e:
                logger.warning(f"Не удалось залогировать удаление мастера {master_id}: {e}")

        return jsonify({'success': success})
    except NotFoundError as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except ValidationError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Ошибка при удалении мастера {master_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500




