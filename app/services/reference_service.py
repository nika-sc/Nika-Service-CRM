"""
Сервис для работы со справочниками с кэшированием.
"""
from typing import List, Dict, Optional, Any
from app.utils.cache import cache_result, clear_cache
from app.database.queries.reference_queries import ReferenceQueries
from app.utils.exceptions import ValidationError, NotFoundError, DatabaseError
from app.utils.types import ReferenceDict
from app.database.connection import get_db_connection
import sqlite3
import logging

logger = logging.getLogger(__name__)


class ReferenceService:
    """Сервис для работы со справочниками с кэшированием."""
    
    @staticmethod
    @cache_result(timeout=3600, key_prefix='ref_device_types')  # Кэш на 1 час
    def get_device_types() -> List[ReferenceDict]:
        """
        Получает типы устройств с кэшированием.
        
        Returns:
            Список словарей с данными типов устройств
        """
        return ReferenceQueries.get_device_types()
    
    @staticmethod
    @cache_result(timeout=3600, key_prefix='ref_device_brands')
    def get_device_brands() -> List[ReferenceDict]:
        """
        Получает бренды устройств с кэшированием.
        
        Returns:
            Список словарей с данными брендов устройств
        """
        return ReferenceQueries.get_device_brands()
    
    @staticmethod
    @cache_result(timeout=3600, key_prefix='ref_managers')
    def get_managers() -> List[ReferenceDict]:
        """
        Получает менеджеров с кэшированием.
        
        Returns:
            Список словарей с данными менеджеров
        """
        return ReferenceQueries.get_managers()
    
    @staticmethod
    @cache_result(timeout=3600, key_prefix='ref_masters')
    def get_masters() -> List[ReferenceDict]:
        """
        Получает мастеров с кэшированием.
        
        Returns:
            Список словарей с данными мастеров
        """
        return ReferenceQueries.get_masters()
    
    @staticmethod
    @cache_result(timeout=3600, key_prefix='ref_symptoms')
    def get_symptoms() -> List[ReferenceDict]:
        """
        Получает симптомы с кэшированием.
        
        Returns:
            Список словарей с данными симптомов
        """
        return ReferenceQueries.get_symptoms()
    
    @staticmethod
    @cache_result(timeout=3600, key_prefix='ref_appearance_tags')
    def get_appearance_tags() -> List[ReferenceDict]:
        """
        Получает теги внешнего вида с кэшированием.
        
        Returns:
            Список словарей с данными тегов внешнего вида
        """
        return ReferenceQueries.get_appearance_tags()
    
    @staticmethod
    @cache_result(timeout=3600, key_prefix='ref_services')
    def get_services() -> List[Dict[str, Any]]:
        """
        Получает услуги с кэшированием.
        
        Returns:
            Список словарей с данными услуг
        """
        return ReferenceQueries.get_services()
    
    @staticmethod
    @cache_result(timeout=3600, key_prefix='ref_order_statuses')
    def get_order_statuses(include_archived: bool = False) -> List[ReferenceDict]:
        """
        Получает статусы заявок с кэшированием.
        
        Args:
            include_archived: Включать архивные статусы
            
        Returns:
            Список словарей с данными статусов заявок
        """
        return ReferenceQueries.get_order_statuses(include_archived=include_archived)
    
    @staticmethod
    @cache_result(timeout=3600, key_prefix='ref_parts')
    def get_parts(search_query: Optional[str] = None, category: Optional[str] = None,
                  low_stock_only: bool = False) -> List[Dict]:
        """
        Получает запчасти с кэшированием.
        
        Args:
            search_query: Поисковый запрос
            category: Категория
            low_stock_only: Только с низким остатком
            
        Returns:
            Список запчастей
        """
        return ReferenceQueries.get_parts(search_query=search_query, category=category)
    
    @staticmethod
    @cache_result(timeout=300, key_prefix='ref_usage_counts')  # Кэш на 5 минут
    def get_all_usage_counts() -> Dict[str, Dict[int, int]]:
        """
        Получает все usage counts для всех справочников одним запросом.
        
        Returns:
            Словарь с usage counts:
            {
                'device_types': {type_id: count, ...},
                'device_brands': {brand_id: count, ...},
                'symptoms': {symptom_id: count, ...},
                'appearance_tags': {tag_id: count, ...},
                'services': {service_id: count, ...}
            }
        """
        result = {
            'device_types': {},
            'device_brands': {},
            'symptoms': {},
            'appearance_tags': {},
            'services': {}
        }
        
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                
                # Device types usage (devices + orders)
                cursor.execute('''
                    SELECT dt.id, 
                           COUNT(DISTINCT d.id) as devices_count,
                           COUNT(DISTINCT o.id) as orders_count
                    FROM device_types dt
                    LEFT JOIN devices d ON d.device_type_id = dt.id
                    LEFT JOIN orders o ON o.device_id = d.id
                    GROUP BY dt.id
                ''')
                for row in cursor.fetchall():
                    result['device_types'][row['id']] = row['devices_count'] + row['orders_count']
                
                # Device brands usage (devices + orders)
                cursor.execute('''
                    SELECT db.id,
                           COUNT(DISTINCT d.id) as devices_count,
                           COUNT(DISTINCT o.id) as orders_count
                    FROM device_brands db
                    LEFT JOIN devices d ON d.device_brand_id = db.id
                    LEFT JOIN orders o ON o.device_id = d.id
                    GROUP BY db.id
                ''')
                for row in cursor.fetchall():
                    result['device_brands'][row['id']] = row['devices_count'] + row['orders_count']
                
                # Symptoms usage (orders)
                cursor.execute('''
                    SELECT s.id, COUNT(DISTINCT os.order_id) as count
                    FROM symptoms s
                    LEFT JOIN order_symptoms os ON os.symptom_id = s.id
                    GROUP BY s.id
                ''')
                for row in cursor.fetchall():
                    result['symptoms'][row['id']] = row['count']
                
                # Appearance tags usage (orders)
                cursor.execute('''
                    SELECT at.id, COUNT(DISTINCT oat.order_id) as count
                    FROM appearance_tags at
                    LEFT JOIN order_appearance_tags oat ON oat.appearance_tag_id = at.id
                    GROUP BY at.id
                ''')
                for row in cursor.fetchall():
                    result['appearance_tags'][row['id']] = row['count']
                
                # Services usage (orders)
                cursor.execute('''
                    SELECT s.id, COUNT(DISTINCT os.order_id) as count
                    FROM services s
                    LEFT JOIN order_services os ON os.service_id = s.id
                    GROUP BY s.id
                ''')
                for row in cursor.fetchall():
                    result['services'][row['id']] = row['count']
                
        except Exception as e:
            logger.error(f"Ошибка при получении usage counts: {e}")
        
        return result
    
    @staticmethod
    def get_all_references() -> Dict[str, List[Dict[str, Any]]]:
        """
        Получает все справочники одним вызовом (для форм).
        
        Returns:
            Словарь со всеми справочниками:
            - device_types: List[ReferenceDict] - типы устройств
            - device_brands: List[ReferenceDict] - бренды устройств
            - managers: List[ReferenceDict] - менеджеры
            - masters: List[ReferenceDict] - мастера
            - symptoms: List[ReferenceDict] - симптомы
            - appearance_tags: List[ReferenceDict] - теги внешнего вида
            - services: List[Dict[str, Any]] - услуги
            - parts: List[Dict[str, Any]] - запчасти
            - order_statuses: List[ReferenceDict] - статусы заявок
        """
        return ReferenceQueries.get_all_references()
    
    @staticmethod
    def clear_all_cache():
        """
        Очищает кэш всех справочников.
        Используется при изменении справочников.
        """
        clear_cache(key_prefix='ref_device_types')
        clear_cache(key_prefix='ref_device_brands')
        clear_cache(key_prefix='ref_managers')
        clear_cache(key_prefix='ref_masters')
        clear_cache(key_prefix='ref_symptoms')
        clear_cache(key_prefix='ref_appearance_tags')
        clear_cache(key_prefix='ref_services')
        clear_cache(key_prefix='ref_order_statuses')
        clear_cache(key_prefix='ref_parts')
        clear_cache(key_prefix='ref_part_categories')
        logger.info("Кэш всех справочников очищен")
    
    # CRUD методы для типов устройств
    @staticmethod
    def create_device_type(name: str, sort_order: Optional[int] = None) -> int:
        """Создает тип устройства."""
        if not name or not name.strip():
            raise ValidationError("Название типа устройства обязательно")
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                if sort_order is None:
                    cursor.execute("SELECT MAX(sort_order) FROM device_types")
                    max_order = cursor.fetchone()[0]
                    sort_order = (max_order or 0) + 1
                
                cursor.execute('''
                    INSERT INTO device_types (name, sort_order)
                    VALUES (?, ?)
                ''', (name.strip(), sort_order))
                conn.commit()
                
                clear_cache(key_prefix='ref_device_types')
                type_id = cursor.lastrowid
                return type_id
        except sqlite3.IntegrityError:
            raise ValidationError("Тип устройства с таким названием уже существует")
        except Exception as e:
            logger.error(f"Ошибка при создании типа устройства: {e}")
            raise DatabaseError(f"Ошибка при создании типа устройства: {e}")
    
    @staticmethod
    def update_device_type(type_id: int, name: Optional[str] = None, sort_order: Optional[int] = None) -> bool:
        """Обновляет тип устройства."""
        if not type_id or type_id <= 0:
            raise ValidationError("Неверный ID типа устройства")
        
        updates = []
        params = []
        
        if name is not None:
            if not name.strip():
                raise ValidationError("Название типа устройства не может быть пустым")
            updates.append('name = ?')
            params.append(name.strip())
        
        if sort_order is not None:
            updates.append('sort_order = ?')
            params.append(sort_order)
        
        if not updates:
            return False
        
        params.append(type_id)
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f'''
                    UPDATE device_types 
                    SET {', '.join(updates)}
                    WHERE id = ?
                ''', params)
                conn.commit()
                
                clear_cache(key_prefix='ref_device_types')
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка при обновлении типа устройства {type_id}: {e}")
            raise DatabaseError(f"Ошибка при обновлении типа устройства: {e}")
    
    @staticmethod
    def delete_device_type(type_id: int) -> bool:
        """Удаляет тип устройства."""
        if not type_id or type_id <= 0:
            raise ValidationError("Неверный ID типа устройства")
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Проверяем, используется ли тип устройства в устройствах
                cursor.execute('SELECT COUNT(*) FROM devices WHERE device_type_id = ?', (type_id,))
                usage_count = cursor.fetchone()[0]
                
                if usage_count > 0:
                    raise ValidationError(f"Тип устройства используется в {usage_count} устройстве(ах) и не может быть удален")
                
                cursor.execute('DELETE FROM device_types WHERE id = ?', (type_id,))
                conn.commit()
                
                clear_cache(key_prefix='ref_device_types')
                return cursor.rowcount > 0
        except ValidationError:
            raise
        except sqlite3.IntegrityError as e:
            error_msg = str(e).lower()
            if 'foreign key' in error_msg:
                raise ValidationError("Тип устройства используется в других записях и не может быть удален")
            raise DatabaseError(f"Ошибка при удалении типа устройства: {e}")
        except Exception as e:
            logger.error(f"Ошибка при удалении типа устройства {type_id}: {e}")
            raise DatabaseError(f"Ошибка при удалении типа устройства: {e}")
    
    # CRUD методы для брендов устройств
    @staticmethod
    def create_device_brand(name: str, sort_order: Optional[int] = None) -> int:
        """Создает бренд устройства."""
        if not name or not name.strip():
            raise ValidationError("Название бренда обязательно")
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                if sort_order is None:
                    cursor.execute("SELECT MAX(sort_order) FROM device_brands")
                    max_order = cursor.fetchone()[0]
                    sort_order = (max_order or 0) + 1
                
                cursor.execute('''
                    INSERT INTO device_brands (name, sort_order)
                    VALUES (?, ?)
                ''', (name.strip(), sort_order))
                conn.commit()
                
                clear_cache(key_prefix='ref_device_brands')
                return cursor.lastrowid
        except sqlite3.IntegrityError:
            raise ValidationError("Бренд с таким названием уже существует")
        except Exception as e:
            logger.error(f"Ошибка при создании бренда: {e}")
            raise DatabaseError(f"Ошибка при создании бренда: {e}")
    
    @staticmethod
    def update_device_brand(brand_id: int, name: Optional[str] = None, sort_order: Optional[int] = None) -> bool:
        """Обновляет бренд устройства."""
        if not brand_id or brand_id <= 0:
            raise ValidationError("Неверный ID бренда")
        
        updates = []
        params = []
        
        if name is not None:
            if not name.strip():
                raise ValidationError("Название бренда не может быть пустым")
            updates.append('name = ?')
            params.append(name.strip())
        
        if sort_order is not None:
            updates.append('sort_order = ?')
            params.append(sort_order)
        
        if not updates:
            return False
        
        params.append(brand_id)
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f'''
                    UPDATE device_brands 
                    SET {', '.join(updates)}
                    WHERE id = ?
                ''', params)
                conn.commit()
                
                clear_cache(key_prefix='ref_device_brands')
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка при обновлении бренда {brand_id}: {e}")
            raise DatabaseError(f"Ошибка при обновлении бренда: {e}")
    
    @staticmethod
    def delete_device_brand(brand_id: int) -> bool:
        """Удаляет бренд устройства."""
        if not brand_id or brand_id <= 0:
            raise ValidationError("Неверный ID бренда")
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Проверяем, используется ли бренд в устройствах
                cursor.execute('SELECT COUNT(*) FROM devices WHERE device_brand_id = ?', (brand_id,))
                usage_count = cursor.fetchone()[0]
                
                if usage_count > 0:
                    raise ValidationError(f"Бренд используется в {usage_count} устройстве(ах) и не может быть удален")
                
                cursor.execute('DELETE FROM device_brands WHERE id = ?', (brand_id,))
                conn.commit()
                
                clear_cache(key_prefix='ref_device_brands')
                return cursor.rowcount > 0
        except ValidationError:
            raise
        except sqlite3.IntegrityError as e:
            error_msg = str(e).lower()
            if 'foreign key' in error_msg:
                raise ValidationError("Бренд используется в других записях и не может быть удален")
            raise DatabaseError(f"Ошибка при удалении бренда: {e}")
        except Exception as e:
            logger.error(f"Ошибка при удалении бренда {brand_id}: {e}")
            raise DatabaseError(f"Ошибка при удалении бренда: {e}")
    
    # CRUD методы для симптомов
    @staticmethod
    def create_symptom(name: str, sort_order: Optional[int] = None) -> int:
        """Создает симптом."""
        if not name or not name.strip():
            raise ValidationError("Название симптома обязательно")
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                if sort_order is None:
                    cursor.execute("SELECT MAX(sort_order) FROM symptoms")
                    max_order = cursor.fetchone()[0]
                    sort_order = (max_order or 0) + 1
                
                cursor.execute('''
                    INSERT INTO symptoms (name, sort_order)
                    VALUES (?, ?)
                ''', (name.strip(), sort_order))
                conn.commit()
                
                clear_cache(key_prefix='ref_symptoms')
                return cursor.lastrowid
        except sqlite3.IntegrityError:
            raise ValidationError("Симптом с таким названием уже существует")
        except Exception as e:
            logger.error(f"Ошибка при создании симптома: {e}")
            raise DatabaseError(f"Ошибка при создании симптома: {e}")
    
    @staticmethod
    def update_symptom(symptom_id: int, name: Optional[str] = None, sort_order: Optional[int] = None) -> bool:
        """Обновляет симптом."""
        if not symptom_id or symptom_id <= 0:
            raise ValidationError("Неверный ID симптома")
        
        updates = []
        params = []
        
        if name is not None:
            if not name.strip():
                raise ValidationError("Название симптома не может быть пустым")
            updates.append('name = ?')
            params.append(name.strip())
        
        if sort_order is not None:
            updates.append('sort_order = ?')
            params.append(sort_order)
        
        if not updates:
            return False
        
        params.append(symptom_id)
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f'''
                    UPDATE symptoms 
                    SET {', '.join(updates)}
                    WHERE id = ?
                ''', params)
                conn.commit()
                
                clear_cache(key_prefix='ref_symptoms')
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка при обновлении симптома {symptom_id}: {e}")
            raise DatabaseError(f"Ошибка при обновлении симптома: {e}")
    
    @staticmethod
    def delete_symptom(symptom_id: int) -> bool:
        """Удаляет симптом."""
        if not symptom_id or symptom_id <= 0:
            raise ValidationError("Неверный ID симптома")
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Проверяем, используется ли симптом в заявках
                cursor.execute('SELECT COUNT(*) FROM order_symptoms WHERE symptom_id = ?', (symptom_id,))
                usage_count = cursor.fetchone()[0]
                
                if usage_count > 0:
                    raise ValidationError(f"Симптом используется в {usage_count} заявке(ах) и не может быть удален")
                
                cursor.execute('DELETE FROM symptoms WHERE id = ?', (symptom_id,))
                conn.commit()
                
                clear_cache(key_prefix='ref_symptoms')
                return cursor.rowcount > 0
        except ValidationError:
            raise
        except sqlite3.IntegrityError as e:
            error_msg = str(e).lower()
            if 'foreign key' in error_msg:
                raise ValidationError("Симптом используется в других записях и не может быть удален")
            raise DatabaseError(f"Ошибка при удалении симптома: {e}")
        except Exception as e:
            logger.error(f"Ошибка при удалении симптома {symptom_id}: {e}")
            raise DatabaseError(f"Ошибка при удалении симптома: {e}")
    
    # CRUD методы для тегов внешнего вида
    @staticmethod
    def create_appearance_tag(name: str, sort_order: Optional[int] = None) -> int:
        """Создает тег внешнего вида."""
        if not name or not name.strip():
            raise ValidationError("Название тега обязательно")
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                if sort_order is None:
                    cursor.execute("SELECT MAX(sort_order) FROM appearance_tags")
                    max_order = cursor.fetchone()[0]
                    sort_order = (max_order or 0) + 1
                
                cursor.execute('''
                    INSERT INTO appearance_tags (name, sort_order)
                    VALUES (?, ?)
                ''', (name.strip(), sort_order))
                conn.commit()
                
                clear_cache(key_prefix='ref_appearance_tags')
                return cursor.lastrowid
        except sqlite3.IntegrityError:
            raise ValidationError("Тег с таким названием уже существует")
        except Exception as e:
            logger.error(f"Ошибка при создании тега: {e}")
            raise DatabaseError(f"Ошибка при создании тега: {e}")
    
    @staticmethod
    def update_appearance_tag(tag_id: int, name: Optional[str] = None, sort_order: Optional[int] = None) -> bool:
        """Обновляет тег внешнего вида."""
        if not tag_id or tag_id <= 0:
            raise ValidationError("Неверный ID тега")
        
        updates = []
        params = []
        
        if name is not None:
            if not name.strip():
                raise ValidationError("Название тега не может быть пустым")
            updates.append('name = ?')
            params.append(name.strip())
        
        if sort_order is not None:
            updates.append('sort_order = ?')
            params.append(sort_order)
        
        if not updates:
            return False
        
        params.append(tag_id)
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f'''
                    UPDATE appearance_tags 
                    SET {', '.join(updates)}
                    WHERE id = ?
                ''', params)
                conn.commit()
                
                clear_cache(key_prefix='ref_appearance_tags')
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка при обновлении тега {tag_id}: {e}")
            raise DatabaseError(f"Ошибка при обновлении тега: {e}")
    
    @staticmethod
    def delete_appearance_tag(tag_id: int) -> bool:
        """Удаляет тег внешнего вида."""
        if not tag_id or tag_id <= 0:
            raise ValidationError("Неверный ID тега")
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Проверяем, используется ли тег в заявках
                cursor.execute('SELECT COUNT(*) FROM order_appearance_tags WHERE appearance_tag_id = ?', (tag_id,))
                usage_count = cursor.fetchone()[0]
                
                if usage_count > 0:
                    raise ValidationError(f"Тег используется в {usage_count} заявке(ах) и не может быть удален")
                
                cursor.execute('DELETE FROM appearance_tags WHERE id = ?', (tag_id,))
                conn.commit()
                
                clear_cache(key_prefix='ref_appearance_tags')
                return cursor.rowcount > 0
        except ValidationError:
            raise
        except sqlite3.IntegrityError as e:
            error_msg = str(e).lower()
            if 'foreign key' in error_msg:
                raise ValidationError("Тег используется в других записях и не может быть удален")
            raise DatabaseError(f"Ошибка при удалении тега: {e}")
        except Exception as e:
            logger.error(f"Ошибка при удалении тега {tag_id}: {e}")
            raise DatabaseError(f"Ошибка при удалении тега: {e}")
    
    # CRUD методы для услуг
    @staticmethod
    def create_service(
        name: str, 
        price: float = 0.0, 
        is_default: int = 0, 
        sort_order: Optional[int] = None,
        salary_rule_type: Optional[str] = None,
        salary_rule_value: Optional[float] = None
    ) -> int:
        """Создает услугу."""
        if not name or not name.strip():
            raise ValidationError("Название услуги обязательно")
        
        if price < 0:
            raise ValidationError("Цена не может быть отрицательной")
        
        if salary_rule_type and salary_rule_type not in ['percent', 'fixed']:
            raise ValidationError("Тип правила зарплаты должен быть 'percent' или 'fixed'")
        
        # Проверка на дубликаты
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT id, name FROM services WHERE name = ? LIMIT 1', (name.strip(),))
                existing = cursor.fetchone()
                if existing:
                    raise ValidationError(
                        f"Услуга с названием «{name.strip()}» уже существует (ID: {existing[0]}). "
                        f"Используйте существующую услугу или измените название."
                    )
        except ValidationError:
            raise
        except Exception as e:
            logger.warning(f"Ошибка при проверке дубликатов услуги: {e}")
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                if sort_order is None:
                    cursor.execute("SELECT MAX(sort_order) FROM services")
                    max_order = cursor.fetchone()[0]
                    sort_order = (max_order or 0) + 1
                
                cursor.execute('''
                    INSERT INTO services (name, price, is_default, sort_order, salary_rule_type, salary_rule_value)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (name.strip(), price, is_default, sort_order, salary_rule_type, salary_rule_value))
                conn.commit()
                
                clear_cache(key_prefix='ref_services')
                return cursor.lastrowid
        except sqlite3.IntegrityError as e:
            error_msg = str(e)
            if 'UNIQUE constraint failed' in error_msg or 'unique constraint' in error_msg.lower():
                raise ValidationError(
                    f"Услуга с названием «{name.strip()}» уже существует. "
                    f"Используйте существующую услугу или измените название."
                )
            raise DatabaseError(f"Ошибка при создании услуги: {error_msg}")
        except Exception as e:
            logger.error(f"Ошибка при создании услуги: {e}")
            raise DatabaseError(f"Ошибка при создании услуги: {e}")
    
    @staticmethod
    def update_service(
        service_id: int, 
        name: Optional[str] = None, 
        price: Optional[float] = None,
        is_default: Optional[int] = None, 
        sort_order: Optional[int] = None,
        salary_rule_type: Optional[str] = None,
        salary_rule_value: Optional[float] = None
    ) -> bool:
        """Обновляет услугу."""
        if not service_id or service_id <= 0:
            raise ValidationError("Неверный ID услуги")
        
        if salary_rule_type and salary_rule_type not in ['percent', 'fixed']:
            raise ValidationError("Тип правила зарплаты должен быть 'percent' или 'fixed'")
        
        updates = []
        params = []
        
        if name is not None:
            if not name.strip():
                raise ValidationError("Название услуги не может быть пустым")
            updates.append('name = ?')
            params.append(name.strip())
        
        if price is not None:
            if price < 0:
                raise ValidationError("Цена не может быть отрицательной")
            updates.append('price = ?')
            params.append(price)
        
        if is_default is not None:
            updates.append('is_default = ?')
            params.append(is_default)
        
        if sort_order is not None:
            updates.append('sort_order = ?')
            params.append(sort_order)
        
        if salary_rule_type is not None:
            updates.append('salary_rule_type = ?')
            params.append(salary_rule_type)
        
        if salary_rule_value is not None:
            updates.append('salary_rule_value = ?')
            params.append(salary_rule_value)
        
        if not updates:
            return False
        
        params.append(service_id)
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f'''
                    UPDATE services 
                    SET {', '.join(updates)}
                    WHERE id = ?
                ''', params)
                conn.commit()
                
                clear_cache(key_prefix='ref_services')
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка при обновлении услуги {service_id}: {e}")
            raise DatabaseError(f"Ошибка при обновлении услуги: {e}")
    
    @staticmethod
    def delete_service(service_id: int) -> bool:
        """Удаляет услугу."""
        if not service_id or service_id <= 0:
            raise ValidationError("Неверный ID услуги")
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Проверяем, используется ли услуга в заявках
                cursor.execute('SELECT COUNT(*) FROM order_services WHERE service_id = ?', (service_id,))
                usage_count = cursor.fetchone()[0]
                
                if usage_count > 0:
                    raise ValidationError(f"Услуга используется в {usage_count} заявке(ах) и не может быть удалена")
                
                cursor.execute('DELETE FROM services WHERE id = ?', (service_id,))
                conn.commit()
                
                clear_cache(key_prefix='ref_services')
                return cursor.rowcount > 0
        except ValidationError:
            raise
        except sqlite3.IntegrityError as e:
            error_msg = str(e).lower()
            if 'foreign key' in error_msg:
                raise ValidationError("Услуга используется в других записях и не может быть удалена")
            raise DatabaseError(f"Ошибка при удалении услуги: {e}")
        except Exception as e:
            logger.error(f"Ошибка при удалении услуги {service_id}: {e}")
            raise DatabaseError(f"Ошибка при удалении услуги: {e}")
    
    # CRUD методы для запчастей
    @staticmethod
    def get_part(part_id: int) -> Optional[Dict]:
        """Получает запчасть по ID."""
        try:
            parts = ReferenceQueries.get_parts()
            return next((p for p in parts if p['id'] == part_id), None)
        except Exception as e:
            logger.error(f"Ошибка при получении запчасти {part_id}: {e}")
            return None
    
    @staticmethod
    def create_part(name: str, part_number: Optional[str] = None, description: Optional[str] = None,
                    price: float = 0.0, stock_quantity: int = 0, category: Optional[str] = None) -> int:
        """Создает запчасть."""
        if not name or not name.strip():
            raise ValidationError("Название запчасти обязательно")
        
        if price < 0:
            raise ValidationError("Цена не может быть отрицательной")
        
        if stock_quantity < 0:
            raise ValidationError("Количество на складе не может быть отрицательным")
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO parts (name, part_number, description, price, stock_quantity, category)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (name.strip(), part_number, description, price, stock_quantity, category))
                conn.commit()
                
                clear_cache(key_prefix='ref_parts')
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Ошибка при создании запчасти: {e}")
            raise DatabaseError(f"Ошибка при создании запчасти: {e}")
    
    @staticmethod
    def update_part(part_id: int, name: Optional[str] = None, part_number: Optional[str] = None,
                   description: Optional[str] = None, price: Optional[float] = None,
                   stock_quantity: Optional[int] = None, category: Optional[str] = None) -> bool:
        """Обновляет запчасть."""
        if not part_id or part_id <= 0:
            raise ValidationError("Неверный ID запчасти")
        
        updates = []
        params = []
        
        if name is not None:
            if not name.strip():
                raise ValidationError("Название запчасти не может быть пустым")
            updates.append('name = ?')
            params.append(name.strip())
        
        if part_number is not None:
            updates.append('part_number = ?')
            params.append(part_number)
        
        if description is not None:
            updates.append('description = ?')
            params.append(description)
        
        if price is not None:
            if price < 0:
                raise ValidationError("Цена не может быть отрицательной")
            updates.append('price = ?')
            params.append(price)
        
        # Получаем старый остаток перед обновлением
        old_stock = None
        if stock_quantity is not None:
            if stock_quantity < 0:
                raise ValidationError("Количество на складе не может быть отрицательным")
            # Получаем текущий остаток
            try:
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('SELECT stock_quantity FROM parts WHERE id = ?', (part_id,))
                    row = cursor.fetchone()
                    if row:
                        old_stock = int(row[0] or 0)
            except Exception:
                pass  # Если не удалось получить, пропускаем создание движения
            
            updates.append('stock_quantity = ?')
            params.append(stock_quantity)
        
        if category is not None:
            updates.append('category = ?')
            params.append(category)
        
        if not updates:
            return False
        
        updates.append('updated_at = CURRENT_TIMESTAMP')
        params.append(part_id)
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f'''
                    UPDATE parts 
                    SET {', '.join(updates)}
                    WHERE id = ?
                ''', params)
                
                # Создаем движение при изменении остатка
                if stock_quantity is not None and old_stock is not None:
                    stock_diff = stock_quantity - old_stock
                    if stock_diff != 0:
                        movement_type = 'adjustment_increase' if stock_diff > 0 else 'adjustment_decrease'
                        movement_qty = abs(stock_diff)
                        notes = f"Корректировка остатка через справочник: было {old_stock}, стало {stock_quantity}"
                        
                        cursor.execute('''
                            INSERT INTO stock_movements 
                            (part_id, movement_type, quantity, reference_type, notes)
                            VALUES (?, ?, ?, 'adjustment', ?)
                        ''', (part_id, movement_type, movement_qty, notes))
                
                conn.commit()
                
                clear_cache(key_prefix='ref_parts')
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка при обновлении запчасти {part_id}: {e}")
            raise DatabaseError(f"Ошибка при обновлении запчасти: {e}")
    
    @staticmethod
    def delete_part(part_id: int) -> bool:
        """Удаляет запчасть."""
        if not part_id or part_id <= 0:
            raise ValidationError("Неверный ID запчасти")
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM parts WHERE id = ?', (part_id,))
                conn.commit()
                
                clear_cache(key_prefix='ref_parts')
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка при удалении запчасти {part_id}: {e}")
            raise DatabaseError(f"Ошибка при удалении запчасти: {e}")
    
    # Методы для обновления порядка сортировки
    @staticmethod
    def update_device_types_sort_order(items: List[Dict]) -> bool:
        """Обновляет порядок сортировки типов устройств."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                for item in items:
                    cursor.execute('''
                        UPDATE device_types SET sort_order = ? WHERE id = ?
                    ''', (item.get('sort_order', 0), item['id']))
                conn.commit()
                
                clear_cache(key_prefix='ref_device_types')
                return True
        except Exception as e:
            logger.error(f"Ошибка при обновлении порядка сортировки типов устройств: {e}")
            raise DatabaseError(f"Ошибка при обновлении порядка сортировки: {e}")
    
    @staticmethod
    def update_device_brands_sort_order(items: List[Dict]) -> bool:
        """Обновляет порядок сортировки брендов."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                for item in items:
                    cursor.execute('''
                        UPDATE device_brands SET sort_order = ? WHERE id = ?
                    ''', (item.get('sort_order', 0), item['id']))
                conn.commit()
                
                clear_cache(key_prefix='ref_device_brands')
                return True
        except Exception as e:
            logger.error(f"Ошибка при обновлении порядка сортировки брендов: {e}")
            raise DatabaseError(f"Ошибка при обновлении порядка сортировки: {e}")
    
    @staticmethod
    def update_symptoms_sort_order(items: List[Dict]) -> bool:
        """Обновляет порядок сортировки симптомов."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                for item in items:
                    cursor.execute('''
                        UPDATE symptoms SET sort_order = ? WHERE id = ?
                    ''', (item.get('sort_order', 0), item['id']))
                conn.commit()
                
                clear_cache(key_prefix='ref_symptoms')
                return True
        except Exception as e:
            logger.error(f"Ошибка при обновлении порядка сортировки симптомов: {e}")
            raise DatabaseError(f"Ошибка при обновлении порядка сортировки: {e}")
    
    @staticmethod
    def update_appearance_tags_sort_order(items: List[Dict]) -> bool:
        """Обновляет порядок сортировки тегов внешнего вида."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                for item in items:
                    cursor.execute('''
                        UPDATE appearance_tags SET sort_order = ? WHERE id = ?
                    ''', (item.get('sort_order', 0), item['id']))
                conn.commit()
                
                clear_cache(key_prefix='ref_appearance_tags')
                return True
        except Exception as e:
            logger.error(f"Ошибка при обновлении порядка сортировки тегов: {e}")
            raise DatabaseError(f"Ошибка при обновлении порядка сортировки: {e}")
    
    @staticmethod
    def update_services_sort_order(items: List[Dict]) -> bool:
        """Обновляет порядок сортировки услуг."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                for item in items:
                    cursor.execute('''
                        UPDATE services SET sort_order = ? WHERE id = ?
                    ''', (item.get('sort_order', 0), item['id']))
                conn.commit()
                
                clear_cache(key_prefix='ref_services')
                return True
        except Exception as e:
            logger.error(f"Ошибка при обновлении порядка сортировки услуг: {e}")
            raise DatabaseError(f"Ошибка при обновлении порядка сортировки: {e}")
    
    # CRUD методы для статусов заявок
    @staticmethod
    def create_order_status(code: str, name: str, color: str = '#007bff', 
                           is_default: int = 0, sort_order: int = 0) -> int:
        """Создает статус заявки."""
        if not code or not code.strip():
            raise ValidationError("Код статуса обязателен")
        
        if not name or not name.strip():
            raise ValidationError("Название статуса обязательно")
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Если это статус по умолчанию, снимаем флаг с других статусов
                if is_default:
                    cursor.execute('UPDATE order_statuses SET is_default = 0')
                
                cursor.execute('''
                    INSERT INTO order_statuses (code, name, color, is_default, sort_order)
                    VALUES (?, ?, ?, ?, ?)
                ''', (code.strip(), name.strip(), color, is_default, sort_order))
                conn.commit()
                
                clear_cache(key_prefix='ref_order_statuses')
                return cursor.lastrowid
        except sqlite3.IntegrityError:
            raise ValidationError("Статус с таким кодом уже существует")
        except Exception as e:
            logger.error(f"Ошибка при создании статуса: {e}")
            raise DatabaseError(f"Ошибка при создании статуса: {e}")
    
    @staticmethod
    def update_order_status(status_id: int, code: Optional[str] = None, name: Optional[str] = None,
                           color: Optional[str] = None, is_default: Optional[int] = None,
                           sort_order: Optional[int] = None) -> bool:
        """Обновляет статус заявки."""
        if not status_id or status_id <= 0:
            raise ValidationError("Неверный ID статуса")
        
        updates = []
        params = []
        
        if code is not None:
            if not code.strip():
                raise ValidationError("Код статуса не может быть пустым")
            updates.append('code = ?')
            params.append(code.strip())
        
        if name is not None:
            if not name.strip():
                raise ValidationError("Название статуса не может быть пустым")
            updates.append('name = ?')
            params.append(name.strip())
        
        if color is not None:
            updates.append('color = ?')
            params.append(color)
        
        if is_default is not None:
            updates.append('is_default = ?')
            params.append(is_default)
            # Если это статус по умолчанию, снимаем флаг с других статусов
            if is_default:
                try:
                    with get_db_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute('UPDATE order_statuses SET is_default = 0 WHERE id != ?', (status_id,))
                        conn.commit()
                except Exception as e:
                    logger.warning(f"Не удалось снять флаг is_default с других статусов: {e}")
        
        if sort_order is not None:
            updates.append('sort_order = ?')
            params.append(sort_order)
        
        if not updates:
            return False
        
        params.append(status_id)
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f'''
                    UPDATE order_statuses 
                    SET {', '.join(updates)}
                    WHERE id = ?
                ''', params)
                conn.commit()
                
                clear_cache(key_prefix='ref_order_statuses')
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка при обновлении статуса {status_id}: {e}")
            raise DatabaseError(f"Ошибка при обновлении статуса: {e}")
    
    @staticmethod
    def delete_order_status(status_id: int) -> bool:
        """Удаляет статус заявки."""
        if not status_id or status_id <= 0:
            raise ValidationError("Неверный ID статуса")
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM order_statuses WHERE id = ?', (status_id,))
                conn.commit()
                
                clear_cache(key_prefix='ref_order_statuses')
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка при удалении статуса {status_id}: {e}")
            raise DatabaseError(f"Ошибка при удалении статуса: {e}")

