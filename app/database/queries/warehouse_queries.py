"""
SQL запросы для работы со складом.
"""
from typing import Dict, List, Optional
from app.database.connection import get_db_connection
from app.utils.exceptions import ValidationError
import sqlite3
import logging

logger = logging.getLogger(__name__)


class WarehouseQueries:
    """Класс для SQL-запросов по складу."""

    @staticmethod
    def _part_price_column(cursor) -> str:
        """Возвращает актуальное имя колонки розничной цены в parts."""
        cursor.execute("PRAGMA table_info(parts)")
        columns = {row[1] for row in cursor.fetchall()}
        if "retail_price" in columns:
            return "retail_price"
        return "price"
    
    @staticmethod
    def get_stock_levels(
        search_query: Optional[str] = None,
        category: Optional[str] = None,
        low_stock_only: bool = False,
        page: int = 1,
        per_page: int = 50,
        sort_by: str = 'name',
        sort_order: str = 'ASC'
    ) -> Dict:
        """
        Получает остатки товаров на складе.
        
        Args:
            search_query: Поисковый запрос (название, артикул, категория) - полнотекстовый поиск по всем словам
            category: Фильтр по категории
            low_stock_only: Только товары с низким остатком
            page: Номер страницы
            per_page: Количество элементов на странице
            sort_by: Поле для сортировки (name, part_number, category, stock_quantity, retail_price, margin)
            sort_order: Направление сортировки (ASC, DESC)
            
        Returns:
            Словарь с данными: items, total, page, per_page, pages
        """
        offset = (page - 1) * per_page
        where_clauses = ['p.is_deleted = 0']  # Исключаем удаленные товары
        params = []
        
        # Полнотекстовый поиск по всем словам (регистронезависимый)
        if search_query:
            # Разбиваем поисковый запрос на слова
            search_words = search_query.strip().split()
            if search_words:
                search_conditions = []
                for word in search_words:
                    # Для регистронезависимого поиска создаем паттерн с оригинальным словом
                    # SQLite LIKE по умолчанию регистрозависимый, но мы используем несколько вариантов
                    # для надежности работы с кириллицей
                    word_lower = word.lower()
                    word_upper = word.upper()
                    word_title = word.capitalize()
                    
                    # Создаем паттерны для всех вариантов регистра
                    patterns = [f'%{word_lower}%', f'%{word_upper}%', f'%{word_title}%', f'%{word}%']
                    # Убираем дубликаты
                    patterns = list(dict.fromkeys(patterns))
                    
                    # Поиск по названию, артикулу, категории (через JOIN)
                    # Регистронезависимый поиск: проверяем все варианты регистра
                    # Поиск по всем словам: каждое слово должно встречаться хотя бы в одном поле (AND между словами)
                    # Используем COALESCE для безопасной обработки NULL значений
                    field_conditions = []
                    for pattern in patterns:
                        # Пустая строка только в одинарных кавычках — в PostgreSQL "" это идентификатор, не строка.
                        field_conditions.append("COALESCE(p.name, '') LIKE ?")
                        field_conditions.append("COALESCE(p.part_number, '') LIKE ?")
                        field_conditions.append("COALESCE(pc.name, '') LIKE ?")
                        params.extend([pattern, pattern, pattern])
                    
                    search_conditions.append('(' + ' OR '.join(field_conditions) + ')')
                # Все слова должны встречаться (AND между словами)
                where_clauses.append('(' + ' AND '.join(search_conditions) + ')')
        
        # Фильтр по категории (включая все подкатегории рекурсивно).
        # Поддерживаем legacy parts.category (TEXT) через COALESCE(pc.name, p.category).
        if category:
            # Находим ID категории по имени и получаем все подкатегории рекурсивно
            try:
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    # Проверяем, есть ли категория в part_categories
                    cursor.execute('SELECT id FROM part_categories WHERE name = ?', (category,))
                    cat_row = cursor.fetchone()
                    
                    if cat_row:
                        # Категория найдена в part_categories - получаем все подкатегории рекурсивно
                        category_id = cat_row[0]
                        
                        def get_all_subcategory_ids(parent_id):
                            """Получает все ID подкатегорий рекурсивно."""
                            cursor.execute('SELECT id FROM part_categories WHERE parent_id = ?', (parent_id,))
                            sub_ids = [row[0] for row in cursor.fetchall()]
                            all_ids = [parent_id] + sub_ids
                            for sub_id in sub_ids:
                                all_ids.extend(get_all_subcategory_ids(sub_id))
                            return list(set(all_ids))
                        
                        all_category_ids = get_all_subcategory_ids(category_id)
                        
                        # Фильтруем по category_id (включая все подкатегории) ИЛИ по legacy parts.category (TEXT)
                        if all_category_ids:
                            placeholders = ','.join(['?'] * len(all_category_ids))
                            where_clauses.append(f'(p.category_id IN ({placeholders}) OR COALESCE(pc.name, p.category) = ?)')
                            params.extend(all_category_ids)
                            params.append(category)
                        else:
                            # Только сама категория (без подкатегорий)
                            where_clauses.append('(p.category_id = ? OR COALESCE(pc.name, p.category) = ?)')
                            params.extend([category_id, category])
                    else:
                        # Категория не найдена в part_categories - используем только legacy parts.category (TEXT)
                        where_clauses.append('COALESCE(pc.name, p.category) = ?')
                        params.append(category)
            except Exception as e:
                logger.error(f"Ошибка при фильтрации по категории '{category}': {e}")
                # Fallback: используем простой фильтр
                where_clauses.append('COALESCE(pc.name, p.category) = ?')
                params.append(category)
        
        # Только товары с низким остатком
        if low_stock_only:
            where_clauses.append('p.stock_quantity <= p.min_quantity')
        
        where_sql = 'WHERE ' + ' AND '.join(where_clauses) if where_clauses else ''
        
        sort_order = sort_order.upper() if sort_order.upper() in ('ASC', 'DESC') else 'ASC'
        
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                price_column = WarehouseQueries._part_price_column(cursor)
                price_expr = f"p.{price_column}"
                sort_column_map = {
                    'name': 'p.name',
                    'part_number': 'p.part_number',
                    'category': 'pc.name',
                    'stock_quantity': 'p.stock_quantity',
                    'retail_price': price_expr,
                    'purchase_price': 'p.purchase_price',
                    'margin': 'margin',
                    'created_at': 'p.created_at'
                }
                order_column = sort_column_map.get(sort_by, 'p.name')
                
                # Подсчет общего количества
                count_query = f'''
                    SELECT COUNT(DISTINCT p.id)
                    FROM parts AS p
                    LEFT JOIN part_categories AS pc ON pc.id = p.category_id
                    {where_sql}
                '''
                cursor.execute(count_query, params)
                total = cursor.fetchone()[0]
                
                # Получение данных
                query = f'''
                    SELECT 
                        p.id,
                        p.name,
                        p.part_number,
                        p.description,
                        COALESCE({price_expr}, 0) AS retail_price,
                        p.purchase_price,
                        p.stock_quantity,
                        p.min_quantity,
                        p.category,
                        p.category_id,
                        COALESCE(pc.name, p.category) AS category_name,
                        p.supplier,
                        p.unit,
                        p.warranty_days,
                        p.comment,
                        p.created_at,
                        p.updated_at,
                        CASE 
                            WHEN p.stock_quantity <= p.min_quantity THEN 1
                            ELSE 0
                        END AS is_low_stock,
                        (COALESCE({price_expr}, 0) - COALESCE(p.purchase_price, 0)) AS margin
                    FROM parts AS p
                    LEFT JOIN part_categories AS pc ON pc.id = p.category_id
                    {where_sql}
                    ORDER BY {order_column} {sort_order}
                    LIMIT ? OFFSET ?
                '''
                params.extend([per_page, offset])
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                items = [dict(row) for row in rows]
                
                return {
                    'items': items,
                    'total': total,
                    'page': page,
                    'per_page': per_page,
                    'pages': (total + per_page - 1) // per_page if total > 0 else 0
                }
        except Exception as e:
            logger.error(f"Ошибка при получении остатков: {e}")
            return {
                'items': [],
                'total': 0,
                'page': page,
                'per_page': per_page,
                'pages': 0
            }
    
    @staticmethod
    def get_purchases(
        supplier_id: Optional[int] = None,
        status: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        page: int = 1,
        per_page: int = 50
    ) -> Dict:
        """
        Получает список закупок.
        
        Args:
            supplier_id: Фильтр по поставщику
            status: Фильтр по статусу (draft, completed, cancelled)
            date_from: Дата начала
            date_to: Дата окончания
            page: Номер страницы
            per_page: Количество элементов на странице
            
        Returns:
            Словарь с данными: items, total, page, per_page, pages
        """
        offset = (page - 1) * per_page
        where_clauses = []
        params = []
        
        if supplier_id:
            where_clauses.append('p.supplier_id = ?')
            params.append(supplier_id)
        
        if status:
            where_clauses.append('p.status = ?')
            params.append(status)
        
        if date_from:
            where_clauses.append('p.purchase_date >= ?')
            params.append(date_from)
        
        if date_to:
            where_clauses.append('p.purchase_date <= ?')
            params.append(date_to)
        
        where_sql = 'WHERE ' + ' AND '.join(where_clauses) if where_clauses else ''
        
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                
                # Подсчет общего количества
                count_query = f'''
                    SELECT COUNT(*)
                    FROM purchases AS p
                    {where_sql}
                '''
                cursor.execute(count_query, params)
                total = cursor.fetchone()[0]
                
                # Получение данных
                query = f'''
                    SELECT 
                        p.*,
                        MAX(u.username) AS created_by_username,
                        COUNT(pi.id) AS items_count
                    FROM purchases AS p
                    LEFT JOIN users AS u ON u.id = p.created_by
                    LEFT JOIN purchase_items AS pi ON pi.purchase_id = p.id
                    {where_sql}
                    GROUP BY p.id
                    ORDER BY p.purchase_date DESC, p.created_at DESC
                    LIMIT ? OFFSET ?
                '''
                params.extend([per_page, offset])
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                items = [dict(row) for row in rows]
                
                return {
                    'items': items,
                    'total': total,
                    'page': page,
                    'per_page': per_page,
                    'pages': (total + per_page - 1) // per_page if total > 0 else 0
                }
        except Exception as e:
            logger.error(f"Ошибка при получении закупок: {e}")
            return {
                'items': [],
                'total': 0,
                'page': page,
                'per_page': per_page,
                'pages': 0
            }
    
    @staticmethod
    def get_purchase_items(purchase_id: int) -> List[Dict]:
        """
        Получает позиции закупки.
        
        Args:
            purchase_id: ID закупки
            
        Returns:
            Список позиций закупки
        """
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT 
                        pi.*,
                        p.name AS part_name,
                        p.part_number,
                        p.category
                    FROM purchase_items AS pi
                    INNER JOIN parts AS p ON p.id = pi.part_id
                    WHERE pi.purchase_id = ?
                    ORDER BY pi.id
                ''', (purchase_id,))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Ошибка при получении позиций закупки {purchase_id}: {e}")
            return []
    
    @staticmethod
    def get_stock_movements(
        part_id: Optional[int] = None,
        movement_type: Optional[str] = None,
        operation_type: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Получает движения товаров.
        
        Args:
            part_id: Фильтр по товару
            movement_type: Тип движения (income, expense, sale, return, adjustment_increase, adjustment_decrease, purchase)
            operation_type: Тип операции ('manual' для ручных, 'auto' для автоматических)
            date_from: Дата начала
            date_to: Дата окончания
            limit: Максимальное количество записей
            
        Returns:
            Список движений
        """
        where_clauses = []
        params = []
        
        if part_id:
            where_clauses.append('sm.part_id = ?')
            params.append(part_id)
        
        if movement_type:
            # Специальная обработка для корректировок (оба типа вместе)
            if movement_type == 'adjustment':
                where_clauses.append('(sm.movement_type = ? OR sm.movement_type = ?)')
                params.extend(['adjustment_increase', 'adjustment_decrease'])
            elif movement_type == 'sale_order':
                # Продажа из заявки
                where_clauses.append('sm.movement_type = ? AND sm.reference_type = ?')
                params.extend(['sale', 'order'])
            elif movement_type == 'sale_shop':
                # Продажа из магазина
                where_clauses.append('sm.movement_type = ? AND sm.reference_type = ?')
                params.extend(['sale', 'shop_sale'])
            else:
                where_clauses.append('sm.movement_type = ?')
                params.append(movement_type)
        
        # Фильтр по типу операции (ручная/автоматическая)
        if operation_type == 'manual':
            # Ручные операции: manual (приход/расход из карточки) и adjustment (корректировки)
            where_clauses.append("(sm.reference_type = 'manual' OR sm.reference_type = 'adjustment')")
        elif operation_type == 'auto':
            # Автоматические операции: order, shop_sale, purchase
            where_clauses.append("(sm.reference_type = 'order' OR sm.reference_type = 'shop_sale' OR sm.reference_type = 'purchase')")
        
        if date_from:
            where_clauses.append('DATE(sm.created_at) >= DATE(?)')
            params.append(date_from)
        
        if date_to:
            where_clauses.append('DATE(sm.created_at) <= DATE(?)')
            params.append(date_to)
        
        where_sql = 'WHERE ' + ' AND '.join(where_clauses) if where_clauses else ''
        
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                cursor.execute(f'''
                    SELECT 
                        sm.*,
                        p.name AS part_name,
                        p.part_number,
                        u.username AS created_by_username,
                        CASE 
                            WHEN sm.reference_type = 'manual' OR sm.reference_type = 'adjustment' THEN 'manual'
                            WHEN sm.reference_type = 'order' OR sm.reference_type = 'shop_sale' OR sm.reference_type = 'purchase' THEN 'auto'
                            ELSE 'unknown'
                        END AS operation_category
                    FROM stock_movements AS sm
                    INNER JOIN parts AS p ON p.id = sm.part_id
                    LEFT JOIN users AS u ON u.id = sm.created_by
                    {where_sql}
                    ORDER BY sm.created_at DESC
                    LIMIT ?
                ''', params + [limit])
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Ошибка при получении движений товаров: {e}")
            return []
    
    @staticmethod
    def get_low_stock_items() -> List[Dict]:
        """
        Получает товары с низким остатком (stock_quantity <= min_quantity).
        
        Returns:
            Список товаров с низким остатком
        """
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT 
                        p.*,
                        (p.min_quantity - p.stock_quantity) AS shortage
                    FROM parts AS p
                    WHERE p.stock_quantity <= p.min_quantity AND p.is_deleted = 0
                    ORDER BY (p.min_quantity - p.stock_quantity) DESC, p.name ASC
                ''')
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Ошибка при получении товаров с низким остатком: {e}")
            return []
    
    @staticmethod
    def get_purchase_by_id(purchase_id: int) -> Optional[Dict]:
        """
        Получает закупку по ID.
        
        Args:
            purchase_id: ID закупки
            
        Returns:
            Словарь с данными закупки или None
        """
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT 
                        p.*,
                        u.username AS created_by_username
                    FROM purchases AS p
                    LEFT JOIN users AS u ON u.id = p.created_by
                    WHERE p.id = ?
                ''', (purchase_id,))
                
                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None
        except Exception as e:
            logger.error(f"Ошибка при получении закупки {purchase_id}: {e}")
            return None
    
    @staticmethod
    def get_part_stock_history(part_id: int, limit: int = 50) -> List[Dict]:
        """
        Получает историю движений по конкретному товару.
        
        Args:
            part_id: ID товара
            limit: Максимальное количество записей
            
        Returns:
            Список движений
        """
        return WarehouseQueries.get_stock_movements(part_id=part_id, limit=limit)
    
    @staticmethod
    def get_categories() -> List[Dict]:
        """
        Получает список всех категорий товаров с иерархией.
        
        Returns:
            Список категорий с полем children для подкатегорий
        """
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, name, description, parent_id, created_at, updated_at
                    FROM part_categories
                    ORDER BY CASE WHEN parent_id IS NULL THEN 0 ELSE 1 END, name ASC
                ''')
                rows = cursor.fetchall()
                categories = [dict(row) for row in rows]
                
                # Строим иерархию
                categories_dict = {cat['id']: {**cat, 'children': []} for cat in categories}
                root_categories = []
                
                for cat in categories:
                    if cat['parent_id']:
                        if cat['parent_id'] in categories_dict:
                            categories_dict[cat['parent_id']]['children'].append(categories_dict[cat['id']])
                    else:
                        root_categories.append(categories_dict[cat['id']])
                
                return root_categories
        except Exception as e:
            logger.error(f"Ошибка при получении категорий: {e}")
            return []
    
    @staticmethod
    def get_all_categories_flat() -> List[Dict]:
        """
        Получает плоский список всех категорий (без иерархии).
        
        Returns:
            Список всех категорий
        """
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, name, description, parent_id, created_at, updated_at
                    FROM part_categories
                    ORDER BY name ASC
                ''')
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Ошибка при получении категорий: {e}")
            return []
    
    # (временно) удалили get_category_and_all_subcategories: по требованию UI фильтруем только выбранную категорию
    
    @staticmethod
    def create_category(name: str, description: Optional[str] = None, parent_id: Optional[int] = None) -> int:
        """
        Создает новую категорию товаров.
        
        Args:
            name: Название категории
            description: Описание категории
            parent_id: ID родительской категории (для подкатегорий)
            
        Returns:
            ID созданной категории
            
        Raises:
            sqlite3.IntegrityError: Если категория с таким именем уже существует
        """
        from app.utils.exceptions import ValidationError as AppValidationError
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Проверка на дубликаты (с учетом parent_id - категории с одинаковым именем могут быть в разных родителях)
                cursor.execute('''
                    SELECT id, name FROM part_categories 
                    WHERE name = ? AND (parent_id = ? OR (parent_id IS NULL AND ? IS NULL))
                    LIMIT 1
                ''', (name.strip(), parent_id, parent_id))
                existing = cursor.fetchone()
                if existing:
                    parent_text = f" в категории ID {parent_id}" if parent_id else ""
                    raise AppValidationError(
                        f"Категория с названием «{name.strip()}»{parent_text} уже существует "
                        f"(ID: {existing[0]}). Используйте существующую категорию или измените название."
                    )
                
                cursor.execute('''
                    INSERT INTO part_categories (name, description, parent_id)
                    VALUES (?, ?, ?)
                ''', (name.strip(), description.strip() if description else None, parent_id))
                conn.commit()
                return cursor.lastrowid
        except AppValidationError:
            raise
        except sqlite3.IntegrityError as e:
            error_msg = str(e)
            if 'UNIQUE constraint failed' in error_msg or 'unique constraint' in error_msg.lower():
                parent_text = f" в категории ID {parent_id}" if parent_id else ""
                raise AppValidationError(
                    f"Категория с названием «{name.strip()}»{parent_text} уже существует. "
                    f"Используйте существующую категорию или измените название."
                )
            logger.error(f"Ошибка при создании категории: {e}")
            raise
        except Exception as e:
            logger.error(f"Ошибка при создании категории: {e}")
            raise
    
    @staticmethod
    def update_category(category_id: int, name: str, description: Optional[str] = None, parent_id: Optional[int] = None) -> bool:
        """
        Обновляет категорию товаров.
        
        Args:
            category_id: ID категории
            name: Новое название
            description: Новое описание
            parent_id: ID родительской категории (None для корневых категорий)
            
        Returns:
            True если успешно
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                # Проверяем, что категория не пытается стать родителем самой себя
                if parent_id == category_id:
                    raise ValueError("Категория не может быть родителем самой себя")
                
                cursor.execute('''
                    UPDATE part_categories
                    SET name = ?, description = ?, parent_id = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (name.strip(), description.strip() if description else None, parent_id, category_id))
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.IntegrityError as e:
            logger.error(f"Ошибка при обновлении категории: {e}")
            raise
        except Exception as e:
            logger.error(f"Ошибка при обновлении категории: {e}")
            raise
    
    @staticmethod
    def get_category_by_id(category_id: int) -> Optional[Dict]:
        """
        Получает категорию по ID.
        
        Args:
            category_id: ID категории
            
        Returns:
            Словарь с данными категории или None
        """
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, name, description, parent_id, created_at, updated_at
                    FROM part_categories
                    WHERE id = ?
                ''', (category_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Ошибка при получении категории {category_id}: {e}")
            return None
    
    @staticmethod
    def count_parts_in_category(category_name: str) -> int:
        """
        Подсчитывает количество товаров в категории (по имени категории).
        
        Args:
            category_name: Название категории
            
        Returns:
            Количество товаров в категории
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT COUNT(*) 
                    FROM parts 
                    WHERE category = ? AND is_deleted = 0
                ''', (category_name,))
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Ошибка при подсчете товаров в категории {category_name}: {e}")
            return 0
    
    @staticmethod
    def count_subcategories(category_id: int) -> int:
        """
        Подсчитывает количество подкатегорий у категории.
        
        Args:
            category_id: ID категории
            
        Returns:
            Количество подкатегорий
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT COUNT(*) 
                    FROM part_categories 
                    WHERE parent_id = ?
                ''', (category_id,))
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Ошибка при подсчете подкатегорий для категории {category_id}: {e}")
            return 0
    
    @staticmethod
    def delete_category(category_id: int) -> bool:
        """
        Удаляет категорию товаров.
        
        Args:
            category_id: ID категории
            
        Returns:
            True если успешно
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM part_categories WHERE id = ?', (category_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка при удалении категории: {e}")
            raise
    
    @staticmethod
    def get_part_by_id(part_id: int, include_deleted: bool = False) -> Optional[Dict]:
        """
        Получает товар по ID.
        
        Args:
            part_id: ID товара
            include_deleted: Включать удаленные товары
            
        Returns:
            Словарь с данными товара или None
        """
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                price_column = WarehouseQueries._part_price_column(cursor)
                price_expr = f"p.{price_column}"
                if include_deleted:
                    cursor.execute(f'''
                        SELECT 
                            p.*,
                            COALESCE({price_expr}, 0) AS retail_price
                        FROM parts AS p
                        WHERE p.id = ?
                    ''', (part_id,))
                else:
                    cursor.execute(f'''
                        SELECT 
                            p.*,
                            COALESCE({price_expr}, 0) AS retail_price
                        FROM parts AS p
                        WHERE p.id = ? AND p.is_deleted = 0
                    ''', (part_id,))
                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None
        except Exception as e:
            logger.error(f"Ошибка при получении товара {part_id}: {e}")
            return None
    
    @staticmethod
    def create_part(
        name: str,
        part_number: str,
        category: Optional[str] = None,
        category_id: Optional[int] = None,
        unit: str = 'шт',
        stock_quantity: int = 0,
        retail_price: float = 0.0,
        purchase_price: Optional[float] = None,
        warranty_days: Optional[int] = None,
        comment: Optional[str] = None,
        description: Optional[str] = None,
        min_quantity: int = 0,
        salary_rule_type: Optional[str] = None,
        salary_rule_value: Optional[float] = None
    ) -> int:
        """
        Создает новый товар.
        
        Args:
            name: Название товара
            part_number: Артикул
            category: Категория
            unit: Единица измерения
            stock_quantity: Начальный остаток
            retail_price: Розничная цена
            purchase_price: Закупочная цена
            warranty_days: Гарантия в днях
            comment: Комментарий
            description: Описание
            min_quantity: Минимальное количество
            
        Returns:
            ID созданного товара
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                price_column = WarehouseQueries._part_price_column(cursor)
                # Если передан category_id, пробуем получить name и сохранить также legacy parts.category (TEXT)
                category_name = category
                if category_id:
                    cursor.execute("SELECT name FROM part_categories WHERE id = ? LIMIT 1", (category_id,))
                    r = cursor.fetchone()
                    if r and r[0]:
                        category_name = r[0]
                cursor.execute('''
                    INSERT INTO parts 
                    (name, part_number, category, category_id, unit, stock_quantity, {price_column}, 
                     purchase_price, warranty_days, comment, description, min_quantity,
                     salary_rule_type, salary_rule_value)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                '''.format(price_column=price_column), (name.strip(), part_number.strip() if part_number else None,
                      category_name, category_id, unit, stock_quantity, retail_price,
                      purchase_price, warranty_days, comment, description, min_quantity,
                      salary_rule_type, salary_rule_value))
                conn.commit()
                return cursor.lastrowid
        except sqlite3.IntegrityError as e:
            # Обработка нарушения UNIQUE ограничения
            error_msg = str(e)
            if 'UNIQUE constraint failed' in error_msg or 'unique constraint' in error_msg.lower():
                # Пытаемся найти существующий товар для более информативного сообщения
                try:
                    cursor.execute('''
                        SELECT id, name, part_number 
                        FROM parts 
                        WHERE name = ? AND (part_number = ? OR (part_number IS NULL AND ? IS NULL))
                        AND is_deleted = 0
                        LIMIT 1
                    ''', (name.strip(), part_number.strip() if part_number else None, 
                          part_number.strip() if part_number else None))
                    existing = cursor.fetchone()
                    if existing:
                        raise ValidationError(
                            f"Товар с названием «{name.strip()}» и артикулом «{part_number.strip() if part_number else '(без артикула)'}» уже существует "
                            f"(ID: {existing[0]}). Используйте существующий товар или измените название/артикул."
                        )
                except ValidationError:
                    raise
            raise ValidationError(f"Ошибка при создании товара: {error_msg}")
        except Exception as e:
            logger.error(f"Ошибка при создании товара: {e}")
            raise
    
    @staticmethod
    def update_part(
        part_id: int,
        name: Optional[str] = None,
        category: Optional[str] = None,
        category_id: Optional[int] = None,
        unit: Optional[str] = None,
        stock_quantity: Optional[int] = None,
        retail_price: Optional[float] = None,
        purchase_price: Optional[float] = None,
        warranty_days: Optional[int] = None,
        comment: Optional[str] = None,
        description: Optional[str] = None,
        min_quantity: Optional[int] = None,
        salary_rule_type: Optional[str] = None,
        salary_rule_value: Optional[float] = None
    ) -> bool:
        """
        Обновляет товар (кроме артикула).
        
        Args:
            part_id: ID товара
            name: Название
            category: Категория
            unit: Единица измерения
            stock_quantity: Остаток
            retail_price: Розничная цена
            purchase_price: Закупочная цена
            warranty_days: Гарантия в днях
            comment: Комментарий
            description: Описание
            min_quantity: Минимальное количество
            
        Returns:
            True если успешно
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                price_column = WarehouseQueries._part_price_column(cursor)
                updates = []
                params = []
                
                if name is not None:
                    updates.append('name = ?')
                    params.append(name.strip())
                if category is not None:
                    updates.append('category = ?')
                    params.append(category)
                if category_id is not None:
                    updates.append('category_id = ?')
                    params.append(category_id)
                if unit is not None:
                    updates.append('unit = ?')
                    params.append(unit)
                if stock_quantity is not None:
                    updates.append('stock_quantity = ?')
                    params.append(stock_quantity)
                if retail_price is not None:
                    updates.append(f'{price_column} = ?')
                    params.append(retail_price)
                if purchase_price is not None:
                    updates.append('purchase_price = ?')
                    params.append(purchase_price)
                if warranty_days is not None:
                    updates.append('warranty_days = ?')
                    params.append(warranty_days)
                if comment is not None:
                    updates.append('comment = ?')
                    params.append(comment)
                if description is not None:
                    updates.append('description = ?')
                    params.append(description)
                if min_quantity is not None:
                    updates.append('min_quantity = ?')
                    params.append(min_quantity)
                if salary_rule_type is not None:
                    updates.append('salary_rule_type = ?')
                    params.append(salary_rule_type)
                if salary_rule_value is not None:
                    updates.append('salary_rule_value = ?')
                    params.append(salary_rule_value)
                
                if not updates:
                    return False
                
                updates.append('updated_at = CURRENT_TIMESTAMP')
                params.append(part_id)
                
                query = f'''
                    UPDATE parts
                    SET {', '.join(updates)}
                    WHERE id = ? AND is_deleted = 0
                '''
                cursor.execute(query, params)
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка при обновлении товара: {e}")
            raise
    
    @staticmethod
    def delete_part(part_id: int) -> bool:
        """
        Мягкое удаление товара (устанавливает is_deleted = 1).
        
        Args:
            part_id: ID товара
            
        Returns:
            True если успешно
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE parts
                    SET is_deleted = 1, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (part_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка при удалении товара: {e}")
            raise
    
    @staticmethod
    def get_warehouse_logs(
        operation_type: Optional[str] = None,
        part_id: Optional[int] = None,
        category_id: Optional[int] = None,
        user_id: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        page: int = 1,
        per_page: int = 50
    ) -> Dict:
        """
        Получает логи операций со складом.
        
        Args:
            operation_type: Фильтр по типу операции
            part_id: Фильтр по товару
            category_id: Фильтр по категории
            user_id: Фильтр по пользователю
            date_from: Дата начала
            date_to: Дата окончания
            page: Номер страницы
            per_page: Количество элементов на странице
            
        Returns:
            Словарь с данными: items, total, page, per_page, pages
        """
        offset = (page - 1) * per_page
        where_clauses = []
        params = []
        
        if operation_type:
            where_clauses.append('wl.operation_type = ?')
            params.append(operation_type)
        
        if part_id:
            where_clauses.append('wl.part_id = ?')
            params.append(part_id)
        
        if category_id:
            where_clauses.append('wl.category_id = ?')
            params.append(category_id)
        
        if user_id:
            where_clauses.append('wl.user_id = ?')
            params.append(user_id)
        
        if date_from:
            where_clauses.append('DATE(wl.created_at) >= DATE(?)')
            params.append(date_from)
        
        if date_to:
            where_clauses.append('DATE(wl.created_at) <= DATE(?)')
            params.append(date_to)
        
        where_sql = 'WHERE ' + ' AND '.join(where_clauses) if where_clauses else ''
        
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                
                # Подсчет общего количества
                count_query = f'''
                    SELECT COUNT(*)
                    FROM warehouse_logs AS wl
                    {where_sql}
                '''
                cursor.execute(count_query, params)
                total = cursor.fetchone()[0]
                
                # Получение данных с JOIN для получения названия категории
                query = f'''
                    SELECT 
                        wl.id,
                        wl.operation_type,
                        wl.part_id,
                        wl.category_id,
                        wl.part_name,
                        wl.part_number,
                        pc.name AS category_name,
                        wl.user_id,
                        wl.username,
                        wl.quantity,
                        wl.old_value,
                        wl.new_value,
                        wl.notes,
                        wl.ip_address,
                        wl.created_at
                    FROM warehouse_logs AS wl
                    LEFT JOIN part_categories AS pc ON wl.category_id = pc.id
                    {where_sql}
                    ORDER BY wl.created_at DESC
                    LIMIT ? OFFSET ?
                '''
                params.extend([per_page, offset])
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                items = [dict(row) for row in rows]
                
                return {
                    'items': items,
                    'total': total,
                    'page': page,
                    'per_page': per_page,
                    'pages': (total + per_page - 1) // per_page if total > 0 else 0
                }
        except Exception as e:
            logger.error(f"Ошибка при получении логов склада: {e}")
            return {
                'items': [],
                'total': 0,
                'page': page,
                'per_page': per_page,
                'pages': 0
            }
    
    # ===========================================
    # ПОСТАВЩИКИ
    # ===========================================
    
    @staticmethod
    def get_all_suppliers(include_inactive: bool = False) -> List[Dict]:
        """Получает всех поставщиков."""
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                if include_inactive:
                    cursor.execute('SELECT * FROM suppliers ORDER BY name')
                else:
                    cursor.execute('SELECT * FROM suppliers WHERE is_active = 1 ORDER BY name')
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Ошибка при получении поставщиков: {e}")
            return []
    
    @staticmethod
    def get_supplier_by_id(supplier_id: int) -> Optional[Dict]:
        """Получает поставщика по ID."""
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM suppliers WHERE id = ?', (supplier_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Ошибка при получении поставщика {supplier_id}: {e}")
            return None
    
    @staticmethod
    def create_supplier(
        name: str,
        contact_person: Optional[str] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        address: Optional[str] = None,
        inn: Optional[str] = None,
        comment: Optional[str] = None
    ) -> int:
        """Создает нового поставщика."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO suppliers (name, contact_person, phone, email, address, inn, comment)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (name.strip(), contact_person, phone, email, address, inn, comment))
                conn.commit()
                return cursor.lastrowid
        except sqlite3.IntegrityError:
            raise ValueError(f"Поставщик с названием '{name}' уже существует")
        except Exception as e:
            logger.error(f"Ошибка при создании поставщика: {e}")
            raise
    
    @staticmethod
    def update_supplier(
        supplier_id: int,
        name: str,
        contact_person: Optional[str] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        address: Optional[str] = None,
        inn: Optional[str] = None,
        comment: Optional[str] = None,
        is_active: bool = True
    ) -> bool:
        """Обновляет поставщика."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE suppliers 
                    SET name = ?, contact_person = ?, phone = ?, email = ?, 
                        address = ?, inn = ?, comment = ?, is_active = ?, 
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (name.strip(), contact_person, phone, email, address, inn, comment, 1 if is_active else 0, supplier_id))
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.IntegrityError:
            raise ValueError(f"Поставщик с названием '{name}' уже существует")
        except Exception as e:
            logger.error(f"Ошибка при обновлении поставщика {supplier_id}: {e}")
            raise
    
    @staticmethod
    def delete_supplier(supplier_id: int) -> bool:
        """Удаляет поставщика (мягкое удаление)."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('UPDATE suppliers SET is_active = 0 WHERE id = ?', (supplier_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка при удалении поставщика {supplier_id}: {e}")
            raise
    
    # ===========================================
    # ИНВЕНТАРИЗАЦИЯ
    # ===========================================
    
    @staticmethod
    def get_all_inventories(
        status: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Получает все инвентаризационные ведомости."""
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                where_clauses = []
                params = []
                
                if status:
                    where_clauses.append('status = ?')
                    params.append(status)
                
                if date_from:
                    where_clauses.append('DATE(inventory_date) >= DATE(?)')
                    params.append(date_from)
                
                if date_to:
                    where_clauses.append('DATE(inventory_date) <= DATE(?)')
                    params.append(date_to)
                
                where_sql = 'WHERE ' + ' AND '.join(where_clauses) if where_clauses else ''
                
                cursor.execute(f'''
                    SELECT 
                        i.*, 
                        u.username AS created_by_username,
                        (SELECT COUNT(*) FROM inventory_items ii WHERE ii.inventory_id = i.id) AS items_count
                    FROM inventory AS i
                    LEFT JOIN users AS u ON i.created_by = u.id
                    {where_sql}
                    ORDER BY i.inventory_date DESC, i.created_at DESC
                    LIMIT ?
                ''', params + [limit])
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Ошибка при получении инвентаризаций: {e}")
            return []
    
    @staticmethod
    def get_inventory_by_id(inventory_id: int) -> Optional[Dict]:
        """Получает инвентаризацию по ID."""
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT i.*, u.username AS created_by_username
                    FROM inventory AS i
                    LEFT JOIN users AS u ON i.created_by = u.id
                    WHERE i.id = ?
                ''', (inventory_id,))
                row = cursor.fetchone()
                if row:
                    inventory = dict(row)
                    # Загружаем позиции
                    cursor.execute('''
                        SELECT ii.*, p.name AS part_name, p.part_number
                        FROM inventory_items AS ii
                        INNER JOIN parts AS p ON ii.part_id = p.id
                        WHERE ii.inventory_id = ?
                        ORDER BY p.name
                    ''', (inventory_id,))
                    items = cursor.fetchall()
                    inventory['items'] = [dict(item) for item in items]
                    return inventory
                return None
        except Exception as e:
            logger.error(f"Ошибка при получении инвентаризации {inventory_id}: {e}")
            return None
    
    @staticmethod
    def create_inventory(
        name: str,
        inventory_date: str,
        notes: Optional[str] = None,
        created_by: Optional[int] = None
    ) -> int:
        """Создает новую инвентаризационную ведомость."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO inventory (name, inventory_date, notes, created_by)
                    VALUES (?, ?, ?, ?)
                ''', (name.strip(), inventory_date, notes, created_by))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Ошибка при создании инвентаризации: {e}")
            raise
    
    @staticmethod
    def add_inventory_item(
        inventory_id: int,
        part_id: int,
        stock_quantity: int,
        actual_quantity: int,
        notes: Optional[str] = None
    ) -> int:
        """Добавляет позицию в инвентаризацию."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                difference = actual_quantity - stock_quantity
                cursor.execute('''
                    INSERT INTO inventory_items 
                    (inventory_id, part_id, stock_quantity, actual_quantity, difference, notes)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (inventory_id, part_id, stock_quantity, actual_quantity, difference, notes))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Ошибка при добавлении позиции в инвентаризацию: {e}")
            raise
    
    @staticmethod
    def update_inventory_status(
        inventory_id: int,
        status: str,
        completed_at: Optional[str] = None
    ) -> bool:
        """Обновляет статус инвентаризации."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                if completed_at:
                    cursor.execute('''
                        UPDATE inventory 
                        SET status = ?, completed_at = ?
                        WHERE id = ?
                    ''', (status, completed_at, inventory_id))
                else:
                    cursor.execute('''
                        UPDATE inventory 
                        SET status = ?
                        WHERE id = ?
                    ''', (status, inventory_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка при обновлении статуса инвентаризации {inventory_id}: {e}")
            raise
    
    @staticmethod
    def delete_inventory_item(item_id: int) -> bool:
        """Удаляет позицию из инвентаризации."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM inventory_items WHERE id = ?', (item_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка при удалении позиции инвентаризации {item_id}: {e}")
            raise
    
    @staticmethod
    def restore_part(part_id: int) -> bool:
        """
        Восстанавливает удаленный товар (устанавливает is_deleted = 0).
        
        Args:
            part_id: ID товара
            
        Returns:
            True если успешно
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE parts
                    SET is_deleted = 0, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (part_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка при восстановлении товара: {e}")
            raise

