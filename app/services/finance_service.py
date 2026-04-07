"""
Сервис для финансового модуля.
Обработка статей доходов/расходов, кассовых операций и продаж в магазине.
"""
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, date, timedelta
from app.database.connection import get_db_connection
from app.utils.error_handlers import handle_service_error
from app.utils.datetime_utils import get_moscow_now, get_moscow_now_str
from app.utils.exceptions import ValidationError, NotFoundError
from app.services.action_log_service import ActionLogService
import logging
import sqlite3
import re

logger = logging.getLogger(__name__)


class FinanceService:
    """Сервис для работы с финансами."""
    
    # ===========================================
    # СТАТЬИ ДОХОДОВ/РАСХОДОВ
    # ===========================================
    
    @staticmethod
    @handle_service_error
    def get_transaction_categories(
        category_type: Optional[str] = None,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """Получить список категорий транзакций."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM transaction_categories WHERE 1=1"
            params = []
            
            if category_type:
                query += " AND type = ?"
                params.append(category_type)
            
            if active_only:
                query += " AND is_active = 1"
            
            query += " ORDER BY type, sort_order, name"
            
            cursor.execute(query, params)
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    @staticmethod
    @handle_service_error
    def get_income_categories() -> List[Dict[str, Any]]:
        """Получить категории доходов."""
        return FinanceService.get_transaction_categories(category_type='income')
    
    @staticmethod
    @handle_service_error
    def get_expense_categories() -> List[Dict[str, Any]]:
        """Получить категории расходов."""
        return FinanceService.get_transaction_categories(category_type='expense')
    
    @staticmethod
    @handle_service_error
    def create_transaction_category(
        name: str,
        category_type: str,
        description: Optional[str] = None,
        color: str = '#6c757d'
    ) -> int:
        """Создать новую категорию транзакций."""
        from app.utils.exceptions import ValidationError
        import sqlite3
        
        # Проверка на дубликаты
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, name FROM transaction_categories 
                WHERE name = ? AND type = ?
                LIMIT 1
            ''', (name.strip(), category_type))
            existing = cursor.fetchone()
            if existing:
                raise ValidationError(
                    f"Категория транзакций с названием «{name.strip()}» и типом «{category_type}» уже существует "
                    f"(ID: {existing[0]}). Используйте существующую категорию или измените название."
                )
            
            # Получить максимальный sort_order для данного типа
            cursor.execute(
                "SELECT MAX(sort_order) FROM transaction_categories WHERE type = ?",
                (category_type,)
            )
            max_order = cursor.fetchone()[0] or 0
            
            try:
                cursor.execute('''
                    INSERT INTO transaction_categories (name, type, description, color, sort_order)
                    VALUES (?, ?, ?, ?, ?)
                ''', (name.strip(), category_type, description, color, max_order + 1))

                category_id = cursor.lastrowid
                conn.commit()

                # Логируем создание категории
                try:
                    from flask_login import current_user
                    current_user_id = None
                    current_username = None
                    try:
                        if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
                            current_user_id = current_user.id
                            current_username = current_user.username
                    except Exception:
                        pass

                    ActionLogService.log_action(
                        user_id=current_user_id,
                        username=current_username,
                        action_type='create',
                        entity_type='transaction_category',
                        entity_id=category_id,
                        description=f'Создана категория транзакций: {name.strip()} ({category_type})',
                        details={
                            'name': name.strip(),
                            'type': category_type,
                            'description': description,
                            'color': color
                        }
                    )
                except Exception as e:
                    logger.warning(f"Не удалось залогировать создание категории транзакций {category_id}: {e}")

                return category_id
            except sqlite3.IntegrityError as e:
                error_msg = str(e)
                if 'UNIQUE constraint failed' in error_msg or 'unique constraint' in error_msg.lower():
                    raise ValidationError(
                        f"Категория транзакций с названием «{name.strip()}» и типом «{category_type}» уже существует. "
                        f"Используйте существующую категорию или измените название."
                    )
                raise
    
    @staticmethod
    @handle_service_error
    def update_transaction_category(
        category_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        color: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> bool:
        """Обновить категорию транзакций."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            updates = []
            params = []
            
            if name is not None:
                updates.append("name = ?")
                params.append(name)
            if description is not None:
                updates.append("description = ?")
                params.append(description)
            if color is not None:
                updates.append("color = ?")
                params.append(color)
            if is_active is not None:
                updates.append("is_active = ?")
                params.append(1 if is_active else 0)
            
            if not updates:
                return False
            
            params.append(category_id)
            cursor.execute(
                f"UPDATE transaction_categories SET {', '.join(updates)} WHERE id = ?",
                params
            )
            success = cursor.rowcount > 0
            conn.commit()

            if success:
                # Логируем обновление категории
                try:
                    from flask_login import current_user
                    current_user_id = None
                    current_username = None
                    try:
                        if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
                            current_user_id = current_user.id
                            current_username = current_user.username
                    except Exception:
                        pass

                    ActionLogService.log_action(
                        user_id=current_user_id,
                        username=current_username,
                        action_type='update',
                        entity_type='transaction_category',
                        entity_id=category_id,
                        description=f'Обновлена категория транзакций (ID: {category_id})',
                        details={
                            'updates': dict(zip([u.split('=')[0].strip() for u in updates], params[:-1]))
                        }
                    )
                except Exception as e:
                    logger.warning(f"Не удалось залогировать обновление категории транзакций {category_id}: {e}")

            return success
    
    @staticmethod
    @handle_service_error
    def delete_transaction_category(category_id: int) -> Tuple[bool, str]:
        """Удалить категорию транзакций."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Проверить, системная ли категория
            cursor.execute(
                "SELECT is_system FROM transaction_categories WHERE id = ?",
                (category_id,)
            )
            row = cursor.fetchone()
            if not row:
                return False, "Категория не найдена"
            if row[0]:
                return False, "Системную категорию нельзя удалить"
            
            # Проверить использование
            cursor.execute(
                "SELECT COUNT(*) FROM cash_transactions WHERE category_id = ?",
                (category_id,)
            )
            count = cursor.fetchone()[0]
            if count > 0:
                return False, f"Категория используется в {count} транзакциях"
            
            # Получить данные категории перед удалением для лога
            cursor.execute(
                "SELECT name, type FROM transaction_categories WHERE id = ?",
                (category_id,)
            )
            category_data = cursor.fetchone()
            category_name = category_data[0] if category_data else "Неизвестная"
            category_type = category_data[1] if category_data else "неизвестный"

            cursor.execute(
                "DELETE FROM transaction_categories WHERE id = ?",
                (category_id,)
            )
            conn.commit()

            # Логируем удаление категории
            try:
                from flask_login import current_user
                current_user_id = None
                current_username = None
                try:
                    if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
                        current_user_id = current_user.id
                        current_username = current_user.username
                except Exception:
                    pass

                ActionLogService.log_action(
                    user_id=current_user_id,
                    username=current_username,
                    action_type='delete',
                    entity_type='transaction_category',
                    entity_id=category_id,
                    description=f'Удалена категория транзакций: {category_name} ({category_type})',
                    details={
                        'name': category_name,
                        'type': category_type
                    }
                )
            except Exception as e:
                logger.warning(f"Не удалось залогировать удаление категории транзакций {category_id}: {e}")

            return True, "Категория удалена"
    
    # ===========================================
    # КАССОВЫЕ ОПЕРАЦИИ
    # ===========================================
    
    @staticmethod
    @handle_service_error
    def create_transaction(
        amount: float,
        transaction_type: str,
        category_id: Optional[int] = None,
        category_name: Optional[str] = None,
        payment_method: str = 'cash',
        description: Optional[str] = None,
        order_id: Optional[int] = None,
        payment_id: Optional[int] = None,
        shop_sale_id: Optional[int] = None,
        transaction_date: Optional[str] = None,
        created_by_id: Optional[int] = None,
        created_by_username: Optional[str] = None,
        storno_of_id: Optional[int] = None,
        skip_balance_check: bool = False,
    ) -> int:
        """Создать кассовую операцию. skip_balance_check=True — не проверять остаток (для зарплаты/дозаполнения)."""
        from app.utils.exceptions import ValidationError

        with get_db_connection() as conn:
            cursor = conn.cursor()

            # --- Validation & normalization ---
            # category_id или category_name (для обратной совместимости / удобства сервисов)
            if not category_id:
                if category_name:
                    cursor.execute(
                        """
                        SELECT id FROM transaction_categories
                        WHERE name = ? AND type = ? AND is_active = 1
                        LIMIT 1
                        """,
                        (category_name.strip(), transaction_type),
                    )
                    row = cursor.fetchone()
                    if not row:
                        # Автосоздание системной категории (для внутреннего использования сервисов)
                        # Это важно, когда миграции уже были применены, а категория добавилась позже в коде.
                        cursor.execute(
                            """
                            INSERT INTO transaction_categories (name, type, description, color, is_system, is_active, sort_order)
                            VALUES (?, ?, ?, '#6c757d', 1, 1, 999)
                            """,
                            (category_name.strip(), transaction_type, f"Системная категория: {category_name.strip()}"),
                        )
                        conn.commit()
                        category_id = int(cursor.lastrowid)
                    else:
                        category_id = int(row[0])
                else:
                    raise ValidationError("Выберите статью")

            try:
                amount = float(amount)
            except Exception:
                raise ValidationError("Неверная сумма")
            if amount <= 0:
                raise ValidationError("Сумма должна быть больше нуля")

            if transaction_type not in ('income', 'expense'):
                raise ValidationError("Неверный тип операции")

            allowed_methods = {'cash', 'card', 'transfer', 'other'}
            try:
                from app.services.settings_service import SettingsService
                custom_methods = SettingsService.get_payment_method_settings().get('custom_methods', []) or []
                allowed_methods.update({str(m).strip() for m in custom_methods if str(m).strip()})
            except Exception:
                pass
            if payment_method not in allowed_methods:
                raise ValidationError("Неверный способ оплаты")

            # Нормализуем дату: принимаем date/datetime/ISO-string, сохраняем YYYY-MM-DD
            if not transaction_date:
                transaction_date = get_moscow_now().date().isoformat()
            elif isinstance(transaction_date, datetime):
                transaction_date = transaction_date.date().isoformat()
            elif isinstance(transaction_date, date):
                transaction_date = transaction_date.isoformat()
            elif isinstance(transaction_date, str):
                raw_date = transaction_date.strip()
                if re.match(r'^\d{4}-\d{2}-\d{2}$', raw_date):
                    transaction_date = raw_date
                elif len(raw_date) >= 10 and re.match(r'^\d{4}-\d{2}-\d{2}', raw_date[:10]):
                    # Поддержка datetime-строк вида 2026-03-30T20:12:29 / 2026-03-30 20:12:29
                    transaction_date = raw_date[:10]
                else:
                    try:
                        parsed = datetime.fromisoformat(raw_date.replace('Z', '+00:00'))
                        transaction_date = parsed.date().isoformat()
                    except Exception:
                        raise ValidationError("Неверная дата операции (ожидается YYYY-MM-DD)")
            else:
                raise ValidationError("Неверная дата операции (ожидается YYYY-MM-DD)")

            if not re.match(r'^\d{4}-\d{2}-\d{2}$', transaction_date):
                raise ValidationError("Неверная дата операции (ожидается YYYY-MM-DD)")

            # Для ручных операций (не привязанных к оплате/заявке/продаже) описание обязательно
            is_manual = not order_id and not payment_id and not shop_sale_id
            if description is None:
                description = ""
            if isinstance(description, str):
                description = description.strip()
            if is_manual and not description:
                raise ValidationError("Укажите описание (для ручной операции)")

            # Для ручных расходов Наличные/Перевод: не больше доступного остатка по этому способу
            # на выбранную дату (входящий остаток до этого дня + приход за день − расход за день),
            # в т.ч. перенос наличных с прошлых дней — как в карточке «Остаток на конец периода» за один день.
            if (
                not skip_balance_check
                and is_manual
                and transaction_type == 'expense'
                and payment_method in ('cash', 'transfer')
            ):
                cursor.execute("PRAGMA table_info(cash_transactions)")
                cols = [c[1] for c in cursor.fetchall()]
                has_is_cancelled = 'is_cancelled' in cols
                has_storno_of_id = 'storno_of_id' in cols
                extra = []
                if has_is_cancelled:
                    extra.append("(is_cancelled IS NULL OR is_cancelled = 0)")
                if has_storno_of_id:
                    extra.append("(storno_of_id IS NULL OR storno_of_id = 0)")
                    extra.append(
                        "id NOT IN (SELECT storno_of_id FROM cash_transactions "
                        "WHERE storno_of_id IS NOT NULL AND storno_of_id != 0)"
                    )
                where_extra = " AND " + " AND ".join(extra) if extra else ""
                pm_match = "COALESCE(payment_method, 'cash') = ?"

                cursor.execute(
                    f"""
                    SELECT
                        COALESCE(SUM(CASE WHEN transaction_type = 'income' THEN amount ELSE 0 END), 0) -
                        COALESCE(SUM(CASE WHEN transaction_type = 'expense' THEN amount ELSE 0 END), 0)
                    FROM cash_transactions
                    WHERE {pm_match}
                      AND DATE(transaction_date) < DATE(?)
                      {where_extra}
                    """,
                    (payment_method, transaction_date),
                )
                row = cursor.fetchone()
                opening_m = float(row[0] or 0) if row else 0.0

                cursor.execute(
                    f"""
                    SELECT
                        COALESCE(SUM(CASE WHEN transaction_type = 'income' THEN amount ELSE 0 END), 0) -
                        COALESCE(SUM(CASE WHEN transaction_type = 'expense' THEN amount ELSE 0 END), 0)
                    FROM cash_transactions
                    WHERE {pm_match}
                      AND DATE(transaction_date) = DATE(?)
                      {where_extra}
                    """,
                    (payment_method, transaction_date),
                )
                row = cursor.fetchone()
                today_net = float(row[0] or 0) if row else 0.0

                available = opening_m + today_net
                if amount - available > 0.0001:
                    raise ValidationError(
                        f"Недостаточно средств по способу оплаты. "
                        f"Доступно: {available:.2f} ₽ (остаток на начало дня и движение за день), "
                        f"попытка списать: {amount:.2f} ₽"
                    )

            # Проверяем, что категория существует и активна
            cursor.execute(
                "SELECT id FROM transaction_categories WHERE id = ? AND is_active = 1",
                (category_id,)
            )
            if not cursor.fetchone():
                raise ValidationError("Выбранная статья не найдена или неактивна")

            # Защита от дубля: если транзакция привязана к payment_id — не создаем повторно
            if payment_id:
                cursor.execute(
                    "SELECT id FROM cash_transactions WHERE payment_id = ? LIMIT 1",
                    (payment_id,)
                )
                existing = cursor.fetchone()
                if existing:
                    return int(existing[0])
            
            # Защита от дубля по shop_sale_id
            if shop_sale_id:
                cursor.execute(
                    "SELECT id FROM cash_transactions WHERE shop_sale_id = ? LIMIT 1",
                    (shop_sale_id,)
                )
                existing = cursor.fetchone()
                if existing:
                    return int(existing[0])
            
            cursor.execute('''
                INSERT INTO cash_transactions (
                    category_id, amount, transaction_type, payment_method, description,
                    order_id, payment_id, shop_sale_id, transaction_date,
                    created_by_id, created_by_username, storno_of_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                category_id, amount, transaction_type, payment_method, description,
                order_id, payment_id, shop_sale_id, transaction_date,
                created_by_id, created_by_username, storno_of_id
            ))
            
            conn.commit()
            transaction_id = cursor.lastrowid
            
            # Логируем создание кассовой операции
            try:
                from app.services.action_log_service import ActionLogService
                transaction_type_name = 'приход' if transaction_type == 'income' else 'расход'
                ActionLogService.log_action(
                    user_id=created_by_id,
                    username=created_by_username,
                    action_type='create',
                    entity_type='cash_transaction',
                    entity_id=transaction_id,
                    description=f"Создана кассовая операция: {transaction_type_name} {amount:.2f} руб",
                    details={
                        'Тип операции': 'приход' if transaction_type == 'income' else 'расход',
                        'Сумма': f"{amount:.2f} ₽",
                        'ID категории': category_id,
                        'Способ оплаты': payment_method,
                        'Описание': description
                    }
                )
            except Exception as e:
                logger.warning(f"Не удалось залогировать создание кассовой операции: {e}")
            
            return transaction_id
    
    @staticmethod
    @handle_service_error
    def transfer_between_methods(
        amount: float,
        from_method: str,
        to_method: str,
        transaction_date: Optional[str] = None,
        description: Optional[str] = None,
        created_by_id: Optional[int] = None,
        created_by_username: Optional[str] = None,
    ) -> Tuple[int, int]:
        """
        Перемещение денег между способами оплаты (Наличные ↔ Перевод и т.д.).
        Создаёт две операции: расход с from_method и приход на to_method.
        Итоговый баланс кассы не меняется.
        """
        from app.utils.exceptions import ValidationError

        allowed = {'cash', 'card', 'transfer', 'other'}
        try:
            from app.services.settings_service import SettingsService
            custom = SettingsService.get_payment_method_settings().get('custom_methods', []) or []
            allowed.update({str(m).strip() for m in custom if str(m).strip()})
        except Exception:
            pass

        from_method = (from_method or 'cash').strip().lower()
        to_method = (to_method or 'cash').strip().lower()
        if from_method not in allowed or to_method not in allowed:
            raise ValidationError("Неверный способ оплаты")
        if from_method == to_method:
            raise ValidationError("Укажите разные способы оплаты для списания и зачисления")

        amount = float(amount)
        if amount <= 0:
            raise ValidationError("Сумма должна быть больше нуля")

        if not transaction_date:
            transaction_date = get_moscow_now().date().isoformat()
        if isinstance(transaction_date, str):
            transaction_date = transaction_date.strip()[:10]
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', transaction_date):
            raise ValidationError("Неверная дата (ожидается YYYY-MM-DD)")

        base_desc = f"Перевод между кассами: {from_method} → {to_method}"
        desc = (description or "").strip()
        full_desc = f"{base_desc}. {desc}" if desc else base_desc

        id_expense = FinanceService.create_transaction(
            amount=amount,
            transaction_type='expense',
            category_name='Внутренний перевод (списание)',
            payment_method=from_method,
            description=full_desc,
            transaction_date=transaction_date,
            created_by_id=created_by_id,
            created_by_username=created_by_username,
        )
        id_income = FinanceService.create_transaction(
            amount=amount,
            transaction_type='income',
            category_name='Внутренний перевод (зачисление)',
            payment_method=to_method,
            description=full_desc,
            transaction_date=transaction_date,
            created_by_id=created_by_id,
            created_by_username=created_by_username,
        )
        return (id_expense, id_income)

    @staticmethod
    def _create_transaction_with_cursor(
        cursor,
        amount: float,
        transaction_type: str,
        category_id: int,
        payment_method: str,
        description: str,
        order_id: Optional[int] = None,
        payment_id: Optional[int] = None,
        shop_sale_id: Optional[int] = None,
        transaction_date: Optional[str] = None,
        created_by_id: Optional[int] = None,
        created_by_username: Optional[str] = None,
        storno_of_id: Optional[int] = None
    ) -> int:
        """
        Внутренний метод для создания кассовой операции с существующим cursor.
        Не делает commit - должен вызываться внутри транзакции.
        """
        cursor.execute('''
            INSERT INTO cash_transactions (
                category_id, amount, transaction_type, payment_method, description,
                order_id, payment_id, shop_sale_id, transaction_date,
                created_by_id, created_by_username, storno_of_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            category_id, amount, transaction_type, payment_method, description,
            order_id, payment_id, shop_sale_id, transaction_date,
            created_by_id, created_by_username, storno_of_id
        ))
        return cursor.lastrowid
    
    @staticmethod
    @handle_service_error
    def get_transactions(
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        transaction_type: Optional[str] = None,
        category_id: Optional[int] = None,
        payment_method: Optional[str] = None,
        order_id: Optional[int] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Получить список транзакций с фильтрацией."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            query = '''
                SELECT 
                    ct.*,
                    tc.name as category_name,
                    tc.color as category_color,
                    o.order_id as order_uuid,
                    -- Информация о выплате зарплаты (если есть)
                    sp.user_id as salary_employee_id,
                    sp.role as salary_employee_role,
                    CASE 
                        WHEN sp.role = 'master' THEN m.name
                        WHEN sp.role = 'manager' THEN mg.name
                        ELSE NULL
                    END as salary_employee_name
                FROM cash_transactions ct
                LEFT JOIN transaction_categories tc ON ct.category_id = tc.id
                LEFT JOIN orders o ON o.id = ct.order_id
                LEFT JOIN salary_payments sp ON sp.cash_transaction_id = ct.id
                LEFT JOIN masters m ON m.id = sp.user_id AND sp.role = 'master'
                LEFT JOIN managers mg ON mg.id = sp.user_id AND sp.role = 'manager'
                WHERE 1=1
            '''
            params = []
            
            if date_from:
                query += " AND DATE(ct.transaction_date) >= DATE(?)"
                params.append(date_from)
            if date_to:
                query += " AND DATE(ct.transaction_date) <= DATE(?)"
                params.append(date_to)
            if transaction_type:
                query += " AND ct.transaction_type = ?"
                params.append(transaction_type)
            if category_id:
                query += " AND ct.category_id = ?"
                params.append(category_id)
            if payment_method:
                query += " AND ct.payment_method = ?"
                params.append(payment_method)
            if order_id:
                query += " AND ct.order_id = ?"
                params.append(order_id)
            
            # Последняя созданная операция сверху (id растёт при каждой вставке)
            query += " ORDER BY ct.id DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    @staticmethod
    @handle_service_error
    def get_cash_summary(
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Получить сводку по кассе за период с учетом остатка на начало периода.
        
        Кассовая дисциплина:
        - Остаток на начало = все доходы до date_from минус все расходы до date_from
        - По каждому способу оплаты то же для переноса «наличных / перевода» на следующий день
        - Поступления за период = доходы с date_from по date_to
        - Расходы за период = расходы с date_from по date_to
        - Итоговый баланс = остаток на начало + поступления - расходы
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Эффективные операции: не отменены, не сторно-записи, и не исходные операции по которым сделано сторно
            cancelled_col = 'is_cancelled' in [c[1] for c in cursor.execute("PRAGMA table_info(cash_transactions)").fetchall()]
            effective_filter = " AND (ct.is_cancelled IS NULL OR ct.is_cancelled = 0)" if cancelled_col else ""
            effective_filter += " AND (ct.storno_of_id IS NULL OR ct.storno_of_id = 0)"
            effective_filter += " AND ct.id NOT IN (SELECT storno_of_id FROM cash_transactions WHERE storno_of_id IS NOT NULL AND storno_of_id != 0)"
            
            # Рассчитываем остаток на начало периода (до date_from)
            opening_balance = 0.0
            if date_from:
                open_eff = " AND (is_cancelled IS NULL OR is_cancelled = 0)" if cancelled_col else ""
                open_eff += " AND (storno_of_id IS NULL OR storno_of_id = 0)"
                open_eff += " AND id NOT IN (SELECT storno_of_id FROM cash_transactions WHERE storno_of_id IS NOT NULL AND storno_of_id != 0)"
                cursor.execute(f'''
                    SELECT 
                        COALESCE(SUM(CASE WHEN transaction_type = 'income' THEN amount ELSE 0 END), 0) -
                        COALESCE(SUM(CASE WHEN transaction_type = 'expense' THEN amount ELSE 0 END), 0) as balance
                    FROM cash_transactions
                    WHERE DATE(transaction_date) < DATE(?)
                    ''' + open_eff, (date_from,))
                row = cursor.fetchone()
                opening_balance = float(row[0] or 0) if row else 0.0

            # Входящий остаток по способу оплаты (до date_from) — чтобы «Наличные» и др.
            # переносились на следующий день в карточках, даже если в новом дне нет операций.
            opening_balance_by_method: Dict[str, float] = {}
            if date_from:
                cursor.execute(
                    f"""
                    SELECT
                        COALESCE(payment_method, 'cash'),
                        COALESCE(SUM(CASE WHEN transaction_type = 'income' THEN amount ELSE 0 END), 0) -
                        COALESCE(SUM(CASE WHEN transaction_type = 'expense' THEN amount ELSE 0 END), 0) AS balance
                    FROM cash_transactions
                    WHERE DATE(transaction_date) < DATE(?)
                    """
                    + open_eff
                    + """
                    GROUP BY COALESCE(payment_method, 'cash')
                    """,
                    (date_from,),
                )
                for row in cursor.fetchall():
                    method = row[0] or "cash"
                    opening_balance_by_method[method] = float(row[1] or 0)
            
            # Параметры для фильтрации по периоду
            params = []
            date_filter = ""
            if date_from:
                date_filter += " AND DATE(transaction_date) >= DATE(?)"
                params.append(date_from)
            if date_to:
                date_filter += " AND DATE(transaction_date) <= DATE(?)"
                params.append(date_to)
            
            # Общие суммы за период (только эффективные: без отменённых и без учёта сторнированных)
            base_eff = " AND (is_cancelled IS NULL OR is_cancelled = 0)" if cancelled_col else ""
            base_eff += " AND (storno_of_id IS NULL OR storno_of_id = 0)"
            base_eff += " AND id NOT IN (SELECT storno_of_id FROM cash_transactions WHERE storno_of_id IS NOT NULL AND storno_of_id != 0)"
            cursor.execute(f'''
                SELECT 
                    transaction_type,
                    SUM(amount) as total
                FROM cash_transactions
                WHERE 1=1 {date_filter} {base_eff}
                GROUP BY transaction_type
            ''', params)
            
            totals = {'income': 0, 'expense': 0}
            for row in cursor.fetchall():
                totals[row[0]] = row[1] or 0
            
            # Итоговый баланс = остаток на начало + поступления - расходы
            period_income = totals['income']
            period_expense = totals['expense']
            final_balance = opening_balance + period_income - period_expense
            
            # По категориям за период (только эффективные операции)
            cat_eff = effective_filter.replace("ct.", "ct.")
            cursor.execute(f'''
                SELECT 
                    tc.id,
                    tc.name,
                    tc.type,
                    tc.color,
                    SUM(ct.amount) as total,
                    COUNT(*) as count
                FROM cash_transactions ct
                JOIN transaction_categories tc ON ct.category_id = tc.id
                WHERE 1=1 {date_filter} {cat_eff}
                GROUP BY tc.id
                ORDER BY total DESC
            ''', params)
            
            columns = [desc[0] for desc in cursor.description]
            categories = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            # По способам оплаты за период (только эффективные)
            cursor.execute(f'''
                SELECT 
                    payment_method,
                    transaction_type,
                    SUM(amount) as total
                FROM cash_transactions
                WHERE 1=1 {date_filter} {base_eff}
                GROUP BY payment_method, transaction_type
            ''', params)
            
            by_payment_method = {}
            for row in cursor.fetchall():
                method = row[0] or 'cash'
                t_type = row[1]
                amount = float(row[2] or 0)
                if method not in by_payment_method:
                    by_payment_method[method] = {'income': 0, 'expense': 0}
                by_payment_method[method][t_type] = amount
            
            # Итог по способу = остаток на начало периода по этому способу + приход − расход за период.
            # Ключи объединяем с opening_balance_by_method, чтобы при нулевых операциях за день
            # карточка «Наличные» всё равно показывала перенесённый остаток.
            preferred_method_order = ("cash", "transfer", "card")
            method_keys = set(by_payment_method.keys()) | set(opening_balance_by_method.keys())
            ordered_methods = [m for m in preferred_method_order if m in method_keys]
            ordered_methods.extend(sorted(m for m in method_keys if m not in preferred_method_order))

            merged_by_payment_method: Dict[str, Dict[str, float]] = {}
            for m in ordered_methods:
                src = by_payment_method.get(m) or {}
                merged_by_payment_method[m] = {
                    "income": float(src.get("income", 0) or 0),
                    "expense": float(src.get("expense", 0) or 0),
                }

            balance_by_method = {}
            for m in ordered_methods:
                ob = float(opening_balance_by_method.get(m, 0) or 0)
                t = merged_by_payment_method[m]
                balance_by_method[m] = ob + t["income"] - t["expense"]

            # Перевод между кассами — внутренний виртуальный, не считаем в приход/расход
            internal_eff = " AND (ct.is_cancelled IS NULL OR ct.is_cancelled = 0)" if cancelled_col else ""
            internal_eff += " AND (ct.storno_of_id IS NULL OR ct.storno_of_id = 0)"
            internal_eff += " AND ct.id NOT IN (SELECT storno_of_id FROM cash_transactions WHERE storno_of_id IS NOT NULL AND storno_of_id != 0)"
            internal_date = ""
            internal_params = []
            if date_from:
                internal_date += " AND DATE(ct.transaction_date) >= DATE(?)"
                internal_params.append(date_from)
            if date_to:
                internal_date += " AND DATE(ct.transaction_date) <= DATE(?)"
                internal_params.append(date_to)
            cursor.execute(
                """
                SELECT COALESCE(ct.payment_method, 'cash'), ct.transaction_type, COALESCE(SUM(ct.amount), 0)
                FROM cash_transactions ct
                JOIN transaction_categories tc ON ct.category_id = tc.id
                WHERE tc.name IN ('Внутренний перевод (списание)', 'Внутренний перевод (зачисление)')
                """ + internal_date + internal_eff + """
                GROUP BY COALESCE(ct.payment_method, 'cash'), ct.transaction_type
                """,
                internal_params,
            )
            internal_income = 0.0
            internal_expense = 0.0
            for row in cursor.fetchall():
                t_type = row[1]
                amount = float(row[2] or 0)
                if t_type == 'income':
                    internal_income += amount
                else:
                    internal_expense += amount
            period_income = period_income - internal_income
            period_expense = period_expense - internal_expense
            
            return {
                'opening_balance': opening_balance,
                'opening_balance_by_method': opening_balance_by_method,
                'total_income': period_income,
                'total_expense': period_expense,
                'balance': final_balance,
                'by_category': categories,
                'by_payment_method': merged_by_payment_method,
                'balance_by_method': balance_by_method,
                'date_from': date_from,
                'date_to': date_to
            }

    @staticmethod
    def get_cash_income_breakdown(
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> Dict[str, float]:
        """
        Разбивка приходов кассы за период: по оплатам (заявки), по продажам магазина, прочие.
        Для сверки с отчётом по зарплате: Выручка в зарплате = from_payments + from_shop_sales.
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cancelled_col = 'is_cancelled' in [c[1] for c in cursor.execute("PRAGMA table_info(cash_transactions)").fetchall()]
            base_eff = " AND (is_cancelled IS NULL OR is_cancelled = 0)" if cancelled_col else ""
            base_eff += " AND (storno_of_id IS NULL OR storno_of_id = 0)"
            base_eff += " AND id NOT IN (SELECT storno_of_id FROM cash_transactions WHERE storno_of_id IS NOT NULL AND storno_of_id != 0)"
            date_filter = ""
            params: List[Any] = []
            if date_from:
                date_filter += " AND DATE(transaction_date) >= DATE(?)"
                params.append(date_from)
            if date_to:
                date_filter += " AND DATE(transaction_date) <= DATE(?)"
                params.append(date_to)
            cursor.execute(f'''
                SELECT
                    COALESCE(SUM(CASE WHEN payment_id IS NOT NULL AND payment_id != 0 THEN amount ELSE 0 END), 0) as from_payments,
                    COALESCE(SUM(CASE WHEN shop_sale_id IS NOT NULL AND shop_sale_id != 0 THEN amount ELSE 0 END), 0) as from_shop_sales,
                    COALESCE(SUM(CASE WHEN (payment_id IS NULL OR payment_id = 0) AND (shop_sale_id IS NULL OR shop_sale_id = 0) THEN amount ELSE 0 END), 0) as other
                FROM cash_transactions
                WHERE transaction_type = 'income' {date_filter} {base_eff}
            ''', params)
            row = cursor.fetchone()
            from_payments = float(row[0] or 0)
            from_shop_sales = float(row[1] or 0)
            other = float(row[2] or 0)
            return {
                'from_payments': from_payments,
                'from_shop_sales': from_shop_sales,
                'other': other,
                'total': from_payments + from_shop_sales + other,
            }
    
    @staticmethod
    @handle_service_error
    def cancel_transaction(
        transaction_id: int,
        reason: str = None,
        user_id: int = None,
        username: str = None
    ) -> bool:
        """
        Отменить кассовую операцию (soft-delete + сторно).
        
        Для операций, привязанных к payment_id или shop_sale_id,
        отмена запрещена — нужно отменять саму оплату/продажу.
        
        Args:
            transaction_id: ID операции
            reason: Причина отмены
            user_id: ID пользователя
            username: Имя пользователя
            
        Returns:
            True если успешно
        """
        from datetime import datetime
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Получаем информацию об операции
            cursor.execute('''
                SELECT id, category_id, amount, transaction_type, payment_method, description,
                       order_id, payment_id, shop_sale_id, is_cancelled, storno_of_id
                FROM cash_transactions 
                WHERE id = ?
            ''', (transaction_id,))
            row = cursor.fetchone()
            
            if not row:
                raise NotFoundError(f"Кассовая операция с ID {transaction_id} не найдена")
            
            # Проверяем, не отменена ли уже
            if row[9]:  # is_cancelled
                raise ValidationError("Операция уже отменена")
            
            # Проверяем, это сторно-запись
            if row[10]:  # storno_of_id
                raise ValidationError("Сторно-операции нельзя отменять")
            
            # Запрещаем отмену автоматических операций напрямую
            payment_id = row[7]
            shop_sale_id = row[8]
            
            if payment_id:
                raise ValidationError(
                    "Нельзя отменить операцию, связанную с оплатой. "
                    "Отмените оплату, и кассовая операция будет сторнирована автоматически."
                )
            
            if shop_sale_id:
                raise ValidationError(
                    "Нельзя отменить операцию, связанную с продажей в магазине. "
                    "Отмените продажу, и кассовая операция будет сторнирована автоматически."
                )
            
            category_id = row[1]
            amount = float(row[2])
            transaction_type = row[3]
            payment_method = row[4]
            description = row[5] or ''
            order_id = row[6]
            
            now = get_moscow_now_str()
            
            # Помечаем оригинальную операцию как отменённую
            cursor.execute('''
                UPDATE cash_transactions SET 
                    is_cancelled = 1,
                    cancelled_at = ?,
                    cancelled_reason = ?,
                    cancelled_by_id = ?,
                    cancelled_by_username = ?
                WHERE id = ?
            ''', (now, reason, user_id, username, transaction_id))
            
            # Создаём сторно-операцию
            storno_type = 'expense' if transaction_type == 'income' else 'income'
            storno_description = f"СТОРНО: {description}"
            if reason:
                storno_description += f" (причина: {reason})"
            
            FinanceService._create_transaction_with_cursor(
                cursor=cursor,
                amount=amount,
                transaction_type=storno_type,
                category_id=category_id,
                payment_method=payment_method,
                description=storno_description,
                order_id=order_id,
                transaction_date=get_moscow_now().date().isoformat(),
                created_by_id=user_id,
                created_by_username=username,
                storno_of_id=transaction_id
            )
            
            conn.commit()
            
            # Логируем отмену
            try:
                from app.services.action_log_service import ActionLogService
                type_name = 'приход' if transaction_type == 'income' else 'расход'
                ActionLogService.log_action(
                    user_id=user_id,
                    username=username,
                    action_type='cancel',
                    entity_type='cash_transaction',
                    entity_id=transaction_id,
                    description=f"Отменена кассовая операция #{transaction_id}: {type_name} {amount:.2f} руб",
                    details={
                        'Тип операции': type_name,
                        'Сумма': f"{amount:.2f} ₽",
                        'Причина отмены': reason or 'Не указана'
                    }
                )
            except Exception as e:
                logger.warning(f"Не удалось залогировать отмену операции: {e}")
            
            return True
    
    @staticmethod
    @handle_service_error
    def delete_transaction(
        transaction_id: int,
        user_id: int = None,
        username: str = None,
        reason: str = None
    ) -> bool:
        """
        Отменить кассовую операцию (обёртка над cancel_transaction).
        
        ВАЖНО: Физическое удаление заменено на soft-delete + сторно.
        
        Args:
            transaction_id: ID операции
            user_id: ID пользователя
            username: Имя пользователя
            reason: Причина отмены
            
        Returns:
            True если успешно
        """
        return FinanceService.cancel_transaction(
            transaction_id=transaction_id,
            reason=reason or "Удаление операции",
            user_id=user_id,
            username=username
        )
    
    # ===========================================
    # ПРОДАЖИ В МАГАЗИНЕ
    # ===========================================
    
    @staticmethod
    @handle_service_error
    def create_shop_sale(
        items: List[Dict[str, Any]],
        customer_id: Optional[int] = None,
        customer_name: Optional[str] = None,
        customer_phone: Optional[str] = None,
        manager_id: Optional[int] = None,
        master_id: Optional[int] = None,
        discount: float = 0,
        payment_method: str = 'cash',
        paid_amount: Optional[float] = None,
        comment: Optional[str] = None,
        created_by_id: Optional[int] = None,
        created_by_username: Optional[str] = None
    ) -> Tuple[int, Dict[str, Any]]:
        """
        Создать продажу в магазине.
        
        master_id сохраняется в shop_sales (это users.id выбранного мастера).
        Начисления зарплаты по продажам магазина создаются через SalaryService.accrue_salary_for_shop_sale
        по тем же правилам, что и по заявкам: услуга — правило услуги или salary_percent_services мастера,
        товар — правило товара или salary_percent_shop_parts мастера.
        
        items - список позиций:
        [
            {'type': 'service', 'service_id': 1, 'quantity': 1, 'price': 500},
            {'type': 'part', 'part_id': 2, 'quantity': 2, 'price': 200}
        ]
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Расчет сумм
            total_amount = sum(item['price'] * item.get('quantity', 1) for item in items)
            final_amount = total_amount - discount
            if paid_amount is None:
                paid_amount = final_amount
            
            # Дата продажи — по московскому времени, чтобы попадать в фильтр «Сегодня» на странице /shop/
            try:
                from app.utils.datetime_utils import get_moscow_now_str
                sale_date_value = get_moscow_now_str('%Y-%m-%d')
            except Exception:
                sale_date_value = get_moscow_now().date().isoformat()
            
            # Создаем продажу
            cursor.execute('''
                INSERT INTO shop_sales (
                    customer_id, customer_name, customer_phone,
                    manager_id, master_id,
                    total_amount, discount, final_amount, paid_amount, payment_method,
                    comment, sale_date, created_by_id, created_by_username
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                customer_id, customer_name, customer_phone,
                manager_id, master_id,
                total_amount, discount, final_amount, paid_amount, payment_method,
                comment, sale_date_value, created_by_id, created_by_username
            ))
            
            sale_id = cursor.lastrowid
            
            # Добавляем позиции
            for item in items:
                item_type = item.get('type', 'service')
                quantity = item.get('quantity', 1)
                price = item['price']
                total = price * quantity
                
                service_id = None
                service_name = None
                part_id = None
                part_name = None
                part_sku = None
                purchase_price = 0
                
                if item_type == 'service':
                    service_id = item.get('service_id')
                    if service_id:
                        cursor.execute(
                            "SELECT name FROM services WHERE id = ?", (service_id,)
                        )
                        row = cursor.fetchone()
                        if row:
                            service_name = row[0]
                    else:
                        service_name = item.get('name', 'Услуга')
                else:
                    part_id = item.get('part_id')
                    if part_id:
                        cursor.execute(
                            "SELECT name, part_number, purchase_price, stock_quantity FROM parts WHERE id = ? AND is_deleted = 0", 
                            (part_id,)
                        )
                        row = cursor.fetchone()
                        if row:
                            part_name, part_sku, purchase_price, old_stock = row
                            purchase_price = purchase_price or 0
                            old_stock = old_stock or 0
                        else:
                            old_stock = 0
                        
                        # Списание со склада
                        cursor.execute('''
                            UPDATE parts 
                            SET stock_quantity = stock_quantity - ?
                            WHERE id = ? AND stock_quantity >= ?
                        ''', (quantity, part_id, quantity))
                        
                        if cursor.rowcount == 0:
                            conn.rollback()
                            raise ValidationError(f"Недостаточно товара на складе: {part_name}")
                        
                        new_stock = old_stock - quantity
                        
                        # Создаем запись о движении товара
                        cursor.execute('''
                            INSERT INTO stock_movements (
                                part_id, movement_type, quantity, 
                                reference_id, reference_type, 
                                created_by, notes
                            )
                            VALUES (?, 'sale', ?, ?, 'shop_sale', ?, ?)
                        ''', (
                            part_id, -quantity, sale_id, 
                            created_by_id, f"Продажа в магазине: {part_name}"
                        ))
                        
                        # Логируем в warehouse_logs
                        cursor.execute('''
                            INSERT INTO warehouse_logs (
                                operation_type, part_id, part_name, part_number,
                                user_id, username, quantity, old_value, new_value, notes
                            )
                            VALUES ('expense', ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            part_id, part_name, part_sku,
                            created_by_id, created_by_username, quantity,
                            str(old_stock), str(new_stock),
                            f"Продажа в магазине #{sale_id}"
                        ))
                    else:
                        part_name = item.get('name', 'Товар')
                
                cursor.execute('''
                    INSERT INTO shop_sale_items (
                        shop_sale_id, item_type,
                        service_id, service_name,
                        part_id, part_name, part_sku,
                        quantity, price, purchase_price, total
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    sale_id, item_type,
                    service_id, service_name,
                    part_id, part_name, part_sku,
                    quantity, price, purchase_price, total
                ))
            
            conn.commit()
            
            # Создаем кассовую транзакцию через единый метод
            # Определяем категорию
            has_services = any(i.get('type') == 'service' for i in items)
            has_parts = any(i.get('type') == 'part' for i in items)
            
            if has_parts:
                category_name = 'Продажа товаров'
            else:
                category_name = 'Оплата услуг'
            
            # Получаем дату продажи из БД
            cursor.execute("SELECT sale_date FROM shop_sales WHERE id = ?", (sale_id,))
            sale_date_row = cursor.fetchone()
            sale_date = sale_date_row[0] if sale_date_row else get_moscow_now_str()
            
            # Используем create_transaction для создания кассовой операции
            # Это обеспечивает единый путь и валидацию
            FinanceService.create_transaction(
                category_name=category_name,
                amount=paid_amount,
                transaction_type='income',
                payment_method=payment_method,
                description=f"Продажа в магазине #{sale_id}",
                shop_sale_id=sale_id,
                transaction_date=sale_date,  # Используем дату продажи
                created_by_id=created_by_id,
                created_by_username=created_by_username
            )
            
            # Логируем создание продажи в магазине
            try:
                from app.services.action_log_service import ActionLogService
                ActionLogService.log_action(
                    user_id=created_by_id,
                    username=created_by_username,
                    action_type='create',
                    entity_type='shop_sale',
                    entity_id=sale_id,
                    description=f"Создана продажа в магазине #{sale_id}: {final_amount:.2f} руб",
                    details={
                        'ID клиента': customer_id,
                        'Клиент': customer_name,
                        'Сумма': f"{total_amount:.2f} ₽",
                        'Скидка': f"{discount:.2f} ₽" if discount else "0 ₽",
                        'Итого': f"{final_amount:.2f} ₽",
                        'Оплачено': f"{paid_amount:.2f} ₽",
                        'Позиций': len(items)
                    }
                )
            except Exception as e:
                logger.warning(f"Не удалось залогировать создание продажи в магазине: {e}")

            # Начисление зарплаты по правилам услуги/товара (как в модуле зарплаты)
            if master_id and final_amount > 0:
                try:
                    from app.services.salary_service import SalaryService
                    accruals = SalaryService.accrue_salary_for_shop_sale(sale_id)
                    if not accruals:
                        logger.warning(
                            f"По продаже магазина #{sale_id} начисления зарплаты не созданы: "
                            "проверьте правила зарплаты для мастера (процент с услуг/товаров магазина) или для услуг/товаров"
                        )
                except Exception as e:
                    logger.warning(f"Не удалось начислить зарплату по продаже магазина #{sale_id}: {e}")
            elif final_amount > 0 and not master_id:
                logger.info(f"Продажа магазина #{sale_id}: исполнитель не выбран — зарплата не начисляется")
            
            return sale_id, {
                'id': sale_id,
                'total_amount': total_amount,
                'discount': discount,
                'final_amount': final_amount,
                'paid_amount': paid_amount
            }

    @staticmethod
    @handle_service_error
    def refund_shop_sale(
        sale_id: int,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        reason: Optional[str] = None,
        create_refund_sale: bool = True
    ) -> Dict[str, Any]:
        """
        Возврат продажи в магазине.
        Создает сторно по кассе, возвращает товары на склад.
        Если create_refund_sale=True — создаёт отрицательную продажу.
        """
        if not sale_id or sale_id <= 0:
            raise ValidationError("Неверный ID продажи")
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM shop_sales WHERE id = ?", (sale_id,))
            sale_row = cursor.fetchone()
            if not sale_row:
                raise NotFoundError(f"Продажа с ID {sale_id} не найдена")
            
            sale_columns = [desc[0] for desc in cursor.description]
            sale = dict(zip(sale_columns, sale_row))

            # Нельзя делать возврат по возвратной (отрицательной) продаже
            try:
                final_amount = float(sale.get('final_amount') or 0)
            except Exception:
                final_amount = 0
            if final_amount < 0:
                raise ValidationError("Нельзя делать возврат по возвратной продаже")

            # Удаляем начисления зарплаты по этой продаже (при возврате они не применяются)
            try:
                from app.database.queries.salary_queries import SalaryQueries
                SalaryQueries.delete_accruals_for_shop_sale(sale_id)
            except Exception as e:
                logger.warning(f"Не удалось удалить начисления зарплаты по продаже #{sale_id}: {e}")
            
            # Если уже создана возвратная кассовая операция, блокируем повторный возврат
            cursor.execute(
                """
                SELECT id FROM cash_transactions
                WHERE shop_sale_id = ?
                  AND storno_of_id IS NOT NULL
                  AND storno_of_id != 0
                LIMIT 1
                """,
                (sale_id,),
            )
            if cursor.fetchone():
                raise ValidationError("Возврат по этой продаже уже выполнен")
            
            cursor.execute("SELECT * FROM shop_sale_items WHERE shop_sale_id = ?", (sale_id,))
            item_columns = [desc[0] for desc in cursor.description]
            items = [dict(zip(item_columns, row)) for row in cursor.fetchall()]
            
            # Ищем исходную кассовую операцию (включая уже отмененные)
            cursor.execute('''
                SELECT id, category_id, amount, payment_method, transaction_type
                FROM cash_transactions
                WHERE shop_sale_id = ? AND (storno_of_id IS NULL OR storno_of_id = 0)
                ORDER BY id DESC
                LIMIT 1
            ''', (sale_id,))
            cash_row = cursor.fetchone()
            cash_tx_id = cash_row[0] if cash_row else None
            cash_category_id = cash_row[1] if cash_row else None
            cash_amount = float(cash_row[2]) if cash_row else float(sale.get('paid_amount') or sale.get('final_amount') or 0)
            cash_method = cash_row[3] if cash_row else sale.get('payment_method') or 'cash'
            cash_type = cash_row[4] if cash_row else 'income'
            
            if cash_tx_id:
                cursor.execute("SELECT id FROM cash_transactions WHERE storno_of_id = ? LIMIT 1", (cash_tx_id,))
                if cursor.fetchone():
                    raise ValidationError("Возврат по этой продаже уже выполнен")
            
            # Дополнительная защита: ищем возвратные продажи по комментарию
            cursor.execute(
                "SELECT id FROM shop_sales WHERE final_amount < 0 AND comment LIKE ? LIMIT 1",
                (f"Возврат продажи #{sale_id}%",),
            )
            if cursor.fetchone():
                raise ValidationError("Возврат по этой продаже уже выполнен")
            
            # Возврат товаров на склад
            for item in items:
                if item.get('item_type') != 'part' or not item.get('part_id'):
                    continue
                part_id = int(item['part_id'])
                qty = int(item.get('quantity') or 0)
                if qty <= 0:
                    continue
                
                cursor.execute('''
                    UPDATE parts
                    SET stock_quantity = stock_quantity + ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND is_deleted = 0
                ''', (qty, part_id))
                
                cursor.execute('''
                    INSERT INTO stock_movements 
                    (part_id, movement_type, quantity, reference_id, reference_type, created_by, notes)
                    VALUES (?, 'return', ?, ?, 'shop_sale', ?, ?)
                ''', (part_id, qty, sale_id, user_id, f"Возврат продажи в магазине #{sale_id}"))
                
                cursor.execute('''
                    INSERT INTO warehouse_logs 
                    (operation_type, part_id, part_name, part_number, user_id, username, quantity, notes)
                    VALUES ('return', ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    part_id,
                    item.get('part_name'),
                    item.get('part_sku'),
                    user_id,
                    username,
                    qty,
                    f"Возврат продажи в магазине #{sale_id}"
                ))
            
            refund_sale_id = None
            if create_refund_sale:
                cursor.execute('''
                    INSERT INTO shop_sales (
                        customer_id, customer_name, customer_phone,
                        manager_id, master_id,
                        total_amount, discount, final_amount, paid_amount, payment_method,
                        comment, created_by_id, created_by_username, sale_date
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, DATE('now'))
                ''', (
                    sale.get('customer_id'), sale.get('customer_name'), sale.get('customer_phone'),
                    sale.get('manager_id'), sale.get('master_id'),
                    -float(sale.get('total_amount') or 0),
                    0,
                    -float(sale.get('final_amount') or 0),
                    -float(sale.get('paid_amount') or 0),
                    cash_method,
                    f"Возврат продажи #{sale_id}" + (f" — {reason}" if reason else ""),
                    user_id, username
                ))
                refund_sale_id = cursor.lastrowid
                
                for item in items:
                    qty = int(item.get('quantity') or 0)
                    price = float(item.get('price') or 0)
                    total = price * (-qty)
                    cursor.execute('''
                        INSERT INTO shop_sale_items (
                            shop_sale_id, item_type,
                            service_id, service_name,
                            part_id, part_name, part_sku,
                            quantity, price, purchase_price, total
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        refund_sale_id,
                        item.get('item_type'),
                        item.get('service_id'),
                        item.get('service_name'),
                        item.get('part_id'),
                        item.get('part_name'),
                        item.get('part_sku'),
                        -qty,
                        price,
                        item.get('purchase_price'),
                        total
                    ))
            
            # Сторно кассовой операции
            # Если есть исходная кассовая операция - создаем сторно
            # Если нет - создаем expense операцию с категорией по умолчанию
            if cash_category_id:
                storno_description = f"СТОРНО: продажа в магазине #{sale_id}"
                if reason:
                    storno_description += f" (причина: {reason})"
                storno_type = 'expense' if cash_type == 'income' else 'income'
                FinanceService._create_transaction_with_cursor(
                    cursor=cursor,
                    amount=abs(cash_amount),
                    transaction_type=storno_type,
                    category_id=cash_category_id,
                    payment_method=cash_method,
                    description=storno_description,
                    shop_sale_id=refund_sale_id if refund_sale_id else None,
                    transaction_date=get_moscow_now().date().isoformat(),
                    created_by_id=user_id,
                    created_by_username=username,
                    storno_of_id=cash_tx_id
                )
                
                if cash_tx_id:
                    cursor.execute('''
                        UPDATE cash_transactions
                        SET is_cancelled = 1,
                            cancelled_at = CURRENT_TIMESTAMP,
                            cancelled_reason = ?,
                            cancelled_by_id = ?,
                            cancelled_by_username = ?
                        WHERE id = ?
                    ''', (reason or "Возврат продажи", user_id, username, cash_tx_id))
            elif refund_sale_id:
                # Если нет исходной кассовой операции, но есть возвратная продажа
                # Создаем expense операцию с категорией по умолчанию
                # Ищем категорию "Возврат" или первую expense категорию
                cursor.execute('''
                    SELECT id FROM transaction_categories
                    WHERE category_type = 'expense'
                    AND (name LIKE '%Возврат%' OR name LIKE '%Возвраты%')
                    LIMIT 1
                ''')
                default_category_row = cursor.fetchone()
                if not default_category_row:
                    # Если нет категории "Возврат", берем первую expense категорию
                    cursor.execute('''
                        SELECT id FROM transaction_categories
                        WHERE category_type = 'expense'
                        ORDER BY id
                        LIMIT 1
                    ''')
                    default_category_row = cursor.fetchone()
                
                if default_category_row:
                    default_category_id = default_category_row[0]
                    storno_description = f"Возврат продажи в магазине #{sale_id}"
                    if reason:
                        storno_description += f" (причина: {reason})"
                    
                    FinanceService._create_transaction_with_cursor(
                        cursor=cursor,
                        amount=abs(cash_amount),
                        transaction_type='expense',
                        category_id=default_category_id,
                        payment_method=cash_method,
                        description=storno_description,
                        shop_sale_id=refund_sale_id,
                        transaction_date=get_moscow_now().date().isoformat(),
                        created_by_id=user_id,
                        created_by_username=username,
                        storno_of_id=None  # Нет исходной операции для сторно
                    )
            
            conn.commit()
        
        # Логируем возврат
        try:
            from app.services.action_log_service import ActionLogService
            ActionLogService.log_action(
                user_id=user_id,
                username=username,
                action_type='refund_shop_sale',
                entity_type='shop_sale',
                entity_id=sale_id,
                description=f"Возврат продажи в магазине #{sale_id}",
                details={
                    'refund_sale_id': refund_sale_id,
                    'amount': cash_amount,
                    'reason': reason
                }
            )
        except Exception as e:
            logger.warning(f"Не удалось залогировать возврат продажи {sale_id}: {e}")
        
        return {
            'success': True,
            'refund_sale_id': refund_sale_id
        }

    @staticmethod
    @handle_service_error
    def delete_shop_sale(
        sale_id: int,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        reason: Optional[str] = None
    ) -> bool:
        """Удаляет продажу из магазина с возвратом средств и остатков."""
        FinanceService.refund_shop_sale(
            sale_id=sale_id,
            user_id=user_id,
            username=username,
            reason=reason or "Удаление продажи",
            create_refund_sale=False
        )
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM shop_sale_items WHERE shop_sale_id = ?", (sale_id,))
            cursor.execute("DELETE FROM shop_sales WHERE id = ?", (sale_id,))
            conn.commit()
        
        try:
            from app.services.action_log_service import ActionLogService
            ActionLogService.log_action(
                user_id=user_id,
                username=username,
                action_type='delete_shop_sale',
                entity_type='shop_sale',
                entity_id=sale_id,
                description=f"Удалена продажа в магазине #{sale_id}",
                details={'reason': reason or "Удаление продажи"}
            )
        except Exception as e:
            logger.warning(f"Не удалось залогировать удаление продажи {sale_id}: {e}")
        
        return True
    
    @staticmethod
    @handle_service_error
    def get_shop_sales(
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        customer_id: Optional[int] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Получить список продаж в магазине."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            query = '''
                SELECT 
                    ss.*,
                    u1.username as manager_name,
                    COALESCE(NULLIF(TRIM(m.name), ''), u2.display_name, u2.username) as master_name,
                    c.name as customer_full_name
                FROM shop_sales ss
                LEFT JOIN users u1 ON ss.manager_id = u1.id
                LEFT JOIN users u2 ON ss.master_id = u2.id
                LEFT JOIN masters m ON m.user_id = ss.master_id
                LEFT JOIN customers c ON ss.customer_id = c.id
                WHERE 1=1
            '''
            params = []
            
            if date_from:
                query += " AND DATE(ss.sale_date) >= DATE(?)"
                params.append(date_from)
            if date_to:
                query += " AND DATE(ss.sale_date) <= DATE(?)"
                params.append(date_to)
            if customer_id:
                query += " AND ss.customer_id = ?"
                params.append(customer_id)
            
            query += " ORDER BY ss.sale_date DESC, ss.created_at DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            columns = [desc[0] for desc in cursor.description]
            sales = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            # Загружаем позиции и статусы для каждой продажи
            for sale in sales:
                cursor.execute('''
                    SELECT * FROM shop_sale_items WHERE shop_sale_id = ?
                ''', (sale['id'],))
                item_columns = [desc[0] for desc in cursor.description]
                sale['items'] = [dict(zip(item_columns, row)) for row in cursor.fetchall()]
                sale['items_count'] = len(sale['items'])
                
                # Признак возврата (отрицательная продажа)
                try:
                    sale['is_refund'] = float(sale.get('final_amount') or 0) < 0
                except Exception:
                    sale['is_refund'] = False
                
                # Признак уже возвращенной продажи
                cursor.execute(
                    "SELECT id FROM shop_sales WHERE final_amount < 0 AND comment LIKE ? LIMIT 1",
                    (f"Возврат продажи #{sale['id']}%",),
                )
                sale['is_refunded'] = cursor.fetchone() is not None
            
            return sales
    
    @staticmethod
    @handle_service_error
    def get_master_shop_sales(master_id: int, date_from: Optional[str] = None, date_to: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Получает продажи из магазина для мастера (для расчета зарплаты).
        
        Args:
            master_id: ID мастера
            date_from: Дата начала периода (опционально)
            date_to: Дата окончания периода (опционально)
            
        Returns:
            Список продаж из магазина
        """
        with get_db_connection(row_factory=sqlite3.Row) as conn:
            cursor = conn.cursor()
            
            where_clauses = ["ss.master_id = ?"]
            params = [master_id]
            
            if date_from:
                where_clauses.append("DATE(ss.sale_date) >= DATE(?)")
                params.append(date_from)
            if date_to:
                where_clauses.append("DATE(ss.sale_date) <= DATE(?)")
                params.append(date_to)
            
            where_sql = " AND ".join(where_clauses)
            
            cursor.execute(f'''
                SELECT 
                    ss.id,
                    ss.sale_date,
                    ss.created_at,
                    ss.final_amount,
                    ss.paid_amount,
                    ss.payment_method,
                    ss.customer_id,
                    c.name as customer_name,
                    c.phone as customer_phone
                FROM shop_sales ss
                LEFT JOIN customers c ON ss.customer_id = c.id
                WHERE {where_sql}
                ORDER BY ss.sale_date DESC, ss.created_at DESC
            ''', params)
            
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
    
    @staticmethod
    @handle_service_error
    def get_shop_sale(sale_id: int) -> Optional[Dict[str, Any]]:
        """Получить продажу по ID."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    ss.*,
                    u1.username as manager_name,
                    COALESCE(NULLIF(TRIM(m.name), ''), u2.display_name, u2.username) as master_name,
                    c.name as customer_full_name,
                    c.phone as customer_phone,
                    NULL as order_uuid
                FROM shop_sales ss
                LEFT JOIN users u1 ON ss.manager_id = u1.id
                LEFT JOIN users u2 ON ss.master_id = u2.id
                LEFT JOIN masters m ON m.user_id = ss.master_id
                LEFT JOIN customers c ON ss.customer_id = c.id
                WHERE ss.id = ?
            ''', (sale_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            columns = [desc[0] for desc in cursor.description]
            sale = dict(zip(columns, row))
            
            # Загружаем позиции с подстановкой наименований из services/parts при их отсутствии
            cursor.execute('''
                SELECT 
                    ssi.id, ssi.shop_sale_id, ssi.item_type,
                    ssi.service_id, COALESCE(NULLIF(TRIM(ssi.service_name), ''), s.name) as service_name,
                    ssi.part_id, COALESCE(NULLIF(TRIM(ssi.part_name), ''), p.name) as part_name,
                    ssi.part_sku, ssi.quantity, ssi.price, ssi.purchase_price, ssi.total, ssi.created_at
                FROM shop_sale_items ssi
                LEFT JOIN services s ON ssi.service_id = s.id
                LEFT JOIN parts p ON ssi.part_id = p.id
                WHERE ssi.shop_sale_id = ?
            ''', (sale_id,))
            item_columns = [desc[0] for desc in cursor.description]
            sale['items'] = [dict(zip(item_columns, row)) for row in cursor.fetchall()]
            
            return sale
    
    @staticmethod
    @handle_service_error
    def get_payment(payment_id: int) -> Optional[Dict[str, Any]]:
        """Получить оплату по ID с детальной информацией о заявке."""
        with get_db_connection(row_factory=sqlite3.Row) as conn:
            cursor = conn.cursor()
            
            # Получаем оплату с данными заявки
            cursor.execute('''
                SELECT 
                    p.*,
                    o.order_id AS order_uuid,
                    o.id AS order_internal_id,
                    o.model,
                    c.id AS customer_id,
                    c.name AS customer_name,
                    c.phone AS customer_phone,
                    c.email AS customer_email,
                    d.id AS device_id,
                    dt.name AS device_type,
                    db.name AS brand,
                    d.serial_number
                FROM payments p
                LEFT JOIN orders o ON o.id = p.order_id
                LEFT JOIN customers c ON c.id = o.customer_id
                LEFT JOIN devices d ON d.id = o.device_id
                LEFT JOIN device_types dt ON dt.id = d.device_type_id
                LEFT JOIN device_brands db ON db.id = d.device_brand_id
                WHERE p.id = ?
            ''', (payment_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            payment = dict(row)
            
            # Получаем услуги и запчасти заявки для отображения в чеке
            order_internal_id = payment.get('order_internal_id')
            if order_internal_id:
                # Услуги
                cursor.execute('''
                    SELECT 
                        s.name,
                        os.quantity,
                        os.price,
                        (os.quantity * os.price) AS total
                    FROM order_services os
                    JOIN services s ON s.id = os.service_id
                    WHERE os.order_id = ?
                ''', (order_internal_id,))
                
                services = []
                for svc_row in cursor.fetchall():
                    services.append({
                        'name': svc_row[0],
                        'quantity': svc_row[1],
                        'price': svc_row[2],
                        'total': svc_row[3]
                    })
                
                # Запчасти
                cursor.execute('''
                    SELECT 
                        pt.name,
                        pt.part_number,
                        op.quantity,
                        op.price,
                        (op.quantity * op.price) AS total
                    FROM order_parts op
                    JOIN parts pt ON pt.id = op.part_id
                    WHERE op.order_id = ?
                ''', (order_internal_id,))
                
                parts = []
                for part_row in cursor.fetchall():
                    parts.append({
                        'name': part_row[0],
                        'part_number': part_row[1],
                        'quantity': part_row[2],
                        'price': part_row[3],
                        'total': part_row[4]
                    })
                
                payment['services'] = services
                payment['parts'] = parts
                
                # Вычисляем общую сумму заявки
                total_services = sum(s['total'] for s in services)
                total_parts = sum(p['total'] for p in parts)
                payment['order_total'] = total_services + total_parts
            else:
                payment['services'] = []
                payment['parts'] = []
                payment['order_total'] = 0
            
            return payment
    
    # ===========================================
    # ОТЧЕТЫ И АНАЛИТИКА
    # ===========================================
    
    @staticmethod
    @handle_service_error
    def get_profit_report(
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """Расчет прибыли за период."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            params = []
            date_filter = ""
            if date_from:
                date_filter += " AND transaction_date >= ?"
                params.append(date_from)
            if date_to:
                date_filter += " AND transaction_date <= ?"
                params.append(date_to)
            
            # Исключаем отменённые и сторнированные транзакции (как на странице кассы)
            cursor.execute("PRAGMA table_info(cash_transactions)")
            cols = [c[1] for c in cursor.fetchall()]
            eff_filter = ""
            if 'is_cancelled' in cols:
                eff_filter += " AND (ct.is_cancelled IS NULL OR ct.is_cancelled = 0)"
            if 'storno_of_id' in cols:
                eff_filter += " AND (ct.storno_of_id IS NULL OR ct.storno_of_id = 0)"
                eff_filter += " AND ct.id NOT IN (SELECT storno_of_id FROM cash_transactions WHERE storno_of_id IS NOT NULL AND storno_of_id != 0)"

            # Внутренние переводы не считаем ни в доходах, ни в расходах (виртуальное движение между кассами)
            internal_cat_filter = " AND tc.name NOT IN ('Внутренний перевод (списание)', 'Внутренний перевод (зачисление)')"

            # Доходы по категориям (только приход, без внутренних переводов)
            cursor.execute(f'''
                SELECT 
                    tc.name,
                    SUM(ct.amount) as total
                FROM cash_transactions ct
                JOIN transaction_categories tc ON ct.category_id = tc.id
                WHERE ct.transaction_type = 'income' {internal_cat_filter} {date_filter}{eff_filter}
                GROUP BY tc.id
            ''', params)
            
            income_by_category = {row[0]: float(row[1] or 0) for row in cursor.fetchall()}
            total_income = sum(income_by_category.values())
            
            # Расходы по категориям (только расход, без внутренних переводов)
            cursor.execute(f'''
                SELECT 
                    tc.name,
                    SUM(ct.amount) as total
                FROM cash_transactions ct
                JOIN transaction_categories tc ON ct.category_id = tc.id
                WHERE ct.transaction_type = 'expense' {internal_cat_filter} {date_filter}{eff_filter}
                GROUP BY tc.id
            ''', params)
            
            expense_by_category = {row[0]: float(row[1] or 0) for row in cursor.fetchall()}
            total_expense = sum(expense_by_category.values())

            # Доходы по способам оплаты (без внутренних переводов)
            cursor.execute(f'''
                SELECT
                    COALESCE(ct.payment_method, 'other') AS payment_method,
                    COALESCE(SUM(ct.amount), 0) AS total
                FROM cash_transactions ct
                JOIN transaction_categories tc ON ct.category_id = tc.id
                WHERE ct.transaction_type = 'income' {internal_cat_filter} {date_filter}{eff_filter}
                GROUP BY COALESCE(ct.payment_method, 'other')
            ''', params)
            income_by_payment_method_raw = {row[0]: float(row[1] or 0) for row in cursor.fetchall()}
            try:
                from app.services.settings_service import SettingsService
                payment_labels = SettingsService.get_payment_method_settings()
            except Exception:
                payment_labels = {'cash_label': 'Наличные', 'card_label': 'Карта', 'transfer_label': 'Перевод'}

            payment_method_name_map = {
                'cash': (payment_labels.get('cash_label') or '').strip() or 'Наличные',
                'card': (payment_labels.get('card_label') or '').strip() or 'Другое',
                'transfer': (payment_labels.get('transfer_label') or '').strip() or 'Перевод',
                'other': 'Другое',
            }
            income_by_payment_method = {}
            for method, amount in income_by_payment_method_raw.items():
                display_name = payment_method_name_map.get(method, method or 'Другое')
                income_by_payment_method[display_name] = income_by_payment_method.get(display_name, 0.0) + float(amount or 0)
            
            # Себестоимость проданных товаров (из продаж в магазине)
            shop_date_filter = ""
            shop_params = []
            if date_from:
                shop_date_filter += " AND ss.sale_date >= ?"
                shop_params.append(date_from)
            if date_to:
                shop_date_filter += " AND ss.sale_date <= ?"
                shop_params.append(date_to)
            
            cursor.execute(f'''
                SELECT 
                    SUM(ssi.purchase_price * ssi.quantity) as cogs
                FROM shop_sale_items ssi
                JOIN shop_sales ss ON ssi.shop_sale_id = ss.id
                WHERE ssi.item_type = 'part' {shop_date_filter}
            ''', shop_params)
            
            cogs_shop = float(cursor.fetchone()[0] or 0)
            
            # Себестоимость из order_parts: считаем только по заявкам, оплаченным в периоде
            # (доходы считаются по дате оплаты, поэтому COGS должен быть по той же логике —
            # иначе при создании заявок в одном периоде и оплате в другом прибыль искажается)
            order_params = []
            order_payment_filter = ""
            if date_from:
                order_payment_filter += " AND ct.transaction_date >= ?"
                order_params.append(date_from)
            if date_to:
                order_payment_filter += " AND ct.transaction_date <= ?"
                order_params.append(date_to)
            ct_eff = eff_filter  # те же исключения (отменённые, сторно) в подзапросах

            cursor.execute(f'''
                SELECT 
                    COALESCE(SUM(op.purchase_price * op.quantity), 0) as cogs
                FROM order_parts op
                WHERE op.order_id IN (
                    SELECT DISTINCT ct.order_id
                    FROM cash_transactions ct
                    WHERE ct.transaction_type = 'income'
                      AND ct.order_id IS NOT NULL
                      {ct_eff}
                      {order_payment_filter}
                )
            ''', order_params)
            
            cogs_orders = float(cursor.fetchone()[0] or 0)
            
            total_cogs = cogs_shop + cogs_orders
            
            # Выручка от услуг: все приходные операции, привязанные к заявкам.
            cursor.execute(f'''
                SELECT COALESCE(SUM(ct.amount), 0)
                FROM cash_transactions ct
                WHERE ct.transaction_type = 'income'
                  AND ct.order_id IS NOT NULL
                  {date_filter}{eff_filter}
            ''', params)
            services_revenue = float((cursor.fetchone() or [0])[0] or 0)

            # Выручка от товаров: приходы, привязанные к продажам магазина.
            cursor.execute(f'''
                SELECT COALESCE(SUM(ct.amount), 0)
                FROM cash_transactions ct
                WHERE ct.transaction_type = 'income'
                  AND ct.shop_sale_id IS NOT NULL
                  {date_filter}{eff_filter}
            ''', params)
            goods_revenue = float((cursor.fetchone() or [0])[0] or 0)
            
            # Валовая прибыль = Выручка - Себестоимость
            gross_profit = total_income - total_cogs
            
            # Чистая прибыль = Выручка - Себестоимость - Операционные расходы
            # (раньше было неправильно: total_income - total_expense, без учёта COGS)
            net_profit = total_income - total_cogs - total_expense
            
            # Операционная прибыль (для справки) = Выручка - Расходы (без учёта COGS)
            operating_profit = total_income - total_expense
            
            return {
                'date_from': date_from,
                'date_to': date_to,
                'total_income': total_income,
                'total_expense': total_expense,
                'income_by_category': income_by_category,
                'expense_by_category': expense_by_category,
                'income_by_payment_method': income_by_payment_method,
                'services_revenue': services_revenue,
                'goods_revenue': goods_revenue,
                'cogs': total_cogs,
                'gross_profit': gross_profit,
                'operating_profit': operating_profit,  # Новое поле
                'net_profit': net_profit,  # Исправлено: теперь учитывает COGS
                'margin_percent': (gross_profit / total_income * 100) if total_income > 0 else 0
            }
    
    @staticmethod
    @handle_service_error
    def get_product_analytics(
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        """Аналитика по товарам: рентабельность, оборачиваемость, топ продаж."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            params = []
            date_filter = ""
            if date_from:
                date_filter += " AND ss.sale_date >= ?"
                params.append(date_from)
            if date_to:
                date_filter += " AND ss.sale_date <= ?"
                params.append(date_to)
            
            # Топ продаж товаров: объединяем продажи из магазина и из заявок
            # 1. Продажи из магазина
            shop_date_filter = ""
            shop_params = []
            if date_from:
                shop_date_filter += " AND DATE(ss.sale_date) >= DATE(?)"
                shop_params.append(date_from)
            if date_to:
                shop_date_filter += " AND DATE(ss.sale_date) <= DATE(?)"
                shop_params.append(date_to)
            
            # 2. Продажи из заявок (используем дату создания позиции в заявке, а не дату создания заявки)
            # Это важно: товар/услуга проданы тогда, когда добавлены в заявку, а не когда создана заявка
            order_parts_date_filter = ""
            order_services_date_filter = ""
            order_params = []
            if date_from:
                order_parts_date_filter += " AND DATE(op.created_at) >= DATE(?)"
                order_services_date_filter += " AND DATE(os.created_at) >= DATE(?)"
                order_params.append(date_from)
            if date_to:
                order_parts_date_filter += " AND DATE(op.created_at) <= DATE(?)"
                order_services_date_filter += " AND DATE(os.created_at) <= DATE(?)"
                order_params.append(date_to)
            
            # Объединяем продажи из магазина и заявок
            cursor.execute(f'''
                SELECT 
                    part_id,
                    part_name,
                    SUM(total_qty) as total_qty,
                    SUM(total_revenue) as total_revenue,
                    SUM(total_cost) as total_cost,
                    SUM(profit) as profit,
                    CASE 
                        WHEN SUM(total_cost) > 0 
                        THEN (SUM(profit) * 100.0) / SUM(total_cost)
                        ELSE 0 
                    END as margin_percent
                FROM (
                    -- Продажи из магазина
                    SELECT 
                        ssi.part_id,
                        ssi.part_name,
                        SUM(ssi.quantity) as total_qty,
                        SUM(ssi.total) as total_revenue,
                        SUM(ssi.purchase_price * ssi.quantity) as total_cost,
                        SUM(ssi.total) - SUM(ssi.purchase_price * ssi.quantity) as profit
                    FROM shop_sale_items ssi
                    JOIN shop_sales ss ON ssi.shop_sale_id = ss.id
                    WHERE ssi.item_type = 'part' AND ssi.part_id IS NOT NULL {shop_date_filter}
                    GROUP BY ssi.part_id, ssi.part_name
                    
                    UNION ALL
                    
                    -- Продажи из заявок
                    SELECT 
                        op.part_id,
                        p.name as part_name,
                        SUM(op.quantity) as total_qty,
                        SUM(op.price * op.quantity) as total_revenue,
                        SUM(COALESCE(op.purchase_price, p.purchase_price, 0) * op.quantity) as total_cost,
                        SUM(op.price * op.quantity) - SUM(COALESCE(op.purchase_price, p.purchase_price, 0) * op.quantity) as profit
                    FROM order_parts op
                    JOIN orders o ON o.id = op.order_id
                    JOIN parts p ON p.id = op.part_id
                    WHERE (o.hidden = 0 OR o.hidden IS NULL) AND p.is_deleted = 0 {order_parts_date_filter}
                    GROUP BY op.part_id, p.name
                ) AS combined_sales
                GROUP BY part_id, part_name
                ORDER BY total_revenue DESC
                LIMIT ?
            ''', shop_params + order_params + [limit])
            
            columns = [desc[0] for desc in cursor.description]
            top_products = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            # Топ продаж услуг: объединяем продажи из магазина и из заявок
            cursor.execute(f'''
                SELECT 
                    service_id,
                    service_name,
                    SUM(total_qty) as total_qty,
                    SUM(total_revenue) as total_revenue
                FROM (
                    -- Услуги из магазина
                    SELECT 
                        ssi.service_id,
                        ssi.service_name,
                        SUM(ssi.quantity) as total_qty,
                        SUM(ssi.total) as total_revenue
                    FROM shop_sale_items ssi
                    JOIN shop_sales ss ON ssi.shop_sale_id = ss.id
                    WHERE ssi.item_type = 'service' AND ssi.service_id IS NOT NULL {shop_date_filter}
                    GROUP BY ssi.service_id, ssi.service_name
                    
                    UNION ALL
                    
                    -- Услуги из заявок
                    SELECT 
                        os.service_id,
                        s.name as service_name,
                        SUM(os.quantity) as total_qty,
                        SUM(os.price * os.quantity) as total_revenue
                    FROM order_services os
                    JOIN orders o ON o.id = os.order_id
                    JOIN services s ON s.id = os.service_id
                    WHERE (o.hidden = 0 OR o.hidden IS NULL) {order_services_date_filter}
                    GROUP BY os.service_id, s.name
                ) AS combined_services
                GROUP BY service_id, service_name
                ORDER BY total_revenue DESC
                LIMIT ?
            ''', shop_params + order_params + [limit])
            
            columns = [desc[0] for desc in cursor.description]
            top_services = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            # Оборачиваемость (дней на складе до продажи)
            # Упрощенный расчет: средний остаток / среднедневные продажи
            cursor.execute("SELECT AVG(stock_quantity), SUM(stock_quantity * purchase_price) FROM parts WHERE is_deleted = 0 OR is_deleted IS NULL")
            avg_stock_row = cursor.fetchone()
            avg_stock_qty = avg_stock_row[0] or 0
            avg_stock_value = avg_stock_row[1] or 0
            
            # Среднедневные продажи
            if date_from and date_to:
                try:
                    d1 = datetime.strptime(date_from, '%Y-%m-%d')
                    d2 = datetime.strptime(date_to, '%Y-%m-%d')
                    days = (d2 - d1).days or 1
                except (ValueError, TypeError):
                    days = 30
            else:
                days = 30
            
            # Общее количество проданных товаров (из магазина и заявок)
            cursor.execute(f'''
                SELECT SUM(total_qty)
                FROM (
                    SELECT SUM(ssi.quantity) as total_qty
                    FROM shop_sale_items ssi
                    JOIN shop_sales ss ON ssi.shop_sale_id = ss.id
                    WHERE ssi.item_type = 'part' {shop_date_filter}
                    
                    UNION ALL
                    
                    SELECT SUM(op.quantity) as total_qty
                    FROM order_parts op
                    JOIN orders o ON o.id = op.order_id
                    JOIN parts p ON p.id = op.part_id
                    WHERE (o.hidden = 0 OR o.hidden IS NULL) AND p.is_deleted = 0 {order_parts_date_filter}
                ) AS combined
            ''', shop_params + order_params)
            
            total_sold = cursor.fetchone()[0] or 0
            daily_sales = total_sold / days if days > 0 else 0
            turnover_days = avg_stock_qty / daily_sales if daily_sales > 0 else 0
            
            return {
                'top_products': top_products,
                'top_services': top_services,
                'avg_stock_qty': avg_stock_qty,
                'avg_stock_value': avg_stock_value,
                'daily_sales': daily_sales,
                'turnover_days': round(turnover_days, 1),
                'date_from': date_from,
                'date_to': date_to
            }

