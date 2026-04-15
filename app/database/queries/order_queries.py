"""
SQL запросы для работы с заявками.
"""
from typing import Dict, List, Optional
from app.database.connection import get_db_connection, _get_db_driver
import sqlite3
import logging

logger = logging.getLogger(__name__)


class OrderQueries:
    """Класс для SQL-запросов по заявкам."""

    @staticmethod
    def _agg_concat(expr_sql: str, separator: str = ", ") -> str:
        """
        Возвращает SQL-агрегатор конкатенации строк для текущего драйвера БД.
        SQLite: GROUP_CONCAT(expr, ', ')
        PostgreSQL: STRING_AGG(expr, ', ')
        """
        if _get_db_driver() == "postgres":
            return f"STRING_AGG({expr_sql}, '{separator}')"
        return f"GROUP_CONCAT({expr_sql}, '{separator}')"

    @staticmethod
    def _orders_not_deleted_clause(cursor, alias: str = 'o') -> str:
        """Условие исключения soft-deleted заявок (совместимо со старыми БД)."""
        try:
            cursor.execute("PRAGMA table_info(orders)")
            columns = {row[1] for row in cursor.fetchall()}
            if 'is_deleted' in columns:
                return f"({alias}.is_deleted = 0 OR {alias}.is_deleted IS NULL)"
        except Exception:
            pass
        return "1=1"

    @staticmethod
    def _table_exists(cursor, table_name: str) -> bool:
        """Проверяет существование таблицы с учетом драйвера БД."""
        try:
            if _get_db_driver() == "postgres":
                cursor.execute(
                    """
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_name = ?
                    LIMIT 1
                    """,
                    (table_name,),
                )
                return cursor.fetchone() is not None
            cursor.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
                (table_name,),
            )
            return cursor.fetchone() is not None
        except Exception:
            return False
    
    @staticmethod
    def get_orders_with_all_details(
        filters: Dict = None,
        page: int = 1,
        per_page: int = 50,
        sort_by: str = 'created_at',
        sort_order: str = 'DESC',
        pinned_user_id: Optional[int] = None,
        pins_first: bool = False,
    ) -> Dict:
        """
        Получает заявки со всеми связанными данными одним запросом (оптимизация N+1).
        
        Args:
            filters: Словарь с фильтрами:
                - status: код статуса (str)
                - status_id: ID статуса (int)
                - customer_id: ID клиента (int)
                - device_id: ID устройства (int)
                - manager_id: ID менеджера (int)
                - master_id: ID мастера (int)
                - search: поисковый запрос (str) - поиск по имени клиента, телефону, email, UUID заявки, серийному номеру, комментарию, неисправности (symptom_tags), внешнему виду (appearance), статусу, типу устройства, модели/бренду устройства, менеджеру, мастеру
                - date_from: дата начала (str, формат YYYY-MM-DD)
                - date_to: дата окончания (str, формат YYYY-MM-DD)
            page: Номер страницы
            per_page: Количество элементов на странице
            sort_by: Поле для сортировки (id, client_name, phone, device_type, device_brand, manager, status, created_at)
            sort_order: Направление сортировки (ASC, DESC)
            pinned_user_id: Не используется в глобальном режиме закрепов (оставлен для совместимости вызовов)
            pins_first: Если True, глобально закрепленные заявки идут в начале списка
            
        Returns:
            Словарь с данными: items, total, page, per_page, pages
        """
        offset = (page - 1) * per_page
        params = []
        where_clauses = ['(o.hidden = 0 OR o.hidden IS NULL)']
        
        # Маппинг полей сортировки (для DataTables и реестра заявок)
        sort_column_map = {
            'id': 'o.id',
            'client_name': 'c.name',
            'phone': 'c.phone',
            'device_type': 'dt.name',
            'device_brand': 'db.name',
            'manager': 'mgr.name',
            'master': 'ms.name',
            'status': 'os.name',
            'created_at': 'o.created_at',
            'updated_at': 'o.updated_at',
        }
        
        # Валидация и маппинг сортировки
        order_column = sort_column_map.get(sort_by, 'o.created_at')
        if order_column not in sort_column_map.values():
            order_column = 'o.created_at'
        
        if sort_order.upper() not in ['ASC', 'DESC']:
            sort_order = 'DESC'
        else:
            sort_order = sort_order.upper()
        
        if filters:
            if 'status' in filters:
                status_val = filters['status']
                if status_val == 'in_progress':
                    # Все в работе: все статусы, кроме финальных и кроме «Незабирашка»
                    where_clauses.append('(os.is_final = 0 OR os.is_final IS NULL)')
                    where_clauses.append("(LOWER(TRIM(os.name)) NOT LIKE '%незабираш%')")
                else:
                    where_clauses.append('os.code = ?')
                    params.append(status_val)
            
            if 'status_id' in filters:
                where_clauses.append('o.status_id = ?')
                params.append(filters['status_id'])
            
            if 'customer_id' in filters:
                where_clauses.append('o.customer_id = ?')
                params.append(filters['customer_id'])
            
            if 'device_id' in filters:
                where_clauses.append('o.device_id = ?')
                params.append(filters['device_id'])
            
            if 'manager_id' in filters:
                where_clauses.append('o.manager_id = ?')
                params.append(filters['manager_id'])
            
            if 'master_id' in filters:
                where_clauses.append('o.master_id = ?')
                params.append(filters['master_id'])
            
            # Поиск по нескольким полям
            if 'search' in filters and filters['search']:
                search_query = filters['search'].strip()
                if search_query:
                    # Проверяем, является ли поисковый запрос числом (для поиска по ID заявки)
                    is_numeric = False
                    order_id = None
                    try:
                        numeric_candidate = search_query.strip().replace('№', '').replace('#', '').strip()
                        order_id = int(numeric_candidate)
                        if order_id > 0:
                            is_numeric = True
                    except (ValueError, TypeError):
                        pass
                    
                    # Экранируем специальные символы для LIKE
                    def _esc(s: str) -> str:
                        return s.replace("%", "\\%").replace("_", "\\_")
                    like_q = f'%{_esc(search_query)}%'
                    
                    # Варианты телефона для поиска (8/7, последние 10 цифр) — чтобы 89881463231 находил 79881463231
                    phone_variants = [like_q]
                    digits_only = ''.join(ch for ch in search_query if ch.isdigit())
                    if len(digits_only) >= 10 and len(digits_only) <= 11:
                        if digits_only.startswith('8') and len(digits_only) == 11:
                            phone_variants.append(f'%{_esc("7" + digits_only[1:])}%')
                        elif digits_only.startswith('7') and len(digits_only) == 11:
                            phone_variants.append(f'%{_esc("8" + digits_only[1:])}%')
                        if len(digits_only) >= 10:
                            tail10 = f'%{_esc(digits_only[-10:])}%'
                            if tail10 not in phone_variants:
                                phone_variants.append(tail10)
                    phone_variants = list(dict.fromkeys(phone_variants))
                    phone_conditions = [f'c.phone LIKE ?' for _ in phone_variants]
                    
                    # Формируем условие поиска
                    search_conditions = []
                    search_params = []
                    
                    # Если это число, добавляем точный поиск по ID заявки
                    if is_numeric:
                        search_conditions.append('o.id = ?')
                        search_params.append(order_id)
                    
                    # Добавляем LIKE поиск по остальным полям
                    like_conditions = [
                        'c.name LIKE ?',
                        '(' + ' OR '.join(phone_conditions) + ')',
                        'c.email LIKE ?',
                        'o.order_id LIKE ?',
                        'd.serial_number LIKE ?',
                        'o.comment LIKE ?',
                        'o.symptom_tags LIKE ?',
                        'EXISTS(SELECT 1 FROM order_symptoms osymp JOIN symptoms s ON s.id = osymp.symptom_id WHERE osymp.order_id = o.id AND s.name LIKE ?)',
                        'o.appearance LIKE ?',
                        'EXISTS(SELECT 1 FROM order_appearance_tags oat JOIN appearance_tags at ON at.id = oat.appearance_tag_id WHERE oat.order_id = o.id AND at.name LIKE ?)',
                        'os.name LIKE ?',
                        'os.code LIKE ?',
                        'dt.name LIKE ?',
                        'db.name LIKE ?',
                        'om.name LIKE ?',
                        'mgr.name LIKE ?',
                        'ms.name LIKE ?'
                    ]
                    search_conditions.extend(like_conditions)
                    for i, cond in enumerate(like_conditions):
                        if 'c.phone' in cond:
                            search_params.extend(phone_variants)
                        else:
                            search_params.append(like_q)
                    
                    where_clauses.append('(' + ' OR '.join(search_conditions) + ')')
                    params.extend(search_params)
            
            # Фильтр по датам
            if 'date_from' in filters and filters['date_from']:
                where_clauses.append("DATE(o.created_at) >= DATE(?)")
                params.append(filters['date_from'])
            
            if 'date_to' in filters and filters['date_to']:
                where_clauses.append("DATE(o.created_at) <= DATE(?)")
                params.append(filters['date_to'])
        
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                where_clauses.append(OrderQueries._orders_not_deleted_clause(cursor, 'o'))
                where_sql = 'WHERE ' + ' AND '.join(where_clauses)
                
                # Глобальные закрепления заявок (общие для всех пользователей)
                pins_select = "0 AS is_pinned"
                pins_join = ""
                pins_order_prefix = ""
                query_params = list(params)
                if OrderQueries._table_exists(cursor, "order_pins"):
                    pins_select = (
                        "CASE WHEN EXISTS("
                        "SELECT 1 FROM order_pins AS op WHERE op.order_id = o.id"
                        ") THEN 1 ELSE 0 END AS is_pinned"
                    )
                    pins_order_prefix = (
                        "CASE WHEN EXISTS(SELECT 1 FROM order_pins AS op WHERE op.order_id = o.id) "
                        "THEN 1 ELSE 0 END DESC, "
                        if pins_first else ""
                    )

                # Один большой JOIN вместо множественных запросов
                # Используем нормализованные таблицы, но оставляем старые поля для обратной совместимости
                appearance_agg = OrderQueries._agg_concat("at.name", ", ")
                symptoms_agg = OrderQueries._agg_concat("s.name", ", ")
                query = f'''
                    SELECT 
                        o.id,
                        o.order_id,
                        o.customer_id,
                        o.device_id,
                        o.manager_id,
                        o.master_id,
                        o.status_id,
                        COALESCE(os.code, o.status) AS status,
                        COALESCE(os.name, o.status) AS status_name,
                        COALESCE(os.color, '#6c757d') AS status_color,
                        o.comment,
                        o.prepayment,
                        o.prepayment_cents,
                        -- Нормализованные данные (приоритет)
                        COALESCE(
                            (SELECT {appearance_agg}
                             FROM order_appearance_tags oat 
                             JOIN appearance_tags at ON at.id = oat.appearance_tag_id 
                             WHERE oat.order_id = o.id),
                            o.appearance
                        ) AS appearance,
                        COALESCE(
                            (SELECT {symptoms_agg}
                             FROM order_symptoms osymp 
                             JOIN symptoms s ON s.id = osymp.symptom_id 
                             WHERE osymp.order_id = o.id),
                            o.symptom_tags
                        ) AS symptom_tags,
                        COALESCE(om.name, o.model) AS model,
                        o.model_id,
                        o.created_at,
                        o.updated_at,
                        c.name AS client_name,
                        c.phone,
                        c.email,
                        d.serial_number,
                        COALESCE(dt.name, '—') AS device_type,
                        COALESCE(db.name, '—') AS device_brand,
                        COALESCE(mgr.name, '—') AS manager_name,
                        COALESCE(mgr.name, '—') AS manager,
                        COALESCE(ms.name, '—') AS master_name,
                        COALESCE(ms.name, '—') AS master,
                        {pins_select},
                        o.hidden,
                        (SELECT COUNT(*) FROM order_comments WHERE order_id = o.id) AS comments_count,
                        (SELECT COALESCE(SUM(amount), 0) FROM payments WHERE order_id = o.id) AS total_paid
                    FROM orders AS o
                    JOIN customers AS c ON c.id = o.customer_id
                    LEFT JOIN devices AS d ON d.id = o.device_id
                    LEFT JOIN device_types AS dt ON dt.id = d.device_type_id
                    LEFT JOIN device_brands AS db ON db.id = d.device_brand_id
                    LEFT JOIN order_statuses AS os ON os.id = o.status_id
                    LEFT JOIN managers AS mgr ON mgr.id = o.manager_id
                    LEFT JOIN masters AS ms ON ms.id = o.master_id
                    LEFT JOIN order_models AS om ON om.id = o.model_id
                    {pins_join}
                    {where_sql}
                    ORDER BY {pins_order_prefix}{order_column} {sort_order}
                    LIMIT ? OFFSET ?
                '''
                
                query_params.extend([per_page, offset])
                cursor.execute(query, query_params)
                rows = cursor.fetchall()
                
                # Подсчет общего количества (нужны те же JOIN'ы, что и в основном запросе)
                count_query = f'''
                    SELECT COUNT(*) 
                    FROM orders AS o
                    JOIN customers AS c ON c.id = o.customer_id
                    LEFT JOIN devices AS d ON d.id = o.device_id
                    LEFT JOIN device_types AS dt ON dt.id = d.device_type_id
                    LEFT JOIN device_brands AS db ON db.id = d.device_brand_id
                    LEFT JOIN order_statuses AS os ON os.id = o.status_id
                    LEFT JOIN managers AS mgr ON mgr.id = o.manager_id
                    LEFT JOIN masters AS ms ON ms.id = o.master_id
                    LEFT JOIN order_models AS om ON om.id = o.model_id
                    {where_sql}
                '''
                cursor.execute(count_query, params[:-2])  # Убираем LIMIT и OFFSET
                total = cursor.fetchone()[0]
                
                return {
                    'items': [dict(row) for row in rows],
                    'total': total,
                    'page': page,
                    'per_page': per_page,
                    'pages': (total + per_page - 1) // per_page if total > 0 else 0
                }
        except Exception as e:
            logger.error(f"Ошибка при получении заявок: {e}")
            return {
                'items': [],
                'total': 0,
                'page': page,
                'per_page': per_page,
                'pages': 0
            }
    
    @staticmethod
    def get_order_totals(order_id: int) -> Dict[str, float]:
        """
        Получает все суммы по заявке одним запросом.
        
        Args:
            order_id: ID заявки
            
        Returns:
            Словарь с суммами: services_total, parts_total, prepayment, total, paid, debt
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()

                # Определяем, есть ли новые колонки в payments (027 миграция)
                cursor.execute("PRAGMA table_info(payments)")
                pay_cols = [r[1] for r in cursor.fetchall()]
                has_kind = "kind" in pay_cols
                has_status = "status" in pay_cols

                # Суммы по услугам/товарам
                cursor.execute(
                    """
                    SELECT
                        (SELECT COALESCE(SUM(price * quantity), 0) FROM order_services WHERE order_id = ?) AS services_total,
                        (SELECT COALESCE(SUM(price * quantity), 0) FROM order_parts WHERE order_id = ?) AS parts_total
                    """,
                    (order_id, order_id),
                )
                row = cursor.fetchone()
                services_total = float(row[0] or 0)
                parts_total = float(row[1] or 0)
                total = services_total + parts_total

                # Оплаты: считаем net (refund уменьшает paid)
                # Для новых схем: kind='refund' учитываем со знаком минус.
                if has_kind:
                    if has_status:
                        cursor.execute(
                            """
                            SELECT
                                COALESCE(SUM(
                                    CASE WHEN kind = 'refund' THEN -amount ELSE amount END
                                ), 0) AS paid_total
                            FROM payments
                            WHERE order_id = ?
                              AND (is_cancelled = 0 OR is_cancelled IS NULL)
                              AND status = 'captured'
                            """,
                            (order_id,),
                        )
                    else:
                        cursor.execute(
                            """
                            SELECT
                                COALESCE(SUM(
                                    CASE WHEN kind = 'refund' THEN -amount ELSE amount END
                                ), 0) AS paid_total
                            FROM payments
                            WHERE order_id = ?
                              AND (is_cancelled = 0 OR is_cancelled IS NULL)
                            """,
                            (order_id,),
                        )
                else:
                    # Legacy: без kind, считаем всё как оплату
                    if has_status:
                        cursor.execute(
                            """
                            SELECT COALESCE(SUM(amount), 0)
                            FROM payments
                            WHERE order_id = ?
                              AND (is_cancelled = 0 OR is_cancelled IS NULL)
                              AND status = 'captured'
                            """,
                            (order_id,),
                        )
                    else:
                        cursor.execute(
                            """
                            SELECT COALESCE(SUM(amount), 0)
                            FROM payments
                            WHERE order_id = ?
                              AND (is_cancelled = 0 OR is_cancelled IS NULL)
                            """,
                            (order_id,),
                        )
                paid = float((cursor.fetchone() or [0])[0] or 0)

                # Предоплата как часть payments(kind='deposit') — для отображения в UI
                prepayment = 0.0
                if has_kind:
                    if has_status:
                        cursor.execute(
                            """
                            SELECT COALESCE(SUM(amount), 0)
                            FROM payments
                            WHERE order_id = ?
                              AND kind = 'deposit'
                              AND (is_cancelled = 0 OR is_cancelled IS NULL)
                              AND status = 'captured'
                            """,
                            (order_id,),
                        )
                    else:
                        cursor.execute(
                            """
                            SELECT COALESCE(SUM(amount), 0)
                            FROM payments
                            WHERE order_id = ?
                              AND kind = 'deposit'
                              AND (is_cancelled = 0 OR is_cancelled IS NULL)
                            """,
                            (order_id,),
                        )
                    prepayment = float((cursor.fetchone() or [0])[0] or 0)

                # Долг/переплата: считаем от total и paid (предоплата уже входит в paid)
                debt = total - paid
                overpayment = 0.0
                if debt < 0:
                    overpayment = -debt
                    debt = 0.0

                return {
                    "services_total": services_total,
                    "parts_total": parts_total,
                    "prepayment": prepayment,
                    "total": total,
                    "paid": paid,
                    "debt": debt,
                    "overpayment": overpayment,
                }
        except Exception as e:
            logger.error(f"Ошибка при получении сумм заявки {order_id}: {e}")
            return {
                'services_total': 0.0,
                'parts_total': 0.0,
                'prepayment': 0.0,
                'total': 0.0,
                'paid': 0.0,
                'debt': 0.0
            }

    @staticmethod
    def get_orders_totals_batch(order_ids: List[int]) -> Dict[int, Dict[str, float]]:
        """
        Получает суммы по списку заявок одним набором запросов (как get_order_totals).
        
        Args:
            order_ids: Список ID заявок
            
        Returns:
            Словарь { order_id: { services_total, parts_total, total, paid, debt, prepayment } }
        """
        if not order_ids:
            return {}
        default = {
            'services_total': 0.0, 'parts_total': 0.0, 'total': 0.0,
            'paid': 0.0, 'debt': 0.0, 'prepayment': 0.0
        }
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(payments)")
                pay_cols = [r[1] for r in cursor.fetchall()]
                has_kind = "kind" in pay_cols
                has_status = "status" in pay_cols

                placeholders = ','.join('?' * len(order_ids))

                # Суммы по услугам и запчастям по заявкам
                cursor.execute(
                    f"""
                    SELECT order_id,
                        COALESCE(SUM(price * quantity), 0) AS s_total
                    FROM order_services
                    WHERE order_id IN ({placeholders})
                    GROUP BY order_id
                    """,
                    order_ids,
                )
                services_by_id = {row[0]: float(row[1] or 0) for row in cursor.fetchall()}

                cursor.execute(
                    f"""
                    SELECT order_id,
                        COALESCE(SUM(price * quantity), 0) AS p_total
                    FROM order_parts
                    WHERE order_id IN ({placeholders})
                    GROUP BY order_id
                    """,
                    order_ids,
                )
                parts_by_id = {row[0]: float(row[1] or 0) for row in cursor.fetchall()}

                # Оплаты (net: refund со знаком минус)
                if has_kind:
                    if has_status:
                        cursor.execute(
                            f"""
                            SELECT order_id,
                                COALESCE(SUM(CASE WHEN kind = 'refund' THEN -amount ELSE amount END), 0) AS paid_total
                            FROM payments
                            WHERE order_id IN ({placeholders})
                              AND (is_cancelled = 0 OR is_cancelled IS NULL)
                              AND status = 'captured'
                            GROUP BY order_id
                            """,
                            order_ids,
                        )
                    else:
                        cursor.execute(
                            f"""
                            SELECT order_id,
                                COALESCE(SUM(CASE WHEN kind = 'refund' THEN -amount ELSE amount END), 0) AS paid_total
                            FROM payments
                            WHERE order_id IN ({placeholders})
                              AND (is_cancelled = 0 OR is_cancelled IS NULL)
                            GROUP BY order_id
                            """,
                            order_ids,
                        )
                else:
                    if has_status:
                        cursor.execute(
                            f"""
                            SELECT order_id, COALESCE(SUM(amount), 0) AS paid_total
                            FROM payments
                            WHERE order_id IN ({placeholders})
                              AND (is_cancelled = 0 OR is_cancelled IS NULL)
                              AND status = 'captured'
                            GROUP BY order_id
                            """,
                            order_ids,
                        )
                    else:
                        cursor.execute(
                            f"""
                            SELECT order_id, COALESCE(SUM(amount), 0) AS paid_total
                            FROM payments
                            WHERE order_id IN ({placeholders})
                              AND (is_cancelled = 0 OR is_cancelled IS NULL)
                            GROUP BY order_id
                            """,
                            order_ids,
                        )
                paid_by_id = {row[0]: float(row[1] or 0) for row in cursor.fetchall()}

                # Предоплата (kind='deposit')
                prepayment_by_id = {}
                if has_kind:
                    if has_status:
                        cursor.execute(
                            f"""
                            SELECT order_id, COALESCE(SUM(amount), 0) AS prep_total
                            FROM payments
                            WHERE order_id IN ({placeholders})
                              AND kind = 'deposit'
                              AND (is_cancelled = 0 OR is_cancelled IS NULL)
                              AND status = 'captured'
                            GROUP BY order_id
                            """,
                            order_ids,
                        )
                    else:
                        cursor.execute(
                            f"""
                            SELECT order_id, COALESCE(SUM(amount), 0) AS prep_total
                            FROM payments
                            WHERE order_id IN ({placeholders})
                              AND kind = 'deposit'
                              AND (is_cancelled = 0 OR is_cancelled IS NULL)
                            GROUP BY order_id
                            """,
                            order_ids,
                        )
                    prepayment_by_id = {row[0]: float(row[1] or 0) for row in cursor.fetchall()}

                result = {}
                for oid in order_ids:
                    st = services_by_id.get(oid, 0.0)
                    pt = parts_by_id.get(oid, 0.0)
                    total = st + pt
                    paid = paid_by_id.get(oid, 0.0)
                    prepayment = prepayment_by_id.get(oid, 0.0)
                    debt = total - paid
                    if debt < 0:
                        debt = 0.0
                    result[oid] = {
                        'services_total': st,
                        'parts_total': pt,
                        'total': total,
                        'paid': paid,
                        'debt': debt,
                        'prepayment': prepayment,
                    }
                return result
        except Exception as e:
            logger.error(f"Ошибка при получении сумм по заявкам (batch): {e}", exc_info=True)
            return {oid: dict(default) for oid in order_ids}

    @staticmethod
    def get_order_services(order_id: int) -> List[Dict]:
        """
        Получает услуги заявки.
        
        Args:
            order_id: ID заявки
            
        Returns:
            Список услуг
        """
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT 
                        os.*,
                        COALESCE(os.name, s.name) AS service_name,
                        COALESCE(s.price, os.price) AS service_price,
                        COALESCE(u.display_name, u.username) AS executor_username,
                        u.id AS executor_user_id
                    FROM order_services os
                    LEFT JOIN services s ON s.id = os.service_id
                    LEFT JOIN users u ON u.id = os.executor_id
                    WHERE os.order_id = ?
                    ORDER BY os.created_at
                ''', (order_id,))
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Ошибка при получении услуг заявки {order_id}: {e}")
            return []
    
    @staticmethod
    def get_order_parts(order_id: int) -> List[Dict]:
        """
        Получает запчасти заявки.

        Args:
            order_id: ID заявки
            
        Returns:
            Список запчастей
        """
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT
                        op.id,
                        op.order_id,
                        op.part_id,
                        op.name,
                        op.quantity,
                        op.price,
                        op.purchase_price,
                        op.base_price,
                        op.discount_type,
                        op.discount_value,
                        op.warranty_days,
                        op.executor_id,
                        op.created_at,
                        COALESCE(op.name, p.name) AS part_name,
                        COALESCE(p.part_number, '') AS part_number,
                        COALESCE(p.category, '') AS category,
                        COALESCE(p.stock_quantity, 0) AS stock_quantity,
                        COALESCE(u.display_name, u.username) AS executor_username,
                        u.id AS executor_user_id
                    FROM order_parts AS op
                    LEFT JOIN parts AS p ON p.id = op.part_id
                    LEFT JOIN users u ON u.id = op.executor_id
                    WHERE op.order_id = ?
                    ORDER BY op.created_at ASC, op.id ASC
                ''', (order_id,))
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Ошибка при получении запчастей заявки {order_id}: {e}")
            return []
    
    @staticmethod
    def get_order_payments(order_id: int) -> List[Dict]:
        """
        Получает оплаты заявки.
        
        Args:
            order_id: ID заявки
            
        Returns:
            Список оплат
        """
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM payments
                    WHERE order_id = ?
                    ORDER BY payment_date DESC, created_at DESC
                ''', (order_id,))
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Ошибка при получении оплат заявки {order_id}: {e}")
            return []
    
    @staticmethod
    def get_order_full_details(order_id: int) -> Optional[Dict]:
        """
        Получает полные данные заявки со всеми связанными данными одним запросом.
        
        Args:
            order_id: ID заявки
            
        Returns:
            Словарь с полными данными заявки или None
        """
        try:
            with get_db_connection(row_factory=sqlite3.Row) as conn:
                cursor = conn.cursor()
                
                # Основные данные заявки (используем LEFT JOIN для customers и devices)
                # Используем нормализованные данные с fallback на старые поля
                not_deleted_clause = OrderQueries._orders_not_deleted_clause(cursor, 'o')
                symptoms_agg = OrderQueries._agg_concat("s.name", ", ")
                appearance_agg = OrderQueries._agg_concat("at.name", ", ")
                cursor.execute(f'''
                    SELECT 
                        o.*,
                        COALESCE(om.name, o.model) AS model,
                        COALESCE(
                            (SELECT {symptoms_agg}
                             FROM order_symptoms osymp 
                             JOIN symptoms s ON s.id = osymp.symptom_id 
                             WHERE osymp.order_id = o.id),
                            o.symptom_tags
                        ) AS symptom_tags,
                        COALESCE(
                            (SELECT {appearance_agg}
                             FROM order_appearance_tags oat 
                             JOIN appearance_tags at ON at.id = oat.appearance_tag_id 
                             WHERE oat.order_id = o.id),
                            o.appearance
                        ) AS appearance,
                        c.name AS customer_name,
                        c.phone AS customer_phone,
                        c.email AS customer_email,
                        d.serial_number,
                        d.device_type_id,
                        d.device_brand_id,
                        dt.name AS device_type_name,
                        db.name AS device_brand_name,
                        mgr.name AS manager_name,
                        ms.name AS master_name,
                        os.name AS status_name,
                        os.color AS status_color,
                        os.code AS status_code
                    FROM orders AS o
                    LEFT JOIN customers AS c ON c.id = o.customer_id
                    LEFT JOIN devices AS d ON d.id = o.device_id
                    LEFT JOIN device_types AS dt ON dt.id = d.device_type_id
                    LEFT JOIN device_brands AS db ON db.id = d.device_brand_id
                    LEFT JOIN order_models AS om ON om.id = o.model_id
                    LEFT JOIN managers AS mgr ON mgr.id = o.manager_id
                    LEFT JOIN masters AS ms ON ms.id = o.master_id
                    LEFT JOIN order_statuses AS os ON os.id = o.status_id
                    WHERE o.id = ?
                      AND {not_deleted_clause}
                ''', (order_id,))
                
                order_row = cursor.fetchone()
                if not order_row:
                    return None
                
                order_data = dict(order_row)
                
                # Получаем суммы
                totals = OrderQueries.get_order_totals(order_id)
                order_data.update(totals)
                
                return order_data
        except Exception as e:
            logger.error(f"Ошибка при получении полных данных заявки {order_id}: {e}")
            return None

