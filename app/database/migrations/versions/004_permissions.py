"""
Миграция 004: Система прав доступа.

Создает таблицы для системы прав (permissions) и связь ролей с правами.
"""
from app.database.connection import get_db_connection
import logging

logger = logging.getLogger(__name__)


def up():
    """Применяет миграцию."""
    logger.info("Применение миграции 004_permissions: создание системы прав")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Таблица permissions (права)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица role_permissions (связь ролей и прав)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS role_permissions (
                role TEXT NOT NULL,
                permission_id INTEGER NOT NULL,
                PRIMARY KEY (role, permission_id),
                FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE
            )
        ''')
        
        # Индексы
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_permissions_name ON permissions(name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_role_permissions_role ON role_permissions(role)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_role_permissions_permission ON role_permissions(permission_id)')
        
        # Начальные права
        permissions = [
            ('view_orders', 'Просмотр заявок'),
            ('create_orders', 'Создание заявок'),
            ('edit_orders', 'Редактирование заявок'),
            ('delete_orders', 'Удаление заявок'),
            ('view_customers', 'Просмотр клиентов'),
            ('create_customers', 'Создание клиентов'),
            ('edit_customers', 'Редактирование клиентов'),
            ('delete_customers', 'Удаление клиентов'),
            ('view_warehouse', 'Просмотр склада'),
            ('manage_warehouse', 'Управление складом'),
            ('view_reports', 'Просмотр отчетов'),
            ('manage_settings', 'Управление настройками'),
            ('manage_users', 'Управление пользователями')
        ]
        
        for perm_name, perm_desc in permissions:
            cursor.execute('''
                INSERT OR IGNORE INTO permissions (name, description)
                VALUES (?, ?)
            ''', (perm_name, perm_desc))
        
        # Получаем ID прав
        cursor.execute('SELECT id, name FROM permissions')
        perm_dict = {name: id for id, name in cursor.fetchall()}
        
        # Назначаем права ролям
        role_permissions = {
            'viewer': ['view_orders', 'view_customers'],
            'master': ['view_orders', 'create_orders', 'edit_orders', 'view_customers', 'view_warehouse'],
            'manager': ['view_orders', 'create_orders', 'edit_orders', 'view_customers', 'create_customers', 
                       'edit_customers', 'view_warehouse', 'manage_warehouse', 'view_reports'],
            'admin': list(perm_dict.keys())  # Все права
        }
        
        for role, perm_names in role_permissions.items():
            for perm_name in perm_names:
                if perm_name in perm_dict:
                    cursor.execute('''
                        INSERT OR IGNORE INTO role_permissions (role, permission_id)
                        VALUES (?, ?)
                    ''', (role, perm_dict[perm_name]))
        
        conn.commit()
        logger.info("Миграция 004_permissions успешно применена")


def down():
    """Откатывает миграцию."""
    logger.warning("Откат миграции 004_permissions: удаление таблиц прав")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        tables = ['role_permissions', 'permissions']
        
        for table in tables:
            try:
                cursor.execute(f'DROP TABLE IF EXISTS {table}')
                logger.info(f"Таблица {table} удалена")
            except Exception as e:
                logger.warning(f"Не удалось удалить таблицу {table}: {e}")
        
        conn.commit()
        logger.info("Миграция 004_permissions откачена")

