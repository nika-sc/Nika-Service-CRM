"""
Роуты для управления сотрудниками (объединенный endpoint для admin/manager/master).
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.routes.main import permission_required
from app.services.user_service import UserService
from app.services.master_service import MasterService
from app.services.manager_service import ManagerService
from app.services.action_log_service import ActionLogService
from app.utils.exceptions import ValidationError, NotFoundError
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('employees', __name__, url_prefix='/api/employees')


def get_default_permission_ids_for_role(role: str) -> list:
    """
    Получает ID прав по умолчанию для роли.
    
    Args:
        role: Роль (admin, manager, master)
        
    Returns:
        Список ID прав
    """
    # Получаем все роли с правами
    all_roles = UserService.get_all_roles()
    role_data = next((r for r in all_roles if r['role'] == role), None)
    
    if role_data:
        return [p['id'] for p in role_data['permissions']]
    return []


def can_create_role(current_user_role: str, target_role: str) -> bool:
    """
    Проверяет, может ли текущий пользователь создать пользователя с указанной ролью.
    
    Args:
        current_user_role: Роль текущего пользователя
        target_role: Роль, которую нужно создать
        
    Returns:
        True если может создать
    """
    # Главный admin может создавать всех
    if current_user_role == 'admin':
        return target_role in ['admin', 'manager', 'master']
    
    # Менеджер может создавать только мастеров
    if current_user_role == 'manager' or current_user_role.startswith('manager_'):
        return target_role == 'master'
    
    return False


@bp.route('', methods=['GET'])
@login_required
@permission_required('manage_users')
def get_employees():
    """
    Получает список всех сотрудников (admin/manager/master) с фильтрацией по роли.
    
    Query params:
        role: Фильтр по роли (admin, manager, master, all)
        active_only: Только активные (1/0)
    """
    try:
        role_filter = request.args.get('role', 'all')
        active_only = request.args.get('active_only', '1') == '1'
        
        result = {
            'admins': [],
            'managers': [],
            'masters': []
        }
        
        # Получаем администраторов
        if role_filter in ['all', 'admin']:
            users = UserService.get_all_users(include_inactive=not active_only, role='admin')
            result['admins'] = [
                {
                    'id': u['id'],
                    'type': 'admin',
                    'name': u.get('display_name') or u.get('username', ''),
                    'login': u['username'],
                    'role': u['role'],
                    'is_active': u.get('is_active', 1),
                    'last_login': u.get('last_login'),
                    'user_id': u['id']
                }
                for u in users
            ]
        
        # Получаем менеджеров
        if role_filter in ['all', 'manager']:
            managers = ManagerService.get_all_managers(active_only=active_only)
            result['managers'] = [
                {
                    'id': m['id'],
                    'type': 'manager',
                    'name': m['name'],
                    'login': None,  # Получим из users
                    'role': 'manager',
                    'is_active': m.get('active', 1) != 0,
                    'user_id': m.get('user_id'),
                    'salary_rule_type': m.get('salary_rule_type'),
                    'salary_rule_value': m.get('salary_rule_value'),
                    'salary_rule_base': m.get('salary_rule_base') or 'profit',
                    'salary_percent_services': m.get('salary_percent_services'),
                    'salary_percent_parts': m.get('salary_percent_parts'),
                    'salary_percent_shop_parts': m.get('salary_percent_shop_parts'),
                    'comment': m.get('comment')
                }
                for m in managers
            ]
            
            # Заполняем login и name из users
            for manager in result['managers']:
                if manager['user_id']:
                    user = UserService.get_user_by_id(manager['user_id'], include_inactive=True)
                    if user:
                        manager['login'] = user['username']
                        # Если есть display_name в users, используем его
                        if user.get('display_name'):
                            manager['name'] = user['display_name']
        
        # Получаем мастеров
        if role_filter in ['all', 'master']:
            masters = MasterService.get_all_masters(active_only=active_only)
            result['masters'] = [
                {
                    'id': m['id'],
                    'type': 'master',
                    'name': m['name'],
                    'login': None,  # Получим из users
                    'role': 'master',
                    'is_active': m.get('active', 1) != 0,
                    'user_id': m.get('user_id'),
                    'salary_rule_type': m.get('salary_rule_type'),
                    'salary_rule_value': m.get('salary_rule_value'),
                    'salary_percent_services': m.get('salary_percent_services'),
                    'salary_percent_parts': m.get('salary_percent_parts'),
                    'salary_percent_shop_parts': m.get('salary_percent_shop_parts'),
                    'comment': m.get('comment')
                }
                for m in masters
            ]
            
            # Заполняем login и name из users
            for master in result['masters']:
                if master['user_id']:
                    user = UserService.get_user_by_id(master['user_id'], include_inactive=True)
                    if user:
                        master['login'] = user['username']
                        # Если есть display_name в users, используем его
                        if user.get('display_name'):
                            master['name'] = user['display_name']
        
        return jsonify({'success': True, 'employees': result})
    except Exception as e:
        logger.error(f"Ошибка при получении сотрудников: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('', methods=['POST'])
@login_required
@permission_required('manage_users')
def create_employee():
    """
    Создает нового сотрудника (admin/manager/master).
    
    Body:
        full_name: ФИО (видимое имя)
        login: Логин (email для входа)
        password: Пароль
        role: Роль (admin, manager, master)
        salary_rule_type: Тип правила зарплаты (для manager/master)
        salary_rule_value: Значение правила зарплаты (для manager/master)
        active: Активен (1/0)
        comment: Комментарий (для manager/master)
    """
    try:
        data = request.get_json() or {}
        full_name = data.get('full_name', '').strip()
        login = data.get('login', '').strip()
        password = data.get('password', '')
        role = data.get('role', '').strip().lower()
        
        # Валидация
        if not full_name:
            return jsonify({'success': False, 'error': 'ФИО обязательно'}), 400
        
        if not login:
            return jsonify({'success': False, 'error': 'Логин (email) обязателен'}), 400
        
        if not password:
            return jsonify({'success': False, 'error': 'Пароль обязателен'}), 400
        
        if role not in ['admin', 'manager', 'master']:
            msg = 'Выберите роль (Администратор, Менеджер или Мастер)' if not role else 'Неверная роль'
            return jsonify({'success': False, 'error': msg}), 400
        
        # Проверка прав на создание
        current_user_role = getattr(current_user, 'role', 'viewer')
        if not can_create_role(current_user_role, role):
            return jsonify({
                'success': False, 
                'error': f'У вас нет прав для создания пользователя с ролью {role}'
            }), 403
        
        # Получаем права по умолчанию для роли
        default_permission_ids = get_default_permission_ids_for_role(role)
        
        # Валидация email для логина
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, login):
            return jsonify({'success': False, 'error': 'Логин должен быть валидным email адресом'}), 400
        
        # Создаем пользователя
        if role == 'admin':
            # Для админа создаем пользователя с display_name
            user_id = UserService.create_user(
                username=login, 
                password=password, 
                role='admin',
                display_name=full_name
            )
            
            ActionLogService.log_action(
                user_id=current_user.id if current_user.is_authenticated else None,
                username=current_user.username if current_user.is_authenticated else None,
                action_type='create',
                entity_type='user',
                entity_id=user_id,
                description=f'Создан администратор: {full_name}',
                details={'full_name': full_name, 'login': login, 'role': role}
            )
            
            return jsonify({'success': True, 'user_id': user_id, 'type': 'admin'}), 201
        
        elif role == 'manager':
            # Создаем менеджера
            manager_id = ManagerService.create_manager(
                name=full_name,
                salary_rule_type=data.get('salary_rule_type'),
                salary_rule_value=float(data['salary_rule_value']) if data.get('salary_rule_value') is not None else None,
                salary_percent_services=float(data['salary_percent_services']) if data.get('salary_percent_services') not in (None, '') else None,
                salary_percent_parts=float(data['salary_percent_parts']) if data.get('salary_percent_parts') not in (None, '') else None,
                salary_percent_shop_parts=float(data['salary_percent_shop_parts']) if data.get('salary_percent_shop_parts') not in (None, '') else None,
                active=int(data.get('active', 1)),
                comment=data.get('comment')
            )
            
            # Создаем кастомную роль
            custom_role_name = f'manager_{manager_id}'
            UserService.create_role(custom_role_name, default_permission_ids)
            
            # Создаем пользователя с display_name
            user_id = UserService.create_user(
                username=login, 
                password=password, 
                role='manager',
                display_name=full_name
            )
            
            # Обновляем роль на кастомную
            from app.database.connection import get_db_connection
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET role = ? WHERE id = ?", (custom_role_name, user_id))
                conn.commit()
            
            # Связываем менеджера с пользователем
            ManagerService.update_manager(manager_id, user_id=user_id)
            
            ActionLogService.log_action(
                user_id=current_user.id if current_user.is_authenticated else None,
                username=current_user.username if current_user.is_authenticated else None,
                action_type='create',
                entity_type='manager',
                entity_id=manager_id,
                description=f'Создан менеджер: {full_name}',
                details={'full_name': full_name, 'login': login, 'role': role}
            )
            
            return jsonify({'success': True, 'manager_id': manager_id, 'type': 'manager'}), 201
        
        elif role == 'master':
            # Создаем мастера
            master_id = MasterService.create_master(
                name=full_name,
                salary_rule_type=data.get('salary_rule_type'),
                salary_rule_value=float(data['salary_rule_value']) if data.get('salary_rule_value') is not None else None,
                salary_percent_services=float(data['salary_percent_services']) if data.get('salary_percent_services') not in (None, '') else None,
                salary_percent_parts=float(data['salary_percent_parts']) if data.get('salary_percent_parts') not in (None, '') else None,
                salary_percent_shop_parts=float(data['salary_percent_shop_parts']) if data.get('salary_percent_shop_parts') not in (None, '') else None,
                active=int(data.get('active', 1)),
                comment=data.get('comment')
            )
            
            # Создаем кастомную роль
            custom_role_name = f'master_{master_id}'
            UserService.create_role(custom_role_name, default_permission_ids)
            
            # Создаем пользователя с display_name
            user_id = UserService.create_user(
                username=login, 
                password=password, 
                role='master',
                display_name=full_name
            )
            
            # Обновляем роль на кастомную
            from app.database.connection import get_db_connection
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET role = ? WHERE id = ?", (custom_role_name, user_id))
                conn.commit()
            
            # Связываем мастера с пользователем
            MasterService.update_master(master_id, user_id=user_id)
            
            ActionLogService.log_action(
                user_id=current_user.id if current_user.is_authenticated else None,
                username=current_user.username if current_user.is_authenticated else None,
                action_type='create',
                entity_type='master',
                entity_id=master_id,
                description=f'Создан мастер: {full_name}',
                details={'full_name': full_name, 'login': login, 'role': role}
            )
            
            return jsonify({'success': True, 'master_id': master_id, 'type': 'master'}), 201
        
    except ValidationError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Ошибка при создании сотрудника: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/<int:employee_id>', methods=['PATCH'])
@login_required
@permission_required('manage_users')
def update_employee(employee_id):
    """
    Обновляет данные сотрудника.
    
    Body:
        full_name: ФИО (опционально)
        login: Логин/email (опционально)
        password: Новый пароль (опционально)
        role: Роль (опционально, только для админов)
        is_active: Активен (1/0) (опционально)
        salary_rule_type: Тип правила зарплаты (для manager/master, опционально)
        salary_rule_value: Значение правила зарплаты (для manager/master, опционально)
        comment: Комментарий (для manager/master, опционально)
    """
    try:
        data = request.get_json() or {}
        employee_type = data.get('type')  # admin, manager, master
        
        if not employee_type:
            return jsonify({'success': False, 'error': 'Не указан тип сотрудника'}), 400
        
        if employee_type == 'admin':
            # Обновление администратора
            user = UserService.get_user_by_id(employee_id, include_inactive=True)
            if not user:
                return jsonify({'success': False, 'error': 'Пользователь не найден'}), 404
            
            updates = {}
            if 'full_name' in data:
                updates['display_name'] = data['full_name'].strip()
            if 'login' in data:
                # Валидация email
                import re
                email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                if not re.match(email_pattern, data['login']):
                    return jsonify({'success': False, 'error': 'Логин должен быть валидным email адресом'}), 400
                updates['username'] = data['login'].strip()
            if 'password' in data and data['password']:
                UserService.change_password(employee_id, data['password'])
            if 'is_active' in data or 'active' in data:
                updates['is_active'] = int(data.get('is_active', data.get('active', 1)))
            
            if updates:
                UserService.update_user(employee_id, **updates)
            
            ActionLogService.log_action(
                user_id=current_user.id if current_user.is_authenticated else None,
                username=current_user.username if current_user.is_authenticated else None,
                action_type='update',
                entity_type='user',
                entity_id=employee_id,
                description=f'Обновлен администратор',
                details=updates
            )
            
            return jsonify({'success': True})
        
        elif employee_type == 'manager':
            manager = ManagerService.get_manager_by_id(employee_id)
            if not manager:
                return jsonify({'success': False, 'error': 'Менеджер не найден'}), 404
            
            # Обновляем данные менеджера
            manager_updates = {}
            if 'full_name' in data:
                manager_updates['name'] = data['full_name'].strip()
            if 'salary_rule_type' in data:
                manager_updates['salary_rule_type'] = data['salary_rule_type']
            if 'salary_rule_value' in data:
                manager_updates['salary_rule_value'] = data['salary_rule_value']
            if 'salary_rule_base' in data and str(data.get('salary_rule_base')).strip().lower() in ('profit', 'revenue', ''):
                manager_updates['salary_rule_base'] = (data['salary_rule_base'] or 'profit').strip().lower() or 'profit'
            if 'salary_percent_services' in data:
                manager_updates['salary_percent_services'] = float(data['salary_percent_services']) if data.get('salary_percent_services') not in (None, '') else None
            if 'salary_percent_parts' in data:
                manager_updates['salary_percent_parts'] = float(data['salary_percent_parts']) if data.get('salary_percent_parts') not in (None, '') else None
            if 'salary_percent_shop_parts' in data:
                manager_updates['salary_percent_shop_parts'] = float(data['salary_percent_shop_parts']) if data.get('salary_percent_shop_parts') not in (None, '') else None
            if 'comment' in data:
                manager_updates['comment'] = data['comment']
            if 'is_active' in data or 'active' in data:
                manager_updates['active'] = int(data.get('is_active', data.get('active', 1)))
            
            if manager_updates:
                ManagerService.update_manager(employee_id, **manager_updates)
            
            # Обновляем или создаём пользователя для входа (логин всегда сохраняем при указании)
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            login_val = (data.get('login') or '').strip()
            if login_val and not re.match(email_pattern, login_val):
                return jsonify({'success': False, 'error': 'Логин должен быть валидным email адресом'}), 400
            
            if manager.get('user_id'):
                user_updates = {}
                if 'full_name' in data:
                    user_updates['display_name'] = data['full_name'].strip()
                if login_val:
                    user_updates['username'] = login_val
                if 'password' in data and data['password']:
                    UserService.change_password(manager['user_id'], data['password'])
                if 'is_active' in data or 'active' in data:
                    user_updates['is_active'] = int(data.get('is_active', data.get('active', 1)))
                if user_updates:
                    UserService.update_user(manager['user_id'], **user_updates)
            elif login_val:
                # Менеджер без учётки — создаём пользователя и привязываем
                password = (data.get('password') or '').strip()
                if not password:
                    return jsonify({'success': False, 'error': 'Укажите пароль для создания входа'}), 400
                user_id = UserService.create_user(
                    username=login_val,
                    password=password,
                    role='manager',
                    display_name=data.get('full_name', '').strip() or manager.get('name', '')
                )
                from app.database.connection import get_db_connection
                with get_db_connection() as conn:
                    cur = conn.cursor()
                    cur.execute("UPDATE users SET role = ? WHERE id = ?", (f'manager_{employee_id}', user_id))
                    conn.commit()
                ManagerService.update_manager(employee_id, user_id=user_id)
            
            return jsonify({'success': True})
        
        elif employee_type == 'master':
            master = MasterService.get_master_by_id(employee_id)
            if not master:
                return jsonify({'success': False, 'error': 'Мастер не найден'}), 404
            
            # Обновляем данные мастера
            master_updates = {}
            if 'full_name' in data:
                master_updates['name'] = data['full_name'].strip()
            if 'salary_rule_type' in data:
                master_updates['salary_rule_type'] = data['salary_rule_type']
            if 'salary_rule_value' in data:
                master_updates['salary_rule_value'] = data['salary_rule_value']
            if 'salary_percent_services' in data:
                master_updates['salary_percent_services'] = float(data['salary_percent_services']) if data.get('salary_percent_services') not in (None, '') else None
            if 'salary_percent_parts' in data:
                master_updates['salary_percent_parts'] = float(data['salary_percent_parts']) if data.get('salary_percent_parts') not in (None, '') else None
            if 'salary_percent_shop_parts' in data:
                master_updates['salary_percent_shop_parts'] = float(data['salary_percent_shop_parts']) if data.get('salary_percent_shop_parts') not in (None, '') else None
            if 'comment' in data:
                master_updates['comment'] = data['comment']
            if 'is_active' in data or 'active' in data:
                master_updates['active'] = int(data.get('is_active', data.get('active', 1)))
            
            if master_updates:
                MasterService.update_master(employee_id, **master_updates)
            
            # Обновляем или создаём пользователя для входа (логин всегда сохраняем при указании)
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            login_val = (data.get('login') or '').strip()
            if login_val and not re.match(email_pattern, login_val):
                return jsonify({'success': False, 'error': 'Логин должен быть валидным email адресом'}), 400
            
            if master.get('user_id'):
                user_updates = {}
                if 'full_name' in data:
                    user_updates['display_name'] = data['full_name'].strip()
                if login_val:
                    user_updates['username'] = login_val
                if 'password' in data and data['password']:
                    UserService.change_password(master['user_id'], data['password'])
                if 'is_active' in data or 'active' in data:
                    user_updates['is_active'] = int(data.get('is_active', data.get('active', 1)))
                if user_updates:
                    UserService.update_user(master['user_id'], **user_updates)
            elif login_val:
                # Мастер без учётки — создаём пользователя и привязываем
                password = (data.get('password') or '').strip()
                if not password:
                    return jsonify({'success': False, 'error': 'Укажите пароль для создания входа'}), 400
                user_id = UserService.create_user(
                    username=login_val,
                    password=password,
                    role='master',
                    display_name=data.get('full_name', '').strip() or master.get('name', '')
                )
                from app.database.connection import get_db_connection
                with get_db_connection() as conn:
                    cur = conn.cursor()
                    cur.execute("UPDATE users SET role = ? WHERE id = ?", (f'master_{employee_id}', user_id))
                    conn.commit()
                MasterService.update_master(employee_id, user_id=user_id)
            
            return jsonify({'success': True})
        
        else:
            return jsonify({'success': False, 'error': 'Неверный тип сотрудника'}), 400
            
    except ValidationError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except NotFoundError as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Ошибка при обновлении сотрудника {employee_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/<int:employee_id>', methods=['DELETE'])
@login_required
@permission_required('manage_users')
def deactivate_employee(employee_id):
    """
    Деактивирует сотрудника (помечает как неактивного).
    
    Query params:
        type: Тип сотрудника (admin, manager, master)
    """
    try:
        employee_type = request.args.get('type')
        if not employee_type:
            return jsonify({'success': False, 'error': 'Не указан тип сотрудника'}), 400
        
        if employee_type == 'admin':
            # Деактивируем администратора
            user = UserService.get_user_by_id(employee_id, include_inactive=True)
            if not user:
                return jsonify({'success': False, 'error': 'Пользователь не найден'}), 404
            
            # Проверяем, что это не последний активный администратор
            from app.database.connection import get_db_connection
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM users WHERE role = ? AND is_active = 1', ('admin',))
                admin_count = cursor.fetchone()[0]
                if admin_count <= 1 and user.get('is_active', 1) == 1:
                    return jsonify({'success': False, 'error': 'Нельзя деактивировать последнего администратора'}), 400
            
            UserService.update_user(employee_id, is_active=0)
            
            ActionLogService.log_action(
                user_id=current_user.id if current_user.is_authenticated else None,
                username=current_user.username if current_user.is_authenticated else None,
                action_type='delete',
                entity_type='user',
                entity_id=employee_id,
                description=f'Деактивирован администратор'
            )
            
            return jsonify({'success': True})
        
        elif employee_type == 'manager':
            manager = ManagerService.get_manager_by_id(employee_id)
            if not manager:
                return jsonify({'success': False, 'error': 'Менеджер не найден'}), 404
            
            ManagerService.update_manager(employee_id, active=0)
            
            # Деактивируем связанного пользователя
            if manager.get('user_id'):
                UserService.update_user(manager['user_id'], is_active=0)
            
            return jsonify({'success': True})
        
        elif employee_type == 'master':
            master = MasterService.get_master_by_id(employee_id)
            if not master:
                return jsonify({'success': False, 'error': 'Мастер не найден'}), 404
            
            MasterService.update_master(employee_id, active=0)
            
            # Деактивируем связанного пользователя
            if master.get('user_id'):
                UserService.update_user(master['user_id'], is_active=0)
            
            return jsonify({'success': True})
        
        else:
            return jsonify({'success': False, 'error': 'Неверный тип сотрудника'}), 400
            
    except ValidationError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except NotFoundError as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Ошибка при деактивации сотрудника {employee_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
