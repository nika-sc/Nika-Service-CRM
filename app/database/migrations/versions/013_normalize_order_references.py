"""
Миграция 013: Нормализация справочников в заявках.

Изменения:
1. Добавляет model_id в orders (FK к order_models)
2. Мигрирует данные из model (TEXT) в model_id
3. Создает таблицу order_symptoms (many-to-many)
4. Мигрирует данные из symptom_tags (TEXT) в order_symptoms
5. Создает таблицу order_appearance_tags (many-to-many)
6. Мигрирует данные из appearance (TEXT) в order_appearance_tags

Старые колонки (model, symptom_tags, appearance) остаются для обратной совместимости.
"""
from app.database.connection import get_db_connection
import logging
import sqlite3
import re

logger = logging.getLogger(__name__)


def normalize_tag_name(tag_name: str) -> str:
    """Нормализует название тега (убирает пробелы, приводит к нужному формату)."""
    if not tag_name:
        return ''
    # Убираем лишние пробелы, первая буква заглавная
    normalized = ' '.join(tag_name.strip().split())
    if normalized:
        normalized = normalized[0].upper() + normalized[1:] if len(normalized) > 1 else normalized.upper()
    return normalized


def up():
    """Применяет миграцию."""
    logger.info("Применение миграции 013_normalize_order_references: нормализация справочников")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Добавляем колонку model_id в orders
        try:
            cursor.execute("PRAGMA table_info(orders)")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'model_id' not in columns:
                cursor.execute('''
                    ALTER TABLE orders 
                    ADD COLUMN model_id INTEGER
                ''')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_model_id ON orders(model_id)')
                logger.info("Добавлена колонка model_id в таблицу orders")
            else:
                logger.info("Колонка model_id уже существует")
        except sqlite3.OperationalError as e:
            logger.warning(f"Ошибка при добавлении model_id: {e}")
        
        # 2. Мигрируем данные из model (TEXT) в model_id
        try:
            cursor.execute('''
                SELECT DISTINCT id, model 
                FROM orders 
                WHERE model IS NOT NULL AND model != '' AND model_id IS NULL
            ''')
            orders_with_models = cursor.fetchall()
            
            migrated_count = 0
            for order_id, model_text in orders_with_models:
                if not model_text:
                    continue
                
                normalized_model = normalize_tag_name(model_text)
                if not normalized_model:
                    continue
                
                # Ищем или создаем модель в order_models
                cursor.execute('SELECT id FROM order_models WHERE name = ?', (normalized_model,))
                model_row = cursor.fetchone()
                
                if model_row:
                    model_id = model_row[0]
                else:
                    # Создаем новую модель
                    cursor.execute('INSERT INTO order_models (name) VALUES (?)', (normalized_model,))
                    model_id = cursor.lastrowid
                    logger.debug(f"Создана новая модель: {normalized_model} (ID: {model_id})")
                
                # Обновляем заявку
                cursor.execute('UPDATE orders SET model_id = ? WHERE id = ?', (model_id, order_id))
                migrated_count += 1
            
            logger.info(f"Мигрировано {migrated_count} заявок: model -> model_id")
        except Exception as e:
            logger.error(f"Ошибка при миграции model -> model_id: {e}", exc_info=True)
        
        # 3. Создаем таблицу order_symptoms (many-to-many)
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS order_symptoms (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id INTEGER NOT NULL,
                    symptom_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
                    FOREIGN KEY (symptom_id) REFERENCES symptoms(id) ON DELETE CASCADE,
                    UNIQUE(order_id, symptom_id)
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_order_symptoms_order_id ON order_symptoms(order_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_order_symptoms_symptom_id ON order_symptoms(symptom_id)')
            logger.info("Создана таблица order_symptoms")
        except sqlite3.OperationalError as e:
            if 'already exists' not in str(e).lower():
                raise
            logger.info("Таблица order_symptoms уже существует")
        
        # 4. Мигрируем данные из symptom_tags (TEXT) в order_symptoms
        try:
            cursor.execute('''
                SELECT id, symptom_tags 
                FROM orders 
                WHERE symptom_tags IS NOT NULL AND symptom_tags != ''
            ''')
            orders_with_symptoms = cursor.fetchall()
            
            migrated_count = 0
            for order_id, symptom_tags_text in orders_with_symptoms:
                if not symptom_tags_text:
                    continue
                
                # Парсим строку симптомов (разделители: запятая, точка с запятой, перенос строки)
                symptom_names = re.split(r'[,;\n\r]+', symptom_tags_text)
                symptom_ids = []
                
                for symptom_name in symptom_names:
                    normalized = normalize_tag_name(symptom_name)
                    if not normalized:
                        continue
                    
                    # Ищем симптом в справочнике
                    cursor.execute('SELECT id FROM symptoms WHERE name = ?', (normalized,))
                    symptom_row = cursor.fetchone()
                    
                    if symptom_row:
                        symptom_id = symptom_row[0]
                    else:
                        # Создаем новый симптом
                        cursor.execute('''
                            INSERT INTO symptoms (name, sort_order) 
                            VALUES (?, (SELECT COALESCE(MAX(sort_order), 0) + 1 FROM symptoms))
                        ''', (normalized,))
                        symptom_id = cursor.lastrowid
                        logger.debug(f"Создан новый симптом: {normalized} (ID: {symptom_id})")
                    
                    symptom_ids.append(symptom_id)
                
                # Создаем связи в order_symptoms
                for symptom_id in symptom_ids:
                    try:
                        cursor.execute('''
                            INSERT INTO order_symptoms (order_id, symptom_id) 
                            VALUES (?, ?)
                        ''', (order_id, symptom_id))
                    except sqlite3.IntegrityError:
                        # Связь уже существует
                        pass
                
                if symptom_ids:
                    migrated_count += 1
            
            logger.info(f"Мигрировано {migrated_count} заявок: symptom_tags -> order_symptoms")
        except Exception as e:
            logger.error(f"Ошибка при миграции symptom_tags -> order_symptoms: {e}", exc_info=True)
        
        # 5. Создаем таблицу order_appearance_tags (many-to-many)
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS order_appearance_tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id INTEGER NOT NULL,
                    appearance_tag_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
                    FOREIGN KEY (appearance_tag_id) REFERENCES appearance_tags(id) ON DELETE CASCADE,
                    UNIQUE(order_id, appearance_tag_id)
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_order_appearance_order_id ON order_appearance_tags(order_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_order_appearance_tag_id ON order_appearance_tags(appearance_tag_id)')
            logger.info("Создана таблица order_appearance_tags")
        except sqlite3.OperationalError as e:
            if 'already exists' not in str(e).lower():
                raise
            logger.info("Таблица order_appearance_tags уже существует")
        
        # 6. Мигрируем данные из appearance (TEXT) в order_appearance_tags
        try:
            cursor.execute('''
                SELECT id, appearance 
                FROM orders 
                WHERE appearance IS NOT NULL AND appearance != ''
            ''')
            orders_with_appearance = cursor.fetchall()
            
            migrated_count = 0
            for order_id, appearance_text in orders_with_appearance:
                if not appearance_text:
                    continue
                
                # Парсим строку тегов внешнего вида
                tag_names = re.split(r'[,;\n\r]+', appearance_text)
                tag_ids = []
                
                for tag_name in tag_names:
                    normalized = normalize_tag_name(tag_name)
                    if not normalized:
                        continue
                    
                    # Ищем тег в справочнике
                    cursor.execute('SELECT id FROM appearance_tags WHERE name = ?', (normalized,))
                    tag_row = cursor.fetchone()
                    
                    if tag_row:
                        tag_id = tag_row[0]
                    else:
                        # Создаем новый тег
                        cursor.execute('''
                            INSERT INTO appearance_tags (name, sort_order) 
                            VALUES (?, (SELECT COALESCE(MAX(sort_order), 0) + 1 FROM appearance_tags))
                        ''', (normalized,))
                        tag_id = cursor.lastrowid
                        logger.debug(f"Создан новый тег внешнего вида: {normalized} (ID: {tag_id})")
                    
                    tag_ids.append(tag_id)
                
                # Создаем связи в order_appearance_tags
                for tag_id in tag_ids:
                    try:
                        cursor.execute('''
                            INSERT INTO order_appearance_tags (order_id, appearance_tag_id) 
                            VALUES (?, ?)
                        ''', (order_id, tag_id))
                    except sqlite3.IntegrityError:
                        # Связь уже существует
                        pass
                
                if tag_ids:
                    migrated_count += 1
            
            logger.info(f"Мигрировано {migrated_count} заявок: appearance -> order_appearance_tags")
        except Exception as e:
            logger.error(f"Ошибка при миграции appearance -> order_appearance_tags: {e}", exc_info=True)
        
        conn.commit()
        logger.info("Миграция 013_normalize_order_references успешно применена")


def down():
    """Откатывает миграцию."""
    logger.warning("Откат миграции 013_normalize_order_references")
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Удаляем связующие таблицы
        try:
            cursor.execute('DROP TABLE IF EXISTS order_appearance_tags')
            logger.info("Таблица order_appearance_tags удалена")
        except Exception as e:
            logger.warning(f"Не удалось удалить order_appearance_tags: {e}")
        
        try:
            cursor.execute('DROP TABLE IF EXISTS order_symptoms')
            logger.info("Таблица order_symptoms удалена")
        except Exception as e:
            logger.warning(f"Не удалось удалить order_symptoms: {e}")
        
        # SQLite не поддерживает DROP COLUMN напрямую
        # Колонка model_id останется, но можно игнорировать
        logger.warning("Колонка model_id не может быть удалена (SQLite ограничения)")
        logger.warning("Для полного отката необходимо вручную пересоздать таблицу orders")
        
        conn.commit()
        logger.warning("Миграция 013_normalize_order_references откачена (частично)")

