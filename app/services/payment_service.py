"""
Сервис для работы с оплатами.
"""
from typing import Optional, Dict, List
from app.database.queries.payment_queries import PaymentQueries
from app.utils.exceptions import ValidationError, NotFoundError, DatabaseError
from app.database.connection import get_db_connection
from datetime import date, datetime
from app.utils.datetime_utils import get_moscow_now_str, get_moscow_now
import sqlite3
import logging

logger = logging.getLogger(__name__)


class PaymentService:
    """Сервис для работы с оплатами."""
    
    @staticmethod
    def get_order_payments(order_id: int) -> List[Dict]:
        """
        Получает все оплаты по заявке.
        
        Args:
            order_id: ID заявки
            
        Returns:
            Список оплат
        """
        if not order_id or order_id <= 0:
            raise ValidationError("Неверный ID заявки")
        
        return PaymentQueries.get_order_payments(order_id)
    
    @staticmethod
    def get_customer_payments(customer_id: int, limit: int = 50) -> List[Dict]:
        """
        Получает все оплаты клиента.
        
        Args:
            customer_id: ID клиента
            limit: Максимальное количество записей
            
        Returns:
            Список оплат
        """
        if not customer_id or customer_id <= 0:
            raise ValidationError("Неверный ID клиента")
        
        return PaymentQueries.get_customer_payments(customer_id, limit)
    
    @staticmethod
    def add_payment(
        order_id: int,
        amount: float,
        payment_type: str,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        comment: Optional[str] = None,
        kind: str = "payment",
        status: str = "captured",
        idempotency_key: Optional[str] = None
    ) -> int:
        """
        Добавляет оплату к заявке.
        
        Args:
            order_id: ID заявки
            amount: Сумма оплаты
            payment_type: Тип оплаты (cash, card, transfer)
            user_id: ID пользователя
            username: Имя пользователя
            comment: Комментарий
            
        Returns:
            ID созданной оплаты
            
        Raises:
            ValidationError: Если данные невалидны
            NotFoundError: Если заявка не найдена
            DatabaseError: Если произошла ошибка БД
        """
        if not order_id or order_id <= 0:
            raise ValidationError("Неверный ID заявки")
        
        if amount <= 0:
            raise ValidationError("Сумма оплаты должна быть больше нуля")
        
        if payment_type not in ['cash', 'card', 'transfer', 'wallet']:
            raise ValidationError("Неверный тип оплаты")

        allowed_kinds = {"payment", "deposit", "refund", "adjustment"}
        if kind not in allowed_kinds:
            raise ValidationError("Неверный тип платежа (kind)")

        allowed_statuses = {"pending", "captured", "cancelled", "refunded"}
        if status not in allowed_statuses:
            raise ValidationError("Неверный статус платежа (status)")
        
        # Проверяем существование заявки
        from app.services.order_service import OrderService
        order = OrderService.get_order(order_id)
        if not order:
            raise NotFoundError(f"Заявка с ID {order_id} не найдена")
        
        # Получаем display_name из user_id, если не передан
        if not username and user_id:
            try:
                from app.services.user_service import UserService
                username = UserService.get_user_display_name(user_id)
            except Exception as e:
                logger.warning(f"Не удалось получить display_name для user_id {user_id}: {e}")
                username = f"User_{user_id}"
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()

                # Если есть idempotency_key — возвращаем уже созданную оплату
                if idempotency_key:
                    try:
                        cursor.execute(
                            """
                            SELECT id FROM payments
                            WHERE idempotency_key = ?
                              AND TRIM(idempotency_key) != ''
                            LIMIT 1
                            """,
                            (idempotency_key.strip(),),
                        )
                        existing = cursor.fetchone()
                        if existing:
                            return int(existing[0])
                    except Exception:
                        # если колонки ещё нет — просто игнорируем
                        pass
                
                # Определяем, есть ли новые колонки (миграция 027)
                cursor.execute("PRAGMA table_info(payments)")
                cols = [r[1] for r in cursor.fetchall()]
                has_kind = "kind" in cols
                has_status = "status" in cols
                has_idem = "idempotency_key" in cols
                has_captured_at = "captured_at" in cols

                # Используем московское время (UTC+3), как у заявок и начислений — иначе оплаты на 3 ч раньше
                now_moscow = get_moscow_now_str()
                insert_cols = [
                    "order_id", "amount", "payment_type",
                    "created_by", "created_by_username", "comment",
                ]
                values = [order_id, amount, payment_type, user_id, username, comment]

                if has_kind:
                    insert_cols.append("kind")
                    values.append(kind)
                if has_status:
                    insert_cols.append("status")
                    values.append(status)
                if has_idem:
                    insert_cols.append("idempotency_key")
                    values.append(idempotency_key.strip() if idempotency_key else None)
                if has_captured_at:
                    insert_cols.append("captured_at")
                    values.append(now_moscow if status == "captured" else None)

                insert_cols.extend(["payment_date", "created_at"])
                values.extend([now_moscow, now_moscow])

                placeholders = ", ".join(["?"] * len(values))
                cols_sql = ", ".join(insert_cols)

                # Создаем оплату
                cursor.execute(
                    f"""
                    INSERT INTO payments ({cols_sql})
                    VALUES ({placeholders})
                    """,
                    tuple(values),
                )
                
                payment_id = cursor.lastrowid
                
                # Автоматически создаем кассовую операцию через FinanceService
                try:
                    from app.services.finance_service import FinanceService

                    # Оплата с депозита клиента не должна создавать кассовую операцию
                    if payment_type == 'wallet':
                        # Получаем customer_id из заявки
                        cursor.execute('SELECT customer_id FROM orders WHERE id = ?', (order_id,))
                        customer_row = cursor.fetchone()
                        customer_id = customer_row[0] if customer_row else None
                        
                        conn.commit()  # Коммитим оплату перед списанием с кошелька
                        
                        # Списываем с кошелька клиента (использует свой connection)
                        if customer_id:
                            try:
                                from app.services.wallet_service import WalletService
                                WalletService.debit(
                                    customer_id=customer_id,
                                    amount=amount,
                                    source='payment',
                                    order_id=order_id,
                                    payment_id=payment_id,
                                    comment=comment or "Оплата с депозита",
                                    created_by_id=user_id,
                                    created_by_username=username
                                )
                            except Exception as e:
                                logger.error(f"Ошибка при списании с кошелька для оплаты {payment_id}: {e}")
                                raise DatabaseError(f"Не удалось списать средства с кошелька: {e}")
                        
                        return payment_id
                    
                    # Получаем информацию о заявке для описания
                    cursor.execute('''
                        SELECT o.id, o.order_id, c.name as client_name
                        FROM orders o
                        LEFT JOIN customers c ON o.customer_id = c.id
                        WHERE o.id = ?
                    ''', (order_id,))
                    order_info = cursor.fetchone()
                    
                    # Формируем описание транзакции (используем внутренний ID заявки, не UUID)
                    if order_info:
                        display_order_id = order_info[0]
                        if kind == "deposit":
                            description = f"Предоплата по заявке #{display_order_id}"
                        else:
                            description = f"Оплата по заявке #{display_order_id}"
                        if order_info[2]:
                            description += f" ({order_info[2]})"
                    else:
                        description = f"Предоплата по заявке #{order_id}" if kind == "deposit" else f"Оплата по заявке #{order_id}"
                    
                    if comment:
                        description += f". {comment}"
                    
                    # Маппинг типов оплаты
                    payment_method_map = {'cash': 'cash', 'card': 'card', 'transfer': 'transfer'}
                    payment_method = payment_method_map.get(payment_type, 'cash')

                    # Категория для кассы:
                    # - deposit -> "Предоплата"
                    # - остальное -> "Оплата по заявке"
                    category_name = 'Предоплата' if kind == 'deposit' else 'Оплата по заявке'
                    
                    # Получаем дату оплаты
                    cursor.execute('SELECT payment_date FROM payments WHERE id = ?', (payment_id,))
                    payment_date_row = cursor.fetchone()
                    raw_dt = payment_date_row[0] if payment_date_row else get_moscow_now().date().isoformat()
                    transaction_date = raw_dt[:10] if isinstance(raw_dt, str) and len(raw_dt) >= 10 else get_moscow_now().date().isoformat()
                    
                    conn.commit()  # Коммит перед вызовом внешнего сервиса
                    
                    # Создаём кассовую операцию через единый сервис (защита от дублей внутри)
                    FinanceService.create_transaction(
                        category_name=category_name,
                        amount=amount,
                        transaction_type='income',
                        payment_method=payment_method,
                        description=description,
                        order_id=order_id,
                        payment_id=payment_id,
                        transaction_date=transaction_date,
                        created_by_id=user_id,
                        created_by_username=username
                    )
                    
                    logger.info(f"Создана кассовая операция для оплаты {payment_id} заявки {order_id}")
                except Exception as e:
                    # Логируем ошибку, но не прерываем создание оплаты
                    logger.error(f"Ошибка при создании кассовой операции для оплаты {payment_id}: {e}")
                
                # Логируем создание оплаты (после commit, чтобы избежать блокировки БД)
                try:
                    from app.services.action_log_service import ActionLogService
                    ActionLogService.log_action(
                        user_id=user_id,
                        username=username,
                        action_type='create',
                        entity_type='payment',
                        entity_id=payment_id,
                        description=f"Создана оплата по заявке #{order_id}: {amount:.2f} руб ({payment_type})",
                        details={
                            'ID заявки': order_id,
                            'Сумма': f"{amount:.2f} ₽",
                            'Тип оплаты': payment_type,
                            'Комментарий': comment
                        }
                    )
                except Exception as e:
                    logger.warning(f"Не удалось залогировать создание оплаты: {e}")
                
                # Очищаем кэш
                from app.utils.cache import clear_cache
                clear_cache(key_prefix='order')
                clear_cache(key_prefix='finance')
                
                return payment_id
        except sqlite3.Error as e:
            logger.error(f"Ошибка БД при добавлении оплаты к заявке {order_id}: {e}")
            raise DatabaseError(f"Ошибка базы данных: {e}")
        except Exception as e:
            logger.error(f"Неожиданная ошибка при добавлении оплаты: {e}")
            raise DatabaseError(f"Ошибка при добавлении оплаты: {e}")
    
    @staticmethod
    def cancel_payment(
        payment_id: int,
        reason: str = None,
        user_id: int = None,
        username: str = None
    ) -> bool:
        """
        Отменяет оплату (soft-delete) и создаёт сторно-операцию в кассе.
        
        Вместо физического удаления помечает оплату как отменённую и
        создаёт компенсирующую (сторно) запись в кассе.
        
        Args:
            payment_id: ID оплаты
            reason: Причина отмены
            user_id: ID пользователя, отменившего оплату
            username: Имя пользователя
            
        Returns:
            True если успешно
            
        Raises:
            ValidationError: Если данные невалидны
            NotFoundError: Если оплата не найдена
            DatabaseError: Если произошла ошибка БД
        """
        if not payment_id or payment_id <= 0:
            raise ValidationError("Неверный ID оплаты")
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Получаем информацию об оплате
                cursor.execute('''
                    SELECT p.id, p.order_id, p.amount, p.payment_type, p.is_cancelled,
                           o.order_id as order_number, c.name as client_name
                    FROM payments p
                    LEFT JOIN orders o ON p.order_id = o.id
                    LEFT JOIN customers c ON o.customer_id = c.id
                    WHERE p.id = ?
                ''', (payment_id,))
                payment_row = cursor.fetchone()
                
                if not payment_row:
                    raise NotFoundError(f"Оплата с ID {payment_id} не найдена")
                
                # Проверяем, не отменена ли уже
                if payment_row[4]:  # is_cancelled
                    raise ValidationError("Оплата уже отменена")
                
                order_id = payment_row[1]
                amount = float(payment_row[2])
                payment_type = payment_row[3]
                order_number = payment_row[5] or payment_row[1]
                client_name = payment_row[6] or ''
                
                now = get_moscow_now_str()
                
                # 1. Помечаем оплату как отменённую (soft-delete)
                cursor.execute('''
                    UPDATE payments SET 
                        is_cancelled = 1,
                        cancelled_at = ?,
                        cancelled_reason = ?,
                        cancelled_by_id = ?,
                        cancelled_by_username = ?
                    WHERE id = ?
                ''', (now, reason, user_id, username, payment_id))
                
                # 2. Находим связанную кассовую операцию и помечаем как отменённую
                cursor.execute('''
                    SELECT id, category_id, amount, payment_method 
                    FROM cash_transactions 
                    WHERE payment_id = ? AND (is_cancelled = 0 OR is_cancelled IS NULL)
                    LIMIT 1
                ''', (payment_id,))
                cash_row = cursor.fetchone()
                
                if cash_row:
                    original_tx_id = cash_row[0]
                    category_id = cash_row[1]
                    tx_amount = float(cash_row[2])
                    payment_method = cash_row[3]
                    
                    # Помечаем оригинальную операцию как отменённую
                    cursor.execute('''
                        UPDATE cash_transactions SET 
                            is_cancelled = 1,
                            cancelled_at = ?,
                            cancelled_reason = ?,
                            cancelled_by_id = ?,
                            cancelled_by_username = ?
                        WHERE id = ?
                    ''', (now, reason, user_id, username, original_tx_id))
                    
                    # 3. Создаём сторно-операцию (отрицательная сумма для компенсации)
                    storno_description = f"СТОРНО: Отмена оплаты по заявке #{order_number}"
                    if client_name:
                        storno_description += f" ({client_name})"
                    if reason:
                        storno_description += f". Причина: {reason}"
                    
                    # Используем FinanceService для создания сторно-операции (внутренний метод для работы с существующим cursor)
                    from app.services.finance_service import FinanceService
                    FinanceService._create_transaction_with_cursor(
                        cursor=cursor,
                        amount=tx_amount,
                        transaction_type='expense',
                        category_id=category_id,
                        payment_method=payment_method,
                        description=storno_description,
                        order_id=order_id,
                        # payment_id уникален в cash_transactions, поэтому у сторно он должен быть пустым
                        payment_id=None,
                        transaction_date=get_moscow_now().date().isoformat(),
                        created_by_id=user_id,
                        created_by_username=username,
                        storno_of_id=original_tx_id
                    )
                    
                    logger.info(f"Создана сторно-операция для отмены оплаты {payment_id}")
                
                conn.commit()
                
                # Логируем отмену оплаты
                try:
                    from app.services.action_log_service import ActionLogService
                    ActionLogService.log_action(
                        user_id=user_id,
                        username=username,
                        action_type='cancel',
                        entity_type='payment',
                        entity_id=payment_id,
                        description=f"Отменена оплата #{payment_id} по заявке #{order_number}: {amount:.2f} руб",
                        details={
                            'ID заявки': order_id,
                            'Номер заявки': order_number,
                            'Сумма': f"{amount:.2f} ₽",
                            'Тип оплаты': payment_type,
                            'Причина отмены': reason or 'Не указана'
                        }
                    )
                except Exception as e:
                    logger.warning(f"Не удалось залогировать отмену оплаты: {e}")
                
                # Очищаем кэш
                from app.utils.cache import clear_cache
                clear_cache(key_prefix='order')
                clear_cache(key_prefix='finance')

                try:
                    from app.services.salary_service import SalaryService
                    SalaryService.sync_accruals_after_order_payment_change(order_id)
                except Exception as e:
                    logger.warning(
                        "После отмены оплаты не удалось синхронизировать зарплату по заявке %s: %s",
                        order_id,
                        e,
                    )
                
                return True
        except (ValidationError, NotFoundError):
            raise
        except sqlite3.Error as e:
            logger.error(f"Ошибка БД при отмене оплаты {payment_id}: {e}")
            raise DatabaseError(f"Ошибка базы данных: {e}")
        except Exception as e:
            logger.error(f"Неожиданная ошибка при отмене оплаты: {e}")
            raise DatabaseError(f"Ошибка при отмене оплаты: {e}")

    @staticmethod
    def refund_payment(
        original_payment_id: int,
        amount: float,
        reason: str,
        user_id: int = None,
        username: str = None,
        create_cash_transaction: bool = True
    ) -> int:
        """
        Создаёт возврат (refund) как отдельную запись payments(kind='refund') и кассовый расход.

        Возврат НЕ удаляет исходную оплату и не делает сторно исходной кассовой операции.
        Это отдельная финансовая операция.
        """
        if not original_payment_id or original_payment_id <= 0:
            raise ValidationError("Неверный ID исходной оплаты")
        try:
            amount = float(amount)
        except Exception:
            raise ValidationError("Неверная сумма возврата")
        if amount <= 0:
            raise ValidationError("Сумма возврата должна быть больше нуля")
        if not reason or not str(reason).strip():
            raise ValidationError("Укажите причину возврата")

        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()

                # Проверяем исходную оплату
                cursor.execute("PRAGMA table_info(payments)")
                cols = [r[1] for r in cursor.fetchall()]
                has_kind = "kind" in cols
                has_status = "status" in cols
                has_refunded_of = "refunded_of_id" in cols

                # Берём исходную оплату. Если есть kind — также читаем его, чтобы запретить refund от refund.
                if has_kind:
                    cursor.execute(
                        """
                        SELECT id, order_id, amount, payment_type, comment,
                               COALESCE(is_cancelled, 0) AS is_cancelled,
                               kind
                        FROM payments
                        WHERE id = ?
                        """,
                        (original_payment_id,),
                    )
                else:
                    cursor.execute(
                        """
                        SELECT id, order_id, amount, payment_type, comment,
                               COALESCE(is_cancelled, 0) AS is_cancelled
                        FROM payments
                        WHERE id = ?
                        """,
                        (original_payment_id,),
                    )
                row = cursor.fetchone()
                if not row:
                    raise NotFoundError("Исходная оплата не найдена")
                if row[5]:
                    raise ValidationError("Нельзя делать возврат по отменённой оплате")

                order_id = int(row[1])
                original_amount = float(row[2] or 0)
                payment_type = row[3] or "cash"
                original_kind = None
                if has_kind:
                    original_kind = row[6]
                    if original_kind == "refund":
                        raise ValidationError("Нельзя делать возврат по возврату")

                # Ограничение: суммарные возвраты не могут превышать исходную сумму
                already_refunded = 0.0
                if has_refunded_of and has_kind:
                    if has_status:
                        cursor.execute(
                            """
                            SELECT COALESCE(SUM(amount), 0)
                            FROM payments
                            WHERE refunded_of_id = ?
                              AND kind = 'refund'
                              AND (is_cancelled = 0 OR is_cancelled IS NULL)
                              AND status = 'captured'
                            """,
                            (original_payment_id,),
                        )
                    else:
                        cursor.execute(
                            """
                            SELECT COALESCE(SUM(amount), 0)
                            FROM payments
                            WHERE refunded_of_id = ?
                              AND kind = 'refund'
                              AND (is_cancelled = 0 OR is_cancelled IS NULL)
                            """,
                            (original_payment_id,),
                        )
                    already_refunded = float((cursor.fetchone() or [0])[0] or 0)

                remaining = original_amount - already_refunded
                if remaining <= 0:
                    raise ValidationError("По этой оплате уже выполнен полный возврат")
                if amount > remaining:
                    raise ValidationError(f"Сумма возврата не может превышать остаток {remaining:.2f} ₽")

                # Создаём запись возврата в payments (amount положительный, знак учитываем в totals через kind)
                insert_cols = [
                    "order_id", "amount", "payment_type",
                    "created_by", "created_by_username", "comment",
                ]
                values = [
                    order_id, amount, payment_type,
                    user_id, username, f"ВОЗВРАТ: {str(reason).strip()} (по оплате #{original_payment_id})",
                ]
                if has_kind:
                    insert_cols.append("kind")
                    values.append("refund")
                if has_status:
                    insert_cols.append("status")
                    values.append("captured")
                if has_refunded_of:
                    insert_cols.append("refunded_of_id")
                    values.append(original_payment_id)

                placeholders = ", ".join(["?"] * len(values))
                cols_sql = ", ".join(insert_cols)
                now_moscow = get_moscow_now_str()
                cursor.execute(
                    f"""
                    INSERT INTO payments ({cols_sql}, payment_date, created_at)
                    VALUES ({placeholders}, ?, ?)
                    """,
                    (*tuple(values), now_moscow, now_moscow),
                )
                refund_payment_id = int(cursor.lastrowid)

                # Кассовый расход создаём только если это реальный возврат денег.
                # Для "возврата в депозит клиента" cash out не нужен.
                if create_cash_transaction:
                    from app.services.finance_service import FinanceService
                    payment_method_map = {"cash": "cash", "card": "card", "transfer": "transfer"}
                    payment_method = payment_method_map.get(payment_type, "cash")

                    # Дата возврата — сегодня по Москве
                    transaction_date = get_moscow_now_str('%Y-%m-%d')

                    conn.commit()  # до вызова сервиса

                    FinanceService.create_transaction(
                        amount=amount,
                        transaction_type="expense",
                        category_name="Возврат по заявке",
                        payment_method=payment_method,
                        description=f"Возврат по оплате #{original_payment_id}. {str(reason).strip()}",
                        order_id=order_id,
                        payment_id=refund_payment_id,
                        transaction_date=transaction_date,
                        created_by_id=user_id,
                        created_by_username=username,
                    )
                else:
                    conn.commit()

                # Логируем
                try:
                    from app.services.action_log_service import ActionLogService
                    ActionLogService.log_action(
                        user_id=user_id,
                        username=username,
                        action_type="refund",
                        entity_type="payment",
                        entity_id=refund_payment_id,
                        description=f"Возврат {amount:.2f} руб по оплате #{original_payment_id} (заявка #{order_id})",
                        details={
                            "ID заявки": order_id,
                            "ID исходной оплаты": original_payment_id,
                            "ID возврата": refund_payment_id,
                            "Сумма": f"{amount:.2f} ₽",
                            "Причина": str(reason).strip(),
                        },
                    )
                except Exception as e:
                    logger.warning(f"Не удалось залогировать возврат: {e}")

                from app.utils.cache import clear_cache
                clear_cache(key_prefix="order")
                clear_cache(key_prefix="finance")

                try:
                    from app.services.salary_service import SalaryService
                    SalaryService.sync_accruals_after_order_payment_change(order_id)
                except Exception as e:
                    logger.warning(
                        "После возврата оплаты не удалось синхронизировать зарплату по заявке %s: %s",
                        order_id,
                        e,
                    )

                return refund_payment_id
        except (ValidationError, NotFoundError):
            raise
        except sqlite3.Error as e:
            logger.error(f"Ошибка БД при возврате оплаты {original_payment_id}: {e}")
            raise DatabaseError(f"Ошибка базы данных: {e}")
        except Exception as e:
            logger.error(f"Неожиданная ошибка при возврате оплаты: {e}")
            raise DatabaseError(f"Ошибка при возврате оплаты: {e}")
    
    @staticmethod
    def delete_payment(payment_id: int, user_id: int = None, username: str = None, reason: str = None) -> bool:
        """
        Отменяет оплату (обёртка над cancel_payment для обратной совместимости).
        
        ВАЖНО: Физическое удаление заменено на soft-delete + сторно.
        
        Args:
            payment_id: ID оплаты
            user_id: ID пользователя
            username: Имя пользователя
            reason: Причина отмены
            
        Returns:
            True если успешно
        """
        return PaymentService.cancel_payment(
            payment_id=payment_id,
            reason=reason or "Удаление оплаты",
            user_id=user_id,
            username=username
        )
    
    @staticmethod
    def get_payment_statistics(
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        payment_type: Optional[str] = None
    ) -> Dict:
        """
        Получает статистику по оплатам.
        
        Args:
            start_date: Дата начала (YYYY-MM-DD)
            end_date: Дата окончания (YYYY-MM-DD)
            payment_type: Тип оплаты
            
        Returns:
            Словарь со статистикой
        """
        return PaymentQueries.get_payment_statistics(start_date, end_date, payment_type)

