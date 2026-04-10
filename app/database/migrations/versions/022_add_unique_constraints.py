"""
Миграция 022: Добавление UNIQUE ограничений для предотвращения дубликатов.

Добавляет UNIQUE индексы на поля, которые должны быть уникальными:
- services.name - название услуги
- transaction_categories.name + type - название категории транзакций с учетом типа
- part_categories.name + parent_id - название категории товаров с учетом родителя (уже есть в CREATE TABLE, но проверим)
"""
from app.database.connection import get_db_connection
import logging
import sqlite3

logger = logging.getLogger(__name__)


def up():
    """Применяет миграцию."""
    logger.info("Применение миграции 022_add_unique_constraints: добавление UNIQUE ограничений")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 1. UNIQUE индекс для services.name
        logger.info("Создание UNIQUE индекса для services.name...")
        try:
            # Проверяем наличие дубликатов перед созданием индекса
            cursor.execute('''
                SELECT name, COUNT(*) as count
                FROM services
                GROUP BY name
                HAVING COUNT(*) > 1
            ''')
            duplicates = cursor.fetchall()
            
            if duplicates:
                logger.warning(f"Найдено {len(duplicates)} дубликатов услуг. Оставляем первую запись из каждой группы.")
                for dup in duplicates:
                    name = dup[0]
                    cursor.execute('SELECT id FROM services WHERE name = ? ORDER BY id LIMIT 1', (name,))
                    keep_id = cursor.fetchone()[0]
                    cursor.execute('DELETE FROM services WHERE name = ? AND id != ?', (name, keep_id))
                    logger.info(f"Удалены дубликаты услуги '{name}', оставлен ID {keep_id}")
            
            cursor.execute('''
                CREATE UNIQUE INDEX IF NOT EXISTS ux_services_name 
                ON services(name)
            ''')
            logger.info("UNIQUE индекс для services.name создан")
        except sqlite3.OperationalError as e:
            logger.error(f"Не удалось создать UNIQUE индекс для services.name: {e}")
        
        # 2. UNIQUE индекс для transaction_categories (name, type)
        logger.info("Создание UNIQUE индекса для transaction_categories (name, type)...")
        try:
            # Проверяем наличие дубликатов
            cursor.execute('''
                SELECT name, type, COUNT(*) as count
                FROM transaction_categories
                GROUP BY name, type
                HAVING COUNT(*) > 1
            ''')
            duplicates = cursor.fetchall()
            
            if duplicates:
                logger.warning(f"Найдено {len(duplicates)} дубликатов категорий транзакций. Оставляем первую запись из каждой группы.")
                for dup in duplicates:
                    name, cat_type = dup[0], dup[1]
                    cursor.execute('''
                        SELECT id FROM transaction_categories 
                        WHERE name = ? AND type = ? 
                        ORDER BY id LIMIT 1
                    ''', (name, cat_type))
                    keep_id = cursor.fetchone()[0]
                    cursor.execute('''
                        DELETE FROM transaction_categories 
                        WHERE name = ? AND type = ? AND id != ?
                    ''', (name, cat_type, keep_id))
                    logger.info(f"Удалены дубликаты категории '{name}' (тип: {cat_type}), оставлен ID {keep_id}")
            
            cursor.execute('''
                CREATE UNIQUE INDEX IF NOT EXISTS ux_transaction_categories_name_type 
                ON transaction_categories(name, type)
            ''')
            logger.info("UNIQUE индекс для transaction_categories (name, type) создан")
        except sqlite3.OperationalError as e:
            logger.error(f"Не удалось создать UNIQUE индекс для transaction_categories: {e}")
        
        # 3. Проверяем part_categories - должно быть UNIQUE (name, parent_id)
        logger.info("Проверка UNIQUE ограничения для part_categories (name, parent_id)...")
        try:
            # Проверяем наличие дубликатов
            cursor.execute('''
                SELECT name, parent_id, COUNT(*) as count
                FROM part_categories
                GROUP BY name, parent_id
                HAVING COUNT(*) > 1
            ''')
            duplicates = cursor.fetchall()
            
            if duplicates:
                logger.warning(f"Найдено {len(duplicates)} дубликатов категорий товаров. Оставляем первую запись из каждой группы.")
                for dup in duplicates:
                    name, parent_id = dup[0], dup[1]
                    cursor.execute('''
                        SELECT id FROM part_categories 
                        WHERE name = ? AND (parent_id = ? OR (parent_id IS NULL AND ? IS NULL))
                        ORDER BY id LIMIT 1
                    ''', (name, parent_id, parent_id))
                    keep_id = cursor.fetchone()[0]
                    cursor.execute('''
                        DELETE FROM part_categories 
                        WHERE name = ? AND (parent_id = ? OR (parent_id IS NULL AND ? IS NULL)) AND id != ?
                    ''', (name, parent_id, parent_id, keep_id))
                    logger.info(f"Удалены дубликаты категории '{name}' (parent_id: {parent_id}), оставлен ID {keep_id}")
            
            # Проверяем, есть ли уже UNIQUE индекс
            cursor.execute('''
                SELECT name FROM sqlite_master 
                WHERE type='index' AND tbl_name='part_categories' 
                AND name LIKE '%unique%' OR name LIKE '%name%parent%'
            ''')
            existing_index = cursor.fetchone()
            
            if not existing_index:
                # Создаем UNIQUE индекс
                cursor.execute('''
                    CREATE UNIQUE INDEX IF NOT EXISTS ux_part_categories_name_parent 
                    ON part_categories(name, COALESCE(parent_id, 0))
                ''')
                logger.info("UNIQUE индекс для part_categories (name, parent_id) создан")
            else:
                logger.info("UNIQUE индекс для part_categories уже существует")
        except sqlite3.OperationalError as e:
            logger.error(f"Не удалось создать/проверить UNIQUE индекс для part_categories: {e}")
        
        conn.commit()
        logger.info("Миграция 022_add_unique_constraints успешно применена")


def down():
    """Откатывает миграцию."""
    logger.warning("Откат миграции 022_add_unique_constraints: удаление UNIQUE индексов")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        try:
            cursor.execute('DROP INDEX IF EXISTS ux_services_name')
            logger.info("UNIQUE индекс ux_services_name удален")
        except Exception as e:
            logger.warning(f"Не удалось удалить индекс ux_services_name: {e}")
        
        try:
            cursor.execute('DROP INDEX IF EXISTS ux_transaction_categories_name_type')
            logger.info("UNIQUE индекс ux_transaction_categories_name_type удален")
        except Exception as e:
            logger.warning(f"Не удалось удалить индекс ux_transaction_categories_name_type: {e}")
        
        try:
            cursor.execute('DROP INDEX IF EXISTS ux_part_categories_name_parent')
            logger.info("UNIQUE индекс ux_part_categories_name_parent удален")
        except Exception as e:
            logger.warning(f"Не удалось удалить индекс ux_part_categories_name_parent: {e}")
        
        conn.commit()
        logger.info("Миграция 022_add_unique_constraints откачена")

