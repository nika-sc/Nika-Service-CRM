"""
Сервис для расчета и начисления зарплаты.
"""
from typing import Dict, List, Optional, Any, Tuple
from app.database.queries.salary_queries import SalaryQueries
from app.database.queries.status_queries import StatusQueries
from app.database.connection import get_db_connection
from app.utils.exceptions import ValidationError, NotFoundError, DatabaseError
from app.utils.error_handlers import handle_service_error
from app.services.action_log_service import ActionLogService
import sqlite3
import logging

logger = logging.getLogger(__name__)


class SalaryService:
    """Сервис для работы с зарплатой."""
    
    @staticmethod
    def _get_vat_settings() -> Tuple[bool, float]:
        """
        Получает настройки НДС из system_settings.
        
        Returns:
            (vat_enabled, vat_rate)
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT value FROM system_settings WHERE key = ?', ('vat_enabled',))
                row = cursor.fetchone()
                vat_enabled = int(row[0]) == 1 if row else False
                
                cursor.execute('SELECT value FROM system_settings WHERE key = ?', ('vat_rate',))
                row = cursor.fetchone()
                vat_rate = float(row[0]) if row else 20.0
                
                return vat_enabled, vat_rate
        except Exception as e:
            logger.warning(f"Ошибка при получении настроек НДС: {e}, используем значения по умолчанию")
            return False, 20.0
    
    @staticmethod
    def calculate_order_profit(order_id: int, vat_enabled: Optional[bool] = None, vat_rate: Optional[float] = None) -> Dict[str, Any]:
        """
        Рассчитывает прибыль заявки.
        
        Формула: Прибыль = Сумма платежей - Себестоимость (товары + услуги)
        Если НДС включен: Прибыль = (Сумма платежей / (1 + НДС/100)) - Себестоимость
        
        Args:
            order_id: ID заявки
            vat_enabled: Учитывать НДС (если None, берется из настроек)
            vat_rate: Ставка НДС (если None, берется из настроек)
            
        Returns:
            Словарь с данными:
            - total_payments_cents: Сумма всех платежей в копейках
            - total_parts_cost_cents: Себестоимость запчастей в копейках (для обратной совместимости)
            - profit_cents: Прибыль в копейках (рассчитана с учетом товаров И услуг)
            - vat_enabled: Учитывался ли НДС
            - vat_rate: Ставка НДС
        """
        if vat_enabled is None or vat_rate is None:
            vat_enabled, vat_rate = SalaryService._get_vat_settings()
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Проверяем наличие колонки kind для определения возвратов
                cursor.execute("PRAGMA table_info(payments)")
                payment_columns = [row[1] for row in cursor.fetchall()]
                has_kind = 'kind' in payment_columns
                has_status = 'status' in payment_columns
                
                # Сумма всех платежей по заявке (возвраты вычитаются)
                if has_kind:
                    # Новая схема: kind='refund' учитываем со знаком минус
                    if has_status:
                        cursor.execute('''
                            SELECT COALESCE(SUM(
                                CASE WHEN kind = 'refund' THEN -amount ELSE amount END
                            ), 0) as total
                            FROM payments
                            WHERE order_id = ?
                              AND (is_cancelled = 0 OR is_cancelled IS NULL)
                              AND status = 'captured'
                        ''', (order_id,))
                    else:
                        cursor.execute('''
                            SELECT COALESCE(SUM(
                                CASE WHEN kind = 'refund' THEN -amount ELSE amount END
                            ), 0) as total
                            FROM payments
                            WHERE order_id = ?
                              AND (is_cancelled = 0 OR is_cancelled IS NULL)
                        ''', (order_id,))
                else:
                    # Legacy: без kind, считаем всё как оплату
                    cursor.execute('''
                        SELECT COALESCE(SUM(amount), 0) as total
                        FROM payments
                        WHERE order_id = ?
                          AND (is_cancelled = 0 OR is_cancelled IS NULL)
                    ''', (order_id,))
                
                row = cursor.fetchone()
                total_payments = float(row[0] or 0)
                total_payments_cents = int(total_payments * 100)
                
                # Себестоимость запчастей (purchase_price * quantity)
                cursor.execute('''
                    SELECT COALESCE(SUM(COALESCE(purchase_price, 0) * quantity), 0) as total
                    FROM order_parts
                    WHERE order_id = ?
                ''', (order_id,))
                row = cursor.fetchone()
                total_parts_cost = float(row[0] or 0)
                
                # Себестоимость услуг (cost_price * quantity)
                cursor.execute('''
                    SELECT COALESCE(SUM(COALESCE(cost_price, 0) * quantity), 0) as total
                    FROM order_services
                    WHERE order_id = ?
                ''', (order_id,))
                row = cursor.fetchone()
                total_services_cost = float(row[0] or 0)
                
                # Общая себестоимость (товары + услуги)
                total_cost = total_parts_cost + total_services_cost
                total_parts_cost_cents = int(total_parts_cost * 100)
                total_cost_cents = int(total_cost * 100)
                
                # Расчет прибыли
                if vat_enabled:
                    # Прибыль = (Сумма платежей / (1 + НДС/100)) - Себестоимость (товары + услуги)
                    payments_without_vat = total_payments / (1 + vat_rate / 100)
                    profit = payments_without_vat - total_cost
                else:
                    # Прибыль = Сумма платежей - Себестоимость (товары + услуги)
                    profit = total_payments - total_cost
                
                profit_cents = int(profit * 100)

                # Не логируем в action_logs — расчёт прибыли вызывается массово (N заявок)
                # и засорял бы логи. Для отладки используйте logger.debug.

                return {
                    'total_payments_cents': total_payments_cents,
                    'total_parts_cost_cents': total_parts_cost_cents,
                    'total_services_cost_cents': int(total_services_cost * 100),
                    'total_cost_cents': total_cost_cents,
                    'profit_cents': profit_cents,
                    'vat_enabled': vat_enabled,
                    'vat_rate': vat_rate
                }
        except Exception as e:
            logger.error(f"Ошибка при расчете прибыли заявки {order_id}: {e}", exc_info=True)
            raise DatabaseError(f"Ошибка при расчете прибыли: {e}")
    
    @staticmethod
    def _get_salary_rule(
        cursor,
        scope: str,
        scope_id: Optional[int] = None,
        item_type: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Получает правило зарплаты для указанного scope.
        
        Args:
            cursor: Курсор БД
            scope: 'service', 'part', 'master', 'manager', 'status'
            scope_id: ID услуги/товара/мастера/менеджера/статуса
            item_type: 'service', 'part', 'shop_part' — для master/manager выбирает процент
                       по типу (salary_percent_services, salary_percent_parts, salary_percent_shop_parts)
            
        Returns:
            Словарь с правилом или None
        """
        if scope == 'service' and scope_id:
            cursor.execute('''
                SELECT salary_rule_type, salary_rule_value
                FROM services
                WHERE id = ? AND salary_rule_type IS NOT NULL
            ''', (scope_id,))
            row = cursor.fetchone()
            if row:
                return {'rule_type': row[0], 'rule_value': float(row[1])}
        
        elif scope == 'part' and scope_id:
            cursor.execute('''
                SELECT salary_rule_type, salary_rule_value
                FROM parts
                WHERE id = ? AND salary_rule_type IS NOT NULL
            ''', (scope_id,))
            row = cursor.fetchone()
            if row:
                return {'rule_type': row[0], 'rule_value': float(row[1])}
        
        elif scope == 'master' and scope_id:
            cursor.execute('''
                SELECT salary_rule_type, salary_rule_value,
                       salary_percent_services, salary_percent_parts, salary_percent_shop_parts
                FROM masters WHERE id = ?
            ''', (scope_id,))
            row = cursor.fetchone()
            if row:
                p_svc, p_pt, p_shop = row[2], row[3], row[4]
                if item_type == 'service' and p_svc is not None:
                    return {'rule_type': 'percent', 'rule_value': float(p_svc)}
                if item_type == 'part' and p_pt is not None:
                    return {'rule_type': 'percent', 'rule_value': float(p_pt)}
                if item_type == 'shop_part' and p_shop is not None:
                    return {'rule_type': 'percent', 'rule_value': float(p_shop)}
                if row[0] and row[1] is not None:
                    return {'rule_type': row[0], 'rule_value': float(row[1])}
        
        elif scope == 'manager' and scope_id:
            try:
                cursor.execute('''
                    SELECT salary_rule_type, salary_rule_value,
                           salary_percent_services, salary_percent_parts, salary_percent_shop_parts,
                           COALESCE(salary_rule_base, 'profit') as salary_rule_base
                    FROM managers WHERE id = ?
                ''', (scope_id,))
            except Exception:
                # Для PostgreSQL после SQL-ошибки транзакция помечается failed.
                # Откатываем, чтобы fallback-запрос выполнился корректно.
                try:
                    cursor.connection.rollback()
                except Exception:
                    pass
                cursor.execute('''
                    SELECT salary_rule_type, salary_rule_value,
                           salary_percent_services, salary_percent_parts, salary_percent_shop_parts
                    FROM managers WHERE id = ?
                ''', (scope_id,))
            row = cursor.fetchone()
            if row:
                p_svc, p_pt, p_shop = row[2], row[3], row[4]
                rule_base = (row[5] or 'profit').strip().lower() if len(row) > 5 else 'profit'
                if item_type == 'service' and p_svc is not None:
                    return {'rule_type': 'percent', 'rule_value': float(p_svc), 'rule_base': rule_base}
                if item_type == 'part' and p_pt is not None:
                    return {'rule_type': 'percent', 'rule_value': float(p_pt), 'rule_base': rule_base}
                if item_type == 'shop_part' and p_shop is not None:
                    return {'rule_type': 'percent', 'rule_value': float(p_shop), 'rule_base': rule_base}
                if row[0] and row[1] is not None:
                    return {'rule_type': row[0], 'rule_value': float(row[1]), 'rule_base': rule_base}
        
        elif scope == 'status' and scope_id:
            cursor.execute('''
                SELECT salary_rule_type, salary_rule_value
                FROM order_statuses
                WHERE id = ? AND salary_rule_type IS NOT NULL
            ''', (scope_id,))
            row = cursor.fetchone()
            if row:
                return {'rule_type': row[0], 'rule_value': float(row[1])}
        
        return None
    
    @staticmethod
    def calculate_salary_for_order(order_id: int) -> List[Dict[str, Any]]:
        """
        Рассчитывает зарплату для всех позиций заявки.
        
        Зарплата считается только из услуг и товаров, добавленных в заявку и проведённых
        через закрытие (статус с accrues_salary). Начисление выполняется при смене статуса.
        Требуется полная оплата заявки (без долга и переплаты).
        
        Приоритет правил:
        1. Правило услуги/товара (если есть)
        2. Правило исполнителя (executor_id)
        3. Правило мастера заявки (master_id)
        4. Правило менеджера заявки (manager_id)
        5. Правило статуса (status_id)
        
        Returns:
            Список начислений (для записи в БД)
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Получаем данные заявки
                cursor.execute('''
                    SELECT id, master_id, manager_id, status_id
                    FROM orders
                    WHERE id = ?
                ''', (order_id,))
                order_row = cursor.fetchone()
                if not order_row:
                    raise NotFoundError(f"Заявка с ID {order_id} не найдена")
                
                order_master_id = order_row[1]
                order_manager_id = order_row[2]
                order_status_id = order_row[3]
                
                # Рассчитываем прибыль заявки
                profit_data = SalaryService.calculate_order_profit(order_id)
                total_profit_cents = profit_data['profit_cents']
                total_payments_cents = int(profit_data.get('total_payments_cents') or 0)
                
                if total_profit_cents <= 0:
                    logger.info(f"Прибыль заявки {order_id} <= 0, зарплата не начисляется")
                    return []
                
                # Зарплата начисляется только при полной оплате заявки
                cursor.execute('''
                    SELECT
                        (SELECT COALESCE(SUM(price * quantity), 0) FROM order_services WHERE order_id = ?) +
                        (SELECT COALESCE(SUM(price * quantity), 0) FROM order_parts WHERE order_id = ?)
                ''', (order_id, order_id))
                row = cursor.fetchone()
                order_total_revenue_cents = int((float(row[0] or 0) * 100))
                if order_total_revenue_cents > 0 and total_payments_cents < order_total_revenue_cents:
                    logger.info(f"Заявка {order_id} оплачена не полностью ({total_payments_cents/100:.0f} < {order_total_revenue_cents/100:.0f}), зарплата не начисляется")
                    return []
                
                # Получаем все позиции заявки (услуги и товары)
                accruals = []
                
                # Услуги
                cursor.execute('''
                    SELECT id, service_id, quantity, price, cost_price, executor_id
                    FROM order_services
                    WHERE order_id = ?
                ''', (order_id,))
                services = cursor.fetchall()
                
                for service_row in services:
                    service_item_id, service_id, quantity, price, cost_price, executor_id = service_row
                    quantity = quantity or 1
                    price = float(price or 0)
                    cost_price = float(cost_price or 0)
                    
                    # Прибыль по позиции = (price * quantity) - (cost_price * quantity)
                    item_profit = (price * quantity) - (cost_price * quantity)
                    item_profit_cents = int(item_profit * 100)
                    
                    if item_profit_cents <= 0:
                        continue
                    
                    # Определяем правило (приоритет)
                    rule = None
                    calculated_from = None
                    calculated_from_id = None
                    
                    # Приоритет 1: Правило услуги
                    if service_id:
                        rule = SalaryService._get_salary_rule(cursor, 'service', service_id)
                        if rule:
                            calculated_from = 'service'
                            calculated_from_id = service_id
                    
                    # Приоритет 2: Правило исполнителя
                    if not rule and executor_id:
                        rule = SalaryService._get_salary_rule(cursor, 'master', executor_id, item_type='service')
                        if rule:
                            calculated_from = 'master'
                            calculated_from_id = executor_id
                    
                    # Приоритет 3: Правило мастера заявки
                    if not rule and order_master_id:
                        rule = SalaryService._get_salary_rule(cursor, 'master', order_master_id, item_type='service')
                        if rule:
                            calculated_from = 'master'
                            calculated_from_id = order_master_id
                    
                    # Приоритет 4: Правило менеджера заявки
                    if not rule and order_manager_id:
                        rule = SalaryService._get_salary_rule(cursor, 'manager', order_manager_id, item_type='service')
                        if rule:
                            calculated_from = 'manager'
                            calculated_from_id = order_manager_id
                    
                    # Приоритет 5: Правило статуса
                    if not rule and order_status_id:
                        rule = SalaryService._get_salary_rule(cursor, 'status', order_status_id)
                        if rule:
                            calculated_from = 'status'
                            calculated_from_id = order_status_id
                    
                    if not rule:
                        continue
                    
                    # Расчет зарплаты
                    # Услуги и товары хранят фикс в рублях (Настройки), мастер/менеджер/статус — в копейках (Сотрудники)
                    if rule['rule_type'] == 'percent':
                        salary_cents = int(item_profit_cents * rule['rule_value'] / 100)
                        rule_value_stored = rule['rule_value']
                    elif rule['rule_type'] == 'fixed':
                        if calculated_from in ('service', 'part'):
                            # Фикс за единицу: умножаем на количество
                            salary_cents = int(round(float(rule['rule_value']) * 100 * quantity))
                            rule_value_stored = salary_cents  # в копейках для единообразия отображения (rule_value/100 = рубли)
                        else:
                            salary_cents = int(rule['rule_value'])
                            rule_value_stored = salary_cents
                    else:
                        continue
                    
                    if salary_cents <= 0:
                        continue
                    
                    # Определяем user_id и role
                    if executor_id:
                        user_id = executor_id
                        role = 'master'
                    elif order_master_id:
                        user_id = order_master_id
                        role = 'master'
                    else:
                        continue  # Нет мастера для начисления
                    
                    accruals.append({
                        'order_id': order_id,
                        'user_id': user_id,
                        'role': role,
                        'amount_cents': salary_cents,
                        'base_amount_cents': int(price * quantity * 100),
                        'profit_cents': item_profit_cents,
                        'rule_type': rule['rule_type'],
                        'rule_value': rule_value_stored,
                        'calculated_from': calculated_from,
                        'calculated_from_id': calculated_from_id,
                        'service_id': service_id,
                        'part_id': None,
                        'vat_included': 1 if profit_data['vat_enabled'] else 0
                    })
                
                # Товары
                cursor.execute('''
                    SELECT id, part_id, quantity, price, purchase_price, executor_id
                    FROM order_parts
                    WHERE order_id = ?
                ''', (order_id,))
                parts = cursor.fetchall()
                
                for part_row in parts:
                    part_item_id, part_id, quantity, price, purchase_price, executor_id = part_row
                    quantity = quantity or 1
                    price = float(price or 0)
                    purchase_price = float(purchase_price or 0)
                    
                    # Прибыль по позиции = (price * quantity) - (purchase_price * quantity)
                    item_profit = (price * quantity) - (purchase_price * quantity)
                    item_profit_cents = int(item_profit * 100)
                    
                    if item_profit_cents <= 0:
                        continue
                    
                    # Определяем правило (приоритет)
                    rule = None
                    calculated_from = None
                    calculated_from_id = None
                    
                    # Приоритет 1: Правило товара
                    if part_id:
                        rule = SalaryService._get_salary_rule(cursor, 'part', part_id)
                        if rule:
                            calculated_from = 'part'
                            calculated_from_id = part_id
                    
                    # Приоритет 2: Правило исполнителя
                    if not rule and executor_id:
                        rule = SalaryService._get_salary_rule(cursor, 'master', executor_id, item_type='part')
                        if rule:
                            calculated_from = 'master'
                            calculated_from_id = executor_id
                    
                    # Приоритет 3: Правило мастера заявки
                    if not rule and order_master_id:
                        rule = SalaryService._get_salary_rule(cursor, 'master', order_master_id, item_type='part')
                        if rule:
                            calculated_from = 'master'
                            calculated_from_id = order_master_id
                    
                    # Приоритет 4: Правило менеджера заявки
                    if not rule and order_manager_id:
                        rule = SalaryService._get_salary_rule(cursor, 'manager', order_manager_id, item_type='part')
                        if rule:
                            calculated_from = 'manager'
                            calculated_from_id = order_manager_id
                    
                    # Приоритет 5: Правило статуса
                    if not rule and order_status_id:
                        rule = SalaryService._get_salary_rule(cursor, 'status', order_status_id)
                        if rule:
                            calculated_from = 'status'
                            calculated_from_id = order_status_id
                    
                    if not rule:
                        continue
                    
                    # Расчет зарплаты
                    # Услуги и товары хранят фикс в рублях, мастер/менеджер/статус — в копейках
                    if rule['rule_type'] == 'percent':
                        salary_cents = int(item_profit_cents * rule['rule_value'] / 100)
                        rule_value_stored = rule['rule_value']
                    elif rule['rule_type'] == 'fixed':
                        if calculated_from in ('service', 'part'):
                            # Фикс за единицу: умножаем на количество
                            salary_cents = int(round(float(rule['rule_value']) * 100 * quantity))
                            rule_value_stored = salary_cents  # в копейках для отображения (rule_value/100 = рубли)
                        else:
                            salary_cents = int(rule['rule_value'])
                            rule_value_stored = salary_cents
                    else:
                        continue
                    
                    if salary_cents <= 0:
                        continue
                    
                    # Определяем user_id и role
                    if executor_id:
                        user_id = executor_id
                        role = 'master'
                    elif order_master_id:
                        user_id = order_master_id
                        role = 'master'
                    else:
                        continue  # Нет мастера для начисления
                    
                    accruals.append({
                        'order_id': order_id,
                        'user_id': user_id,
                        'role': role,
                        'amount_cents': salary_cents,
                        'base_amount_cents': int(price * quantity * 100),
                        'profit_cents': item_profit_cents,
                        'rule_type': rule['rule_type'],
                        'rule_value': rule_value_stored,
                        'calculated_from': calculated_from,
                        'calculated_from_id': calculated_from_id,
                        'service_id': None,
                        'part_id': part_id,
                        'vat_included': 1 if profit_data['vat_enabled'] else 0
                    })
                
                # Зарплата менеджера: от прибыли заявки или от выручки (salary_rule_base)
                if order_manager_id:
                    rule = SalaryService._get_salary_rule(cursor, 'manager', order_manager_id)
                    if rule:
                        if rule['rule_type'] == 'percent':
                            base_cents = (
                                order_total_revenue_cents
                                if rule.get('rule_base') == 'revenue'
                                else total_profit_cents
                            )
                            salary_cents = int(base_cents * rule['rule_value'] / 100)
                        elif rule['rule_type'] == 'fixed':
                            salary_cents = int(rule['rule_value'])
                        else:
                            salary_cents = 0
                        
                        if salary_cents > 0:
                            accruals.append({
                                'order_id': order_id,
                                'user_id': order_manager_id,
                                'role': 'manager',
                                'amount_cents': salary_cents,
                                'base_amount_cents': profit_data['total_payments_cents'],
                                'profit_cents': total_profit_cents,
                                'rule_type': rule['rule_type'],
                                'rule_value': rule['rule_value'],
                                'calculated_from': 'manager',
                                'calculated_from_id': order_manager_id,
                                'service_id': None,
                                'part_id': None,
                                'vat_included': 1 if profit_data['vat_enabled'] else 0
                            })
                
                # Агрегируем начисления по бизнес-ключу, чтобы избежать дублей
                # (например, одинаковая услуга несколько раз с тем же правилом)
                # и конфликтов с ux_salary_accruals_business_key.
                grouped: Dict[Tuple[Any, ...], Dict[str, Any]] = {}
                for accrual in accruals:
                    key = (
                        accrual.get('order_id'),
                        accrual.get('user_id'),
                        accrual.get('role'),
                        accrual.get('rule_type'),
                        float(accrual.get('rule_value') or 0),
                        accrual.get('calculated_from'),
                        accrual.get('calculated_from_id'),
                        accrual.get('service_id'),
                        accrual.get('part_id'),
                        int(accrual.get('vat_included') or 0),
                    )
                    if key not in grouped:
                        grouped[key] = dict(accrual)
                    else:
                        grouped[key]['amount_cents'] = int(grouped[key].get('amount_cents') or 0) + int(accrual.get('amount_cents') or 0)
                        grouped[key]['base_amount_cents'] = int(grouped[key].get('base_amount_cents') or 0) + int(accrual.get('base_amount_cents') or 0)
                        grouped[key]['profit_cents'] = int(grouped[key].get('profit_cents') or 0) + int(accrual.get('profit_cents') or 0)

                grouped_values = list(grouped.values())
                # Зарплата начисляется только при полной оплате (проверка выполнена выше)
                return grouped_values
        except Exception as e:
            logger.error(f"Ошибка при расчете зарплаты для заявки {order_id}: {e}", exc_info=True)
            raise DatabaseError(f"Ошибка при расчете зарплаты: {e}")

    @staticmethod
    def calculate_salary_for_shop_sale(sale_id: int) -> List[Dict[str, Any]]:
        """
        Рассчитывает зарплату по продаже магазина: по каждой позиции (услуга/товар)
        по правилам услуги или товара, с учётом мастера (salary_percent_services / salary_percent_shop_parts).
        shop_sales.master_id — users.id; в начислении user_id — masters.id (берём из masters WHERE user_id = ?).
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, master_id FROM shop_sales WHERE id = ? AND final_amount > 0",
                    (sale_id,),
                )
                row = cursor.fetchone()
                if not row:
                    return []
                sale_id_db, master_user_id = row[0], row[1]
                if not master_user_id:
                    return []
                cursor.execute("SELECT id FROM masters WHERE user_id = ? AND (active = 1 OR active IS NULL) LIMIT 1", (master_user_id,))
                master_row = cursor.fetchone()
                if not master_row:
                    return []
                master_pk = master_row[0]
                vat_enabled, _ = SalaryService._get_vat_settings()
                vat_included = 1 if vat_enabled else 0
                accruals = []

                # Услуги
                cursor.execute("""
                    SELECT id, service_id, quantity, price
                    FROM shop_sale_items
                    WHERE shop_sale_id = ? AND item_type = 'service'
                """, (sale_id,))
                for item in cursor.fetchall():
                    item_id, service_id, quantity, price = item[0], item[1], item[2] or 1, float(item[3] or 0)
                    # В справочнике services нет cost_price; себестоимость по умолчанию 0
                    cost = 0.0
                    item_profit = (price * quantity) - (cost * quantity)
                    item_profit_cents = int(item_profit * 100)
                    if item_profit_cents <= 0:
                        continue
                    rule = None
                    calculated_from = None
                    calculated_from_id = None
                    if service_id:
                        rule = SalaryService._get_salary_rule(cursor, 'service', service_id)
                        if rule:
                            calculated_from, calculated_from_id = 'service', service_id
                    if not rule:
                        rule = SalaryService._get_salary_rule(cursor, 'master', master_pk, item_type='service')
                        if rule:
                            calculated_from, calculated_from_id = 'master', master_pk
                    if not rule:
                        continue
                    if rule['rule_type'] == 'percent':
                        salary_cents = int(item_profit_cents * rule['rule_value'] / 100)
                        rule_value_stored = rule['rule_value']
                    elif rule['rule_type'] == 'fixed':
                        # Фикс за единицу: умножаем на количество
                        salary_cents = int(round(float(rule['rule_value']) * 100 * quantity))
                        rule_value_stored = salary_cents
                    else:
                        continue
                    if salary_cents <= 0:
                        continue
                    accruals.append({
                        'order_id': None,
                        'shop_sale_id': sale_id_db,
                        'user_id': master_pk,
                        'role': 'master',
                        'amount_cents': salary_cents,
                        'base_amount_cents': int(price * quantity * 100),
                        'profit_cents': item_profit_cents,
                        'rule_type': rule['rule_type'],
                        'rule_value': rule_value_stored,
                        'calculated_from': calculated_from,
                        'calculated_from_id': calculated_from_id,
                        'service_id': service_id,
                        'part_id': None,
                        'vat_included': vat_included,
                    })

                # Товары: правило товара или salary_percent_shop_parts мастера
                cursor.execute("""
                    SELECT id, part_id, quantity, price, purchase_price
                    FROM shop_sale_items
                    WHERE shop_sale_id = ? AND item_type = 'part'
                """, (sale_id,))
                for item in cursor.fetchall():
                    item_id, part_id, quantity, price, purchase_price = item[0], item[1], item[2] or 1, float(item[3] or 0), float(item[4] or 0)
                    item_profit = (price - purchase_price) * quantity
                    item_profit_cents = int(item_profit * 100)
                    if item_profit_cents <= 0:
                        continue
                    rule = None
                    calculated_from = None
                    calculated_from_id = None
                    if part_id:
                        rule = SalaryService._get_salary_rule(cursor, 'part', part_id)
                        if rule:
                            calculated_from, calculated_from_id = 'part', part_id
                    if not rule:
                        rule = SalaryService._get_salary_rule(cursor, 'master', master_pk, item_type='shop_part')
                        if rule:
                            calculated_from, calculated_from_id = 'master', master_pk
                    if not rule:
                        continue
                    if rule['rule_type'] == 'percent':
                        salary_cents = int(item_profit_cents * rule['rule_value'] / 100)
                        rule_value_stored = rule['rule_value']
                    elif rule['rule_type'] == 'fixed':
                        # Фикс за единицу: умножаем на количество
                        salary_cents = int(round(float(rule['rule_value']) * 100 * quantity))
                        rule_value_stored = salary_cents
                    else:
                        continue
                    if salary_cents <= 0:
                        continue
                    accruals.append({
                        'order_id': None,
                        'shop_sale_id': sale_id_db,
                        'user_id': master_pk,
                        'role': 'master',
                        'amount_cents': salary_cents,
                        'base_amount_cents': int(price * quantity * 100),
                        'profit_cents': item_profit_cents,
                        'rule_type': rule['rule_type'],
                        'rule_value': rule_value_stored,
                        'calculated_from': calculated_from,
                        'calculated_from_id': calculated_from_id,
                        'service_id': None,
                        'part_id': part_id,
                        'vat_included': vat_included,
                    })

                # Группировка по бизнес-ключу (как в заявках)
                grouped: Dict[Tuple[Any, ...], Dict[str, Any]] = {}
                for accrual in accruals:
                    key = (
                        accrual.get('order_id'),
                        accrual.get('shop_sale_id'),
                        accrual.get('user_id'),
                        accrual.get('role'),
                        accrual.get('rule_type'),
                        float(accrual.get('rule_value') or 0),
                        accrual.get('calculated_from'),
                        accrual.get('calculated_from_id'),
                        accrual.get('service_id'),
                        accrual.get('part_id'),
                        int(accrual.get('vat_included') or 0),
                    )
                    if key not in grouped:
                        grouped[key] = dict(accrual)
                    else:
                        grouped[key]['amount_cents'] = int(grouped[key].get('amount_cents') or 0) + int(accrual.get('amount_cents') or 0)
                        grouped[key]['base_amount_cents'] = int(grouped[key].get('base_amount_cents') or 0) + int(accrual.get('base_amount_cents') or 0)
                        grouped[key]['profit_cents'] = int(grouped[key].get('profit_cents') or 0) + int(accrual.get('profit_cents') or 0)
                return list(grouped.values())
        except Exception as e:
            logger.error(f"Ошибка при расчете зарплаты для продажи магазина {sale_id}: {e}", exc_info=True)
            raise DatabaseError(f"Ошибка при расчете зарплаты по магазину: {e}")

    @staticmethod
    @handle_service_error
    def accrue_salary_for_shop_sale(sale_id: int) -> List[int]:
        """
        Начисляет зарплату по продаже магазина. Удаляет предыдущие начисления по этой продаже и создаёт новые.
        """
        SalaryQueries.delete_accruals_for_shop_sale(sale_id)
        accruals = SalaryService.calculate_salary_for_shop_sale(sale_id)
        created_ids = []
        for accrual in accruals:
            accrual_id = SalaryQueries.create_accrual(
                user_id=accrual['user_id'],
                role=accrual['role'],
                amount_cents=accrual['amount_cents'],
                base_amount_cents=accrual['base_amount_cents'],
                profit_cents=accrual['profit_cents'],
                rule_type=accrual['rule_type'],
                rule_value=accrual['rule_value'],
                calculated_from=accrual['calculated_from'],
                calculated_from_id=accrual.get('calculated_from_id'),
                service_id=accrual.get('service_id'),
                part_id=accrual.get('part_id'),
                vat_included=accrual['vat_included'],
                order_id=accrual.get('order_id'),
                shop_sale_id=accrual.get('shop_sale_id'),
            )
            created_ids.append(accrual_id)
        if created_ids:
            logger.info(f"Начислена зарплата по продаже магазина #{sale_id}: {len(created_ids)} записей")
        return created_ids

    @staticmethod
    def order_changed_since_last_accrual(order_id: int) -> bool:
        """
        Проверяет, изменилась ли заявка после последнего начисления (новые/изменённые услуги,
        товары, оплаты или обновление заявки). Если начислений ещё нет — возвращает True.
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT MAX(created_at) FROM salary_accruals WHERE order_id = ?",
                    (order_id,),
                )
                row = cursor.fetchone()
                last_accrual = row[0] if row and row[0] else None
                if not last_accrual:
                    return True
                # Есть ли новые услуги, товары или оплаты после последнего начисления?
                cursor.execute(
                    """
                    SELECT 1 FROM order_services WHERE order_id = ? AND created_at > ?
                    UNION ALL
                    SELECT 1 FROM order_parts WHERE order_id = ? AND created_at > ?
                    UNION ALL
                    SELECT 1 FROM payments WHERE order_id = ? AND created_at > ?
                    LIMIT 1
                    """,
                    (order_id, last_accrual, order_id, last_accrual, order_id, last_accrual),
                )
                if cursor.fetchone():
                    return True
                # Обновлялась ли заявка после последнего начисления (редактирование услуг/товаров)?
                cursor.execute(
                    "SELECT 1 FROM orders WHERE id = ? AND updated_at IS NOT NULL AND updated_at > ? LIMIT 1",
                    (order_id, last_accrual),
                )
                return cursor.fetchone() is not None
        except Exception as e:
            logger.warning(f"Ошибка проверки изменений заявки {order_id}: {e}")
            return True

    @staticmethod
    @handle_service_error
    def accrue_salary_for_order(order_id: int, force_recalculate: bool = False) -> List[int]:
        """
        Начисляет зарплату по заявке.
        Если по заявке уже есть начисления и force_recalculate=False — ничего не делает
        (дата начислений сохраняется). При force_recalculate=True удаляет старые начисления
        и создаёт новые (для скриптов и ручного пересчёта).
        
        Args:
            order_id: ID заявки
            force_recalculate: при True пересчитать даже если начисления уже есть
            
        Returns:
            Список ID начислений (существующих или созданных)
        """
        existing = SalaryQueries.get_accruals_for_order(order_id)
        if existing and not force_recalculate:
            ids = [a['id'] for a in existing if a.get('id') is not None]
            if ids:
                logger.info(f"Зарплата по заявке {order_id} уже начислена, пропуск ({len(ids)} записей)")
                return ids

        # Удаляем старые начисления (если были)
        SalaryQueries.delete_accruals_for_order(order_id)

        # Рассчитываем новые начисления
        accruals = SalaryService.calculate_salary_for_order(order_id)
        
        # Создаем записи в БД
        created_ids = []
        for accrual in accruals:
            accrual_id = SalaryQueries.create_accrual(
                user_id=accrual['user_id'],
                role=accrual['role'],
                amount_cents=accrual['amount_cents'],
                base_amount_cents=accrual['base_amount_cents'],
                profit_cents=accrual['profit_cents'],
                rule_type=accrual['rule_type'],
                rule_value=accrual['rule_value'],
                calculated_from=accrual['calculated_from'],
                calculated_from_id=accrual.get('calculated_from_id'),
                service_id=accrual.get('service_id'),
                part_id=accrual.get('part_id'),
                vat_included=accrual['vat_included'],
                order_id=accrual.get('order_id'),
                shop_sale_id=accrual.get('shop_sale_id'),
            )
            created_ids.append(accrual_id)
        
        logger.info(f"Начислена зарплата по заявке {order_id}: {len(created_ids)} записей")

        # Логируем создание начислений зарплаты
        try:
            total_amount = sum(accrual['amount_cents'] for accrual in accruals)
            ActionLogService.log_action(
                user_id=None,  # Системная операция
                username='system',
                action_type='create',
                entity_type='salary_accrual',
                entity_id=order_id,  # Используем order_id как entity_id для группировки
                description=f"Начислена зарплата по заявке #{order_id}",
                details={
                    'Количество начислений': len(created_ids),
                    'Общая сумма': f"{total_amount / 100:.2f} ₽",
                    'Заявка': order_id
                }
            )
        except Exception as e:
            logger.warning(f"Не удалось залогировать начисление зарплаты для заявки {order_id}: {e}")

        return created_ids
    
    @staticmethod
    @handle_service_error
    def get_salary_report(
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        user_id: Optional[int] = None,
        role: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Получает отчет по зарплате.
        
        Args:
            date_from: Дата начала
            date_to: Дата окончания
            user_id: Фильтр по сотруднику
            role: Фильтр по роли
            
        Returns:
            Словарь с данными отчета
        """
        # Начисления за период по дате оплаты (заявки) и дате продажи (магазин) — как в кассе
        accruals = SalaryQueries.get_salary_report_by_period_date(
            date_from=date_from,
            date_to=date_to,
            user_id=user_id,
            role=role
        ) if (date_from or date_to) else SalaryQueries.get_salary_report(
            date_from=date_from,
            date_to=date_to,
            user_id=user_id,
            role=role
        )

        # По каждой заявке добавляем выручку, итого руководителю и списки услуг/товаров
        order_ids = list({a.get('order_id') for a in accruals if a.get('order_id')})
        orders_meta = SalaryQueries.get_orders_revenue_and_costs(order_ids) if order_ids else {}
        order_items = SalaryQueries.get_order_items_with_profit(order_ids) if order_ids else {}
        # Выручка за период (только платежи с датой в периоде) — для сверки с кассой
        orders_revenue_in_period = SalaryQueries.get_orders_revenue_in_period(
            order_ids, date_from, date_to
        ) if order_ids and (date_from or date_to) else {}

        # Выручка по продажам магазина (для карточки «Выручка» и строк отчёта)
        shop_sale_ids = list({a['shop_sale_id'] for a in accruals if a.get('shop_sale_id')})
        shop_sales_revenue = SalaryQueries.get_shop_sales_revenue(shop_sale_ids) if shop_sale_ids else {}
        shop_sale_profit: Dict[int, int] = {}
        shop_sale_salary_sum: Dict[int, int] = {}

        for a in accruals:
            oid = a.get('order_id')
            meta = orders_meta.get(oid, {})
            items = order_items.get(oid, {})
            sid = a.get('shop_sale_id')
            if sid is not None:
                a['revenue_cents'] = shop_sales_revenue.get(sid, 0)
                a['order_profit_cents'] = int(a.get('profit_cents') or 0)
                if sid not in shop_sale_profit:
                    shop_sale_profit[sid] = a['order_profit_cents']
                shop_sale_salary_sum[sid] = shop_sale_salary_sum.get(sid, 0) + int(a.get('amount_cents') or 0)
                a['owner_net_cents'] = max(0, shop_sale_profit[sid] - shop_sale_salary_sum[sid])  # пока без следующей итерации показываем предварительно
                a['order_services_items'] = []
                a['order_parts_items'] = []
                a['parts_cost_cents'] = 0
                a['services_cost_cents'] = 0
                a['salary_order_cents'] = 0
            else:
                a['revenue_cents'] = meta.get('revenue_cents', 0)
                a['order_profit_cents'] = meta.get('order_profit_cents', 0)
                a['owner_net_cents'] = meta.get('owner_net_cents', 0)
            rule_type = a.get('rule_type') or 'percent'
            rule_val = float(a.get('rule_value') or 0)
            total_accrual = int(a.get('amount_cents') or 0)
            all_items = items.get('services', []) + items.get('parts', [])
            total_profit = sum(x.get('profit_cents') or 0 for x in all_items)

            def calc_salary(item: dict) -> dict:
                p = item.get('profit_cents') or 0
                if rule_type == 'percent' and rule_val:
                    sal = int(p * rule_val / 100)
                elif rule_type == 'fixed' and total_profit and total_accrual:
                    sal = int(total_accrual * p / total_profit) if p else 0
                else:
                    sal = 0
                return {**item, 'salary_cents': sal}

            if sid is None:
                a['order_services_items'] = [calc_salary(x) for x in items.get('services', [])]
                a['order_parts_items'] = [calc_salary(x) for x in items.get('parts', [])]
                a['parts_cost_cents'] = meta.get('parts_cost_cents', 0)
                a['services_cost_cents'] = meta.get('services_cost_cents', 0)
                a['salary_order_cents'] = meta.get('salary_order_cents', 0)

        for a in accruals:
            sid = a.get('shop_sale_id')
            if sid is not None:
                a['owner_net_cents'] = max(0, shop_sale_profit.get(sid, 0) - shop_sale_salary_sum.get(sid, 0))

        order_revenue_total = (
            sum(orders_revenue_in_period.values()) if orders_revenue_in_period
            else sum(m.get('revenue_cents', 0) for m in orders_meta.values())
        )
        total_revenue_cents = order_revenue_total + sum(shop_sales_revenue.values())
        total_profit_cents = sum(m.get('order_profit_cents', 0) for m in orders_meta.values()) + sum(shop_sale_profit.values())
        # Сумма начислений за период (зарплата сотрудникам)
        total_amount_cents = sum(int(a.get('amount_cents') or 0) for a in accruals)
        # Итого руководителю = Выручка − Сумма начислений (остаток после выплаты зарплаты)
        total_owner_net_cents = total_revenue_cents - total_amount_cents

        summary = SalaryQueries.get_salary_summary(
            date_from=date_from,
            date_to=date_to,
            user_id=user_id,
            role=role
        )
        if summary is None:
            summary = {}
        summary['total_revenue_cents'] = total_revenue_cents
        summary['total_owner_net_cents'] = total_owner_net_cents
        summary['total_profit_cents'] = total_profit_cents
        summary['total_amount_cents'] = total_amount_cents
        # При фильтре по периоду — уточняем счётчики из фактического списка начислений
        if date_from or date_to:
            summary['total_accruals'] = len(accruals)
            summary['unique_users'] = len({a.get('user_id') for a in accruals if a.get('user_id')})

        return {
            'accruals': accruals,
            'summary': summary,
            'date_from': date_from,
            'date_to': date_to,
            'user_id': user_id,
            'role': role
        }
    
    @staticmethod
    @handle_service_error
    def get_accruals_for_order(order_id: int) -> List[Dict[str, Any]]:
        """
        Получает начисления зарплаты по заявке.
        
        Args:
            order_id: ID заявки
            
        Returns:
            Список начислений
        """
        return SalaryQueries.get_accruals_for_order(order_id)

    @staticmethod
    def get_order_accrual_details(order_id: int) -> Dict[str, Any]:
        """
        Получает полную детализацию начислений по заявке для модального окна.
        Returns: { order_id, order_uuid, revenue_cents, order_profit_cents, owner_net_cents, accruals }
        """
        accruals = SalaryQueries.get_accruals_for_order_with_details(order_id)
        if not accruals:
            return {'order_id': order_id, 'order_uuid': None, 'revenue_cents': 0, 'order_profit_cents': 0,
                    'owner_net_cents': 0, 'accruals': []}
        order_ids = [order_id]
        orders_meta = SalaryQueries.get_orders_revenue_and_costs(order_ids)
        order_items = SalaryQueries.get_order_items_with_profit(order_ids)
        meta = orders_meta.get(order_id, {})
        items = order_items.get(order_id, {})
        first = accruals[0]
        order_uuid = first.get('order_uuid')
        for a in accruals:
            rule_type = a.get('rule_type') or 'percent'
            rule_val = float(a.get('rule_value') or 0)
            total_accrual = int(a.get('amount_cents') or 0)
            all_items = items.get('services', []) + items.get('parts', [])
            total_profit = sum(x.get('profit_cents') or 0 for x in all_items)

            def calc_salary(item: dict) -> dict:
                p = item.get('profit_cents') or 0
                if rule_type == 'percent' and rule_val:
                    sal = int(p * rule_val / 100)
                elif rule_type == 'fixed' and total_profit and total_accrual:
                    sal = int(total_accrual * p / total_profit) if p else 0
                else:
                    sal = 0
                return {**item, 'salary_cents': sal}

            a['order_services_items'] = [calc_salary(x) for x in items.get('services', [])]
            a['order_parts_items'] = [calc_salary(x) for x in items.get('parts', [])]
        return {
            'order_id': order_id,
            'order_uuid': order_uuid,
            'revenue_cents': meta.get('revenue_cents', 0),
            'order_profit_cents': meta.get('order_profit_cents', 0),
            'owner_net_cents': meta.get('owner_net_cents', 0),
            'accruals': accruals,
        }


