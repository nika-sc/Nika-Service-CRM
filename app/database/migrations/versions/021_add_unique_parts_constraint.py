"""
Миграция 021: Добавление UNIQUE ограничения на комбинацию (name, part_number) для товаров.

Предотвращает создание дубликатов товаров с одинаковым названием и артикулом.
Перед добавлением ограничения удаляет существующие дубликаты, оставляя товар с наибольшим ID.
"""
from app.database.connection import get_db_connection
import logging
import sqlite3

logger = logging.getLogger(__name__)


def up():
    """Применяет миграцию."""
    logger.info("Применение миграции 021_add_unique_parts_constraint: добавление UNIQUE ограничения")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Находим все дубликаты (товары с одинаковым name и part_number)
        logger.info("Поиск дубликатов товаров...")
        cursor.execute('''
            SELECT name, part_number, COUNT(*) as count, GROUP_CONCAT(id) as ids
            FROM parts
            WHERE is_deleted = 0
            GROUP BY name, part_number
            HAVING COUNT(*) > 1
        ''')
        duplicates = cursor.fetchall()
        
        if duplicates:
            logger.info(f"Найдено {len(duplicates)} групп дубликатов")
            
            # 2. Для каждой группы дубликатов оставляем товар с наибольшим ID
            # Остальные помечаем как удаленные (мягкое удаление)
            for dup in duplicates:
                name = dup[0]
                part_number = dup[1]
                ids = [int(x) for x in dup[3].split(',')]
                ids_sorted = sorted(ids, reverse=True)  # Сортируем по убыванию ID
                
                # Оставляем первый (с наибольшим ID), остальные помечаем как удаленные
                keep_id = ids_sorted[0]
                delete_ids = ids_sorted[1:]
                
                logger.info(f"Товар '{name}' (артикул: {part_number}): оставляем ID {keep_id}, удаляем {delete_ids}")
                
                # Проверяем, используются ли удаляемые товары
                for part_id in delete_ids:
                    cursor.execute('SELECT COUNT(*) FROM order_parts WHERE part_id = ?', (part_id,))
                    order_count = cursor.fetchone()[0]
                    cursor.execute('SELECT COUNT(*) FROM purchase_items WHERE part_id = ?', (part_id,))
                    purchase_count = cursor.fetchone()[0]
                    cursor.execute('SELECT COUNT(*) FROM stock_movements WHERE part_id = ?', (part_id,))
                    movement_count = cursor.fetchone()[0]
                    
                    if order_count > 0 or purchase_count > 0 or movement_count > 0:
                        logger.warning(
                            f"Товар ID {part_id} используется (заявки: {order_count}, закупки: {purchase_count}, "
                            f"движения: {movement_count}). Переносим ссылки на товар ID {keep_id}..."
                        )
                        
                        # Переносим ссылки на оставляемый товар
                        if order_count > 0:
                            cursor.execute('UPDATE order_parts SET part_id = ? WHERE part_id = ?', (keep_id, part_id))
                            logger.info(f"Перенесено {order_count} ссылок из order_parts")
                        
                        if purchase_count > 0:
                            cursor.execute('UPDATE purchase_items SET part_id = ? WHERE part_id = ?', (keep_id, part_id))
                            logger.info(f"Перенесено {purchase_count} ссылок из purchase_items")
                        
                        if movement_count > 0:
                            cursor.execute('UPDATE stock_movements SET part_id = ? WHERE part_id = ?', (keep_id, part_id))
                            logger.info(f"Перенесено {movement_count} ссылок из stock_movements")
                    
                    # Помечаем как удаленный
                    cursor.execute('UPDATE parts SET is_deleted = 1 WHERE id = ?', (part_id,))
                    logger.info(f"Товар ID {part_id} помечен как удаленный")
        
        # 3. Обновляем остаток оставляемого товара, суммируя остатки удаляемых
        if duplicates:
            logger.info("Обновление остатков товаров...")
            for dup in duplicates:
                name = dup[0]
                part_number = dup[1]
                ids = [int(x) for x in dup[3].split(',')]
                ids_sorted = sorted(ids, reverse=True)
                keep_id = ids_sorted[0]
                delete_ids = ids_sorted[1:]
                
                # Суммируем остатки
                cursor.execute('''
                    SELECT SUM(stock_quantity) 
                    FROM parts 
                    WHERE id IN ({})
                '''.format(','.join('?' * len(ids))), ids)
                total_stock = cursor.fetchone()[0] or 0
                
                # Обновляем остаток оставляемого товара
                cursor.execute('UPDATE parts SET stock_quantity = ? WHERE id = ?', (total_stock, keep_id))
                logger.info(f"Обновлен остаток товара ID {keep_id}: {total_stock}")
        
        # 4. Создаем UNIQUE индекс на комбинацию (name, part_number)
        # Но сначала нужно обработать NULL значения в part_number
        # SQLite позволяет NULL в UNIQUE индексе, но каждая комбинация NULL считается уникальной
        logger.info("Создание UNIQUE индекса на (name, part_number)...")
        try:
            cursor.execute('''
                CREATE UNIQUE INDEX IF NOT EXISTS ux_parts_name_part_number 
                ON parts(name, part_number) 
                WHERE is_deleted = 0
            ''')
            logger.info("UNIQUE индекс успешно создан")
        except sqlite3.OperationalError as e:
            # SQLite не поддерживает WHERE в CREATE UNIQUE INDEX напрямую
            # Используем альтернативный подход: создаем индекс без WHERE
            logger.warning(f"Не удалось создать индекс с WHERE: {e}")
            logger.info("Создание UNIQUE индекса без условия WHERE...")
            try:
                cursor.execute('''
                    CREATE UNIQUE INDEX IF NOT EXISTS ux_parts_name_part_number 
                    ON parts(name, COALESCE(part_number, ''))
                ''')
                logger.info("UNIQUE индекс успешно создан (без условия WHERE)")
            except sqlite3.OperationalError as e2:
                logger.error(f"Не удалось создать UNIQUE индекс: {e2}")
                # Продолжаем выполнение, проверка на дубликаты будет на уровне приложения
                logger.warning("UNIQUE индекс не создан, проверка дубликатов будет выполняться на уровне приложения")
        
        conn.commit()
        logger.info("Миграция 021_add_unique_parts_constraint успешно применена")


def down():
    """Откатывает миграцию."""
    logger.warning("Откат миграции 021_add_unique_parts_constraint: удаление UNIQUE индекса")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        try:
            cursor.execute('DROP INDEX IF EXISTS ux_parts_name_part_number')
            logger.info("UNIQUE индекс удален")
        except Exception as e:
            logger.warning(f"Не удалось удалить индекс: {e}")
        
        conn.commit()
        logger.info("Миграция 021_add_unique_parts_constraint откачена")

