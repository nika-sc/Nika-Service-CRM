"""
Маршруты для финансового модуля.
Статьи доходов/расходов, кассовые операции.
"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from app.routes.main import permission_required
from app.services.finance_service import FinanceService
from app.services.settings_service import SettingsService
from app.services.action_log_service import ActionLogService
from app.services.user_service import UserService
from app.utils.exceptions import ValidationError, NotFoundError, DatabaseError
from app.database.connection import get_db_connection
from app.utils.report_period import normalize_date_range
from datetime import datetime, date, timedelta
from app.utils.datetime_utils import get_moscow_now
import logging

bp = Blueprint('finance', __name__, url_prefix='/finance')
logger = logging.getLogger(__name__)


@bp.before_request
def _finance_api_permission_gate():
    """Единый RBAC-гейт для /finance/api/*."""
    if not request.path.startswith('/finance/api/'):
        return None

    if not current_user.is_authenticated:
        return jsonify({'success': False, 'error': 'auth_required'}), 401

    permission_name = 'view_finance' if request.method in ('GET', 'HEAD', 'OPTIONS') else 'manage_finance'
    if not UserService.check_permission(current_user.id, permission_name):
        return jsonify({
            'success': False,
            'error': 'forbidden',
            'required_permission': permission_name
        }), 403

    return None


# ===========================================
# СТАТЬИ ДОХОДОВ/РАСХОДОВ
# ===========================================

@bp.route('/categories')
@login_required
@permission_required('view_finance')
def categories():
    """Страница управления статьями доходов/расходов."""
    income_categories = FinanceService.get_income_categories()
    expense_categories = FinanceService.get_expense_categories()
    
    return render_template(
        'finance/categories.html',
        income_categories=income_categories,
        expense_categories=expense_categories
    )


@bp.route('/api/categories', methods=['GET'])
@login_required
@permission_required('view_finance')
def api_get_categories():
    """Получить категории."""
    category_type = request.args.get('type')
    categories = FinanceService.get_transaction_categories(category_type=category_type)
    return jsonify({'success': True, 'categories': categories})


@bp.route('/api/categories', methods=['POST'])
@login_required
@permission_required('manage_finance')
def api_create_category():
    """Создать категорию."""
    data = request.get_json()
    
    name = data.get('name', '').strip()
    category_type = data.get('type', 'expense')
    description = data.get('description', '').strip()
    color = data.get('color', '#6c757d')
    
    if not name:
        return jsonify({'success': False, 'error': 'Название обязательно'}), 400
    
    if category_type not in ('income', 'expense'):
        return jsonify({'success': False, 'error': 'Неверный тип категории'}), 400
    
    category_id = FinanceService.create_transaction_category(
        name=name,
        category_type=category_type,
        description=description,
        color=color
    )
    
    ActionLogService.log_action(
        user_id=current_user.id,
        username=current_user.username,
        action_type='create_transaction_category',
        entity_type='transaction_category',
        entity_id=category_id,
        description=f"Создана категория '{name}' ({category_type})"
    )
    
    return jsonify({'success': True, 'id': category_id})


@bp.route('/api/categories/<int:category_id>', methods=['PUT'])
@login_required
@permission_required('manage_finance')
def api_update_category(category_id):
    """Обновить категорию."""
    data = request.get_json()
    
    success = FinanceService.update_transaction_category(
        category_id=category_id,
        name=data.get('name'),
        description=data.get('description'),
        color=data.get('color'),
        is_active=data.get('is_active')
    )
    
    if success:
        ActionLogService.log_action(
            user_id=current_user.id,
            username=current_user.username,
            action_type='update_transaction_category',
            entity_type='transaction_category',
            entity_id=category_id,
            description="Категория обновлена"
        )
    
    return jsonify({'success': success})


@bp.route('/api/categories/<int:category_id>', methods=['DELETE'])
@login_required
@permission_required('manage_finance')
def api_delete_category(category_id):
    """Удалить категорию."""
    success, message = FinanceService.delete_transaction_category(category_id)
    
    if success:
        ActionLogService.log_action(
            user_id=current_user.id,
            username=current_user.username,
            action_type='delete_transaction_category',
            entity_type='transaction_category',
            entity_id=category_id,
            description=message
        )
    
    return jsonify({'success': success, 'message': message})


# ===========================================
# КАССОВЫЕ ОПЕРАЦИИ
# ===========================================

@bp.route('/cash')
@login_required
@permission_required('view_finance')
def cash():
    """Страница кассы. По умолчанию — сегодня."""
    date_from, date_to = normalize_date_range(
        request.args.get('date_from'),
        request.args.get('date_to'),
        default='today',
    )
    category_id = request.args.get('category_id', type=int)
    transaction_type = request.args.get('transaction_type')
    
    transactions = FinanceService.get_transactions(
        date_from=date_from,
        date_to=date_to,
        category_id=category_id,
        transaction_type=transaction_type
    )
    
    summary = FinanceService.get_cash_summary(date_from=date_from, date_to=date_to)
    
    income_categories = FinanceService.get_income_categories()
    expense_categories = FinanceService.get_expense_categories()
    payment_method_settings = SettingsService.get_payment_method_settings()
    
    return render_template(
        'finance/cash.html',
        transactions=transactions,
        summary=summary,
        income_categories=income_categories,
        expense_categories=expense_categories,
        payment_method_settings=payment_method_settings,
        date_from=date_from,
        date_to=date_to,
        selected_category_id=category_id,
        selected_type=transaction_type
    )


@bp.route('/api/transactions', methods=['POST'])
@login_required
@permission_required('manage_finance')
def api_create_transaction():
    """Создать кассовую операцию."""
    data = request.get_json()
    
    category_id = data.get('category_id')
    amount = data.get('amount', 0)
    transaction_type = data.get('transaction_type', 'expense')
    payment_method = data.get('payment_method', 'cash')
    description = data.get('description', '')
    # Дата только день совершения операции (МСК), без выбора с клиента
    transaction_date = get_moscow_now().date().isoformat()
    order_id = data.get('order_id')
    
    if not category_id:
        return jsonify({'success': False, 'error': 'Выберите статью'}), 400
    
    if not amount or float(amount) <= 0:
        return jsonify({'success': False, 'error': 'Укажите сумму'}), 400

    if payment_method not in ('cash', 'transfer'):
        return jsonify({'success': False, 'error': 'Допустимы только Наличные и Перевод'}), 400

    transaction_id = FinanceService.create_transaction(
        category_id=category_id,
        amount=float(amount),
        transaction_type=transaction_type,
        payment_method=payment_method,
        description=description,
        order_id=order_id,
        transaction_date=transaction_date,
        created_by_id=current_user.id,
        created_by_username=current_user.username
    )

    return jsonify({'success': True, 'id': transaction_id})


@bp.route('/api/transfer-between-methods', methods=['POST'])
@login_required
@permission_required('manage_finance')
def api_transfer_between_methods():
    """Перевод между кассами (Наличные ↔ Перевод и т.д.): одна операция создаёт расход и приход."""
    data = request.get_json() or {}
    amount = data.get('amount')
    from_method = data.get('from_method', 'transfer')
    to_method = data.get('to_method', 'cash')
    transaction_date = get_moscow_now().date().isoformat()
    description = data.get('description', '')

    if amount is None:
        return jsonify({'success': False, 'error': 'Укажите сумму'}), 400
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        return jsonify({'success': False, 'error': 'Неверная сумма'}), 400
    if amount <= 0:
        return jsonify({'success': False, 'error': 'Сумма должна быть больше нуля'}), 400
    if from_method not in ('cash', 'transfer') or to_method not in ('cash', 'transfer'):
        return jsonify({'success': False, 'error': 'Допустимы только Наличные и Перевод'}), 400

    try:
        id_expense, id_income = FinanceService.transfer_between_methods(
            amount=amount,
            from_method=from_method,
            to_method=to_method,
            transaction_date=transaction_date,
            description=description,
            created_by_id=current_user.id,
            created_by_username=current_user.username,
        )
        return jsonify({
            'success': True,
            'id_expense': id_expense,
            'id_income': id_income,
            'message': f'Перевод {amount:.2f} ₽ выполнен',
        })
    except ValidationError as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@bp.route('/api/transactions/<int:transaction_id>', methods=['DELETE'])
@login_required
@permission_required('manage_finance')
def api_delete_transaction(transaction_id):
    """Отменить кассовую операцию (soft-delete + сторно)."""
    logger.info(f"Попытка отменить транзакцию {transaction_id} пользователем {current_user.username}")
    
    # Получаем информацию о транзакции до отмены для логирования
    tx_info = None
    try:
        import sqlite3
        with get_db_connection(row_factory=sqlite3.Row) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT ct.*, tc.name as category_name 
                FROM cash_transactions ct
                LEFT JOIN transaction_categories tc ON ct.category_id = tc.id
                WHERE ct.id = ?
            ''', (transaction_id,))
            row = cursor.fetchone()
            if row:
                tx_info = dict(row)
                logger.info(f"Транзакция {transaction_id} найдена: {tx_info.get('description', '')[:50]}")
            else:
                logger.warning(f"Транзакция {transaction_id} не найдена")
                return jsonify({'success': False, 'error': 'Транзакция не найдена'}), 404
    except Exception as e:
        logger.error(f"Ошибка при получении информации о транзакции {transaction_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Ошибка при получении данных транзакции'}), 500
    
    # Получаем причину отмены из запроса (если есть)
    reason = 'Удаление операции'
    try:
        # Проверяем Content-Type
        content_type = request.headers.get('Content-Type', '')
        if 'application/json' in content_type:
            if request.json:
                reason = request.json.get('reason', reason)
                logger.debug(f"Получена причина из JSON: {reason}")
        elif request.form:
            reason = request.form.get('reason', reason)
            logger.debug(f"Получена причина из form: {reason}")
    except Exception as e:
        logger.warning(f"Не удалось получить reason из запроса: {e}, используем значение по умолчанию")
    
    try:
        logger.info(f"Вызываем FinanceService.cancel_transaction для транзакции {transaction_id}")
        
        # Отменяем транзакцию (создаётся сторно)
        # cancel_transaction обёрнут в @handle_service_error, который пробрасывает ValidationError/NotFoundError
        success = FinanceService.cancel_transaction(
            transaction_id=transaction_id,
            reason=reason,
            user_id=current_user.id,
            username=current_user.username
        )
        
        logger.info(f"cancel_transaction вернул success={success}")
        
        if success and tx_info:
            type_label = 'Приход' if tx_info.get('transaction_type') == 'income' else 'Расход'
            ActionLogService.log_action(
                user_id=current_user.id,
                username=current_user.username,
                action_type='cancel',
                entity_type='cash_transaction',
                entity_id=transaction_id,
                description=f"Отменена транзакция: {type_label} {tx_info.get('amount', 0):.0f} руб.",
                details={
                    'Сумма': f"{tx_info.get('amount', 0):.2f} ₽",
                    'Тип операции': 'приход' if tx_info.get('transaction_type') == 'income' else 'расход',
                    'Категория': tx_info.get('category_name'),
                    'Описание': tx_info.get('description'),
                    'Причина отмены': reason
                }
            )
        
        logger.info(f"Транзакция {transaction_id} успешно отменена")
        return jsonify({'success': True, 'message': 'Операция отменена. Создана сторно-операция.'})
        
    except ValidationError as e:
        # Ошибка валидации (например, попытка удалить автоматическую операцию)
        logger.warning(f"Попытка отменить операцию {transaction_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 400
    except NotFoundError as e:
        logger.warning(f"Операция {transaction_id} не найдена: {e}")
        return jsonify({'success': False, 'error': str(e)}), 404
    except DatabaseError as e:
        logger.error(f"Ошибка БД при отмене транзакции {transaction_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    except Exception as e:
        logger.exception(f"Неожиданная ошибка при отмене транзакции {transaction_id}: {e}")
        return jsonify({'success': False, 'error': f'Произошла ошибка при отмене операции: {str(e)}'}), 500


# ===========================================
# ОТЧЕТЫ
# ===========================================

@bp.route('/profit')
@login_required
@permission_required('view_finance')
def profit_report():
    """Перенаправление на отчёт по прибыли в разделе Отчеты."""
    return redirect(
        url_for('reports.profit_report', date_from=request.args.get('date_from'), date_to=request.args.get('date_to'))
    )


@bp.route('/analytics')
@login_required
@permission_required('view_finance')
def analytics():
    """Перенаправление на аналитику в разделе Отчеты."""
    return redirect(
        url_for('reports.analytics_report', date_from=request.args.get('date_from'), date_to=request.args.get('date_to'))
    )


@bp.route('/payment/<int:payment_id>')
@login_required
@permission_required('view_finance')
def payment_detail(payment_id):
    """Детали оплаты (чек)."""
    
    try:
        payment = FinanceService.get_payment(payment_id)
        if not payment:
            # Если оплата не найдена, редиректим на страницу кассы
            # Сохраняем параметры даты из запроса, если они есть
            date_from = request.args.get('date_from')
            date_to = request.args.get('date_to')
            
            flash('Оплата не найдена', 'warning')
            if date_from and date_to:
                return redirect(url_for('finance.cash', date_from=date_from, date_to=date_to))
            else:
                return redirect(url_for('finance.cash'))
        
        return render_template('finance/payment_detail.html', payment=payment)
    except Exception as e:
        # Обработка любых ошибок
        logger.error(f"Ошибка при загрузке чека {payment_id}: {e}")
        flash('Ошибка при загрузке чека', 'error')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        if date_from and date_to:
            return redirect(url_for('finance.cash', date_from=date_from, date_to=date_to))
        return redirect(url_for('finance.cash'))


