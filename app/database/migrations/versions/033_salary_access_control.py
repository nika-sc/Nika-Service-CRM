"""
Миграция 033: Права доступа для модуля зарплаты и связь users с сотрудниками.

1. Добавляет поле user_id в таблицы masters и managers для связи с users
2. Добавляет право salary.view в систему permissions
3. Назначает права ролям (master, manager, admin)
"""
from app.database.connection import get_db_connection
import logging

logger = logging.getLogger(__name__)


def up():
    """Применяет миграцию."""
    logger.info("Применение миграции 033_salary_access_control")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Добавляем user_id в masters
        try:
            cursor.execute('''
                ALTER TABLE masters ADD COLUMN user_id INTEGER REFERENCES users(id)
            ''')
            logger.info("Добавлено поле user_id в таблицу masters")
        except Exception as e:
            # Поле уже существует
            if 'duplicate column' not in str(e).lower():
                logger.warning(f"Не удалось добавить user_id в masters: {e}")
        
        # 2. Добавляем user_id в managers
        try:
            cursor.execute('''
                ALTER TABLE managers ADD COLUMN user_id INTEGER REFERENCES users(id)
            ''')
            logger.info("Добавлено поле user_id в таблицу managers")
        except Exception as e:
            # Поле уже существует
            if 'duplicate column' not in str(e).lower():
                logger.warning(f"Не удалось добавить user_id в managers: {e}")
        
        # 3. Создаем индексы для быстрого поиска
        try:
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_masters_user_id ON masters(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_managers_user_id ON managers(user_id)')
            logger.info("Созданы индексы для user_id в masters и managers")
        except Exception as e:
            logger.warning(f"Не удалось создать индексы: {e}")
        
        # 4. Добавляем право salary.view в permissions
        cursor.execute('''
            INSERT OR IGNORE INTO permissions (name, description)
            VALUES ('salary.view', 'Просмотр модуля зарплаты')
        ''')
        logger.info("Добавлено право salary.view")
        
        # 5. Получаем ID права salary.view
        cursor.execute('SELECT id FROM permissions WHERE name = ?', ('salary.view',))
        salary_view_permission = cursor.fetchone()
        
        if salary_view_permission:
            permission_id = salary_view_permission[0]
            
            # 6. Назначаем права ролям
            roles_to_assign = ['master', 'manager', 'admin']
            for role in roles_to_assign:
                cursor.execute('''
                    INSERT OR IGNORE INTO role_permissions (role, permission_id)
                    VALUES (?, ?)
                ''', (role, permission_id))
                logger.info(f"Право salary.view назначено роли {role}")
        
        conn.commit()
        logger.info("Миграция 033_salary_access_control успешно применена")


def down():
    """Откатывает миграцию."""
    logger.warning("Откат миграции 033_salary_access_control")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Удаляем право salary.view из role_permissions
        cursor.execute('''
            DELETE FROM role_permissions 
            WHERE permission_id IN (SELECT id FROM permissions WHERE name = 'salary.view')
        ''')
        
        # Удаляем право salary.view из permissions
        cursor.execute("DELETE FROM permissions WHERE name = 'salary.view'")
        
        # Удаляем индексы
        try:
            cursor.execute('DROP INDEX IF EXISTS idx_masters_user_id')
            cursor.execute('DROP INDEX IF EXISTS idx_managers_user_id')
        except Exception as e:
            logger.warning(f"Не удалось удалить индексы: {e}")
        
        # Примечание: SQLite не поддерживает ALTER TABLE DROP COLUMN
        # Для удаления колонок нужна пересоздание таблицы
        # Поэтому в down() мы только удаляем индексы и права
        
        conn.commit()
        logger.info("Миграция 033_salary_access_control откачена")
