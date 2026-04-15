"""
Роуты для модуля зарплаты (дашборд и личные кабинеты).
"""
from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from app.services.salary_dashboard_service import SalaryDashboardService
from app.services.salary_dashboard_service import _is_master_role, _is_manager_role
from app.services.user_service import UserService
from app.services.master_service import MasterService
from app.services.manager_service import ManagerService
from app.utils.exceptions import ValidationError, NotFoundError, DatabaseError
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('salary_dashboard', __name__, url_prefix='/salary')
bp_api = Blueprint('salary_dashboard_api', __name__, url_prefix='/api/salary')


def _moscow_today_iso():
    """Дата «сегодня» по московскому времени (для подстановки в формы)."""
    from app.utils.datetime_utils import get_moscow_now
    return get_moscow_now().date().isoformat()


def _normalize_request_date(date_str):
    if not date_str:
        return None
    value = str(date_str).strip()
    if not value:
        return None
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").strftime("%Y-%m-%d")
    except ValueError:
        raise ValidationError("Некорректная дата. Используйте формат YYYY-MM-DD.")


def check_salary_access():
    """Проверяет право доступа к модулю зарплаты."""
    if not current_user.is_authenticated:
        return False
    
    user_id = current_user.id
    user_role = current_user.role
    
    # Проверяем право salary.view
    if not UserService.check_permission(user_id, 'salary.view'):
        return False
    
    return True


@bp.route('')
@login_required
def index():
    """Главная страница модуля зарплаты."""
    if not check_salary_access():
        flash('У вас нет прав для доступа к модулю зарплаты', 'error')
        return redirect(url_for('main.home'))
    
    user_role = current_user.role
    user_id = current_user.id
    
    # Для мастера - сразу редирект на его кабинет
    if _is_master_role(user_role):
        employee_info = SalaryDashboardService.get_employee_id_by_user(user_id, user_role)
        if employee_info:
            employee_id, role = employee_info
            return redirect(url_for('salary_dashboard.employee_detail', 
                                  employee_id=employee_id, 
                                  role=role))
        else:
            flash('Ваш профиль мастера не найден. Обратитесь к администратору.', 'error')
            return redirect(url_for('main.home'))
    
    # Для менеджера и админа - показываем список
    return render_template('salary/index.html')


@bp.route('/employee/<int:employee_id>/<role>')
@login_required
def employee_detail(employee_id, role):
    """Личный кабинет сотрудника."""
    if not check_salary_access():
        flash('У вас нет прав для доступа к модулю зарплаты', 'error')
        return redirect(url_for('main.home'))
    
    user_role = current_user.role
    user_id = current_user.id
    
    # Проверка доступа к кабинету
    if _is_master_role(user_role):
        # Мастер может видеть только свой кабинет
        employee_info = SalaryDashboardService.get_employee_id_by_user(user_id, user_role)
        if not employee_info or employee_info[0] != employee_id:
            flash('У вас нет прав для просмотра этого кабинета', 'error')
            return redirect(url_for('main.home'))
            
    elif _is_manager_role(user_role):
        # Менеджер может видеть мастеров и свой кабинет
        if role == 'manager':
            # Проверяем, что это его кабинет
            employee_info = SalaryDashboardService.get_employee_id_by_user(user_id, user_role)
            if not employee_info or employee_info[0] != employee_id:
                flash('У вас нет прав для просмотра кабинетов других менеджеров', 'error')
                return redirect(url_for('salary_dashboard.index'))
        # Если role == 'master' - доступ разрешен
        
    elif user_role != 'admin':
        # Только админ может видеть всех
        flash('У вас нет прав для доступа к этому кабинету', 'error')
        return redirect(url_for('main.home'))
    
    # Получаем имя сотрудника
    employee_name = "Неизвестно"
    try:
        if role == 'master':
            master = MasterService.get_master_by_id(employee_id)
            if master:
                employee_name = master.get('name', 'Неизвестно')
        elif role == 'manager':
            manager = ManagerService.get_manager_by_id(employee_id)
            if manager:
                employee_name = manager.get('name', 'Неизвестно')
    except Exception as e:
        logger.warning(f"Не удалось получить имя сотрудника: {e}")
    
    # Кнопка «Зарегистрировать выплату» / «Списать долг»: админ всегда; менеджер (в т.ч. manager_*) — для мастеров и для своего кабинета
    can_register_payment = False
    if user_role == 'admin':
        can_register_payment = True
    elif _is_manager_role(user_role):
        if role == 'master':
            can_register_payment = True
        elif role == 'manager':
            my_info = SalaryDashboardService.get_employee_id_by_user(user_id, user_role)
            if my_info and my_info[0] == employee_id:
                can_register_payment = True
    
    # Кнопки «Начислить премию» / «Начислить штраф»: админ всегда; менеджер (в т.ч. manager_*) — только при просмотре кабинета мастера
    can_add_bonus_fine = (user_role == 'admin') or (_is_manager_role(user_role) and role == 'master')
    
    return render_template('salary/employee_detail.html', 
                         employee_id=employee_id,
                         employee_name=employee_name,
                         role=role,
                         can_register_payment=can_register_payment,
                         can_add_bonus_fine=can_add_bonus_fine)


# ========== API Endpoints ==========

@bp_api.route('/employees', methods=['GET'])
@login_required
def api_get_employees():
    """API для получения списка сотрудников с статистикой."""
    if not check_salary_access():
        return jsonify({'success': False, 'error': 'Нет прав доступа'}), 403

    try:
        date_from = _normalize_request_date(request.args.get('date_from'))
        date_to = _normalize_request_date(request.args.get('date_to'))
        role = request.args.get('role')  # 'master', 'manager', None
        status = request.args.get('status', 'active')  # 'active', 'inactive', None
        sort_by = request.args.get('sort_by', 'profit')  # 'profit', 'revenue', 'orders', 'salary'

        logger.info(f"API call: status={status}, role={role}, sort_by={sort_by}, date_from={date_from}, date_to={date_to}")

        employees = SalaryDashboardService.get_employees_with_stats(
            date_from=date_from,
            date_to=date_to,
            role=role,
            status=status,
            sort_by=sort_by,
            current_user_id=current_user.id,
            current_user_role=current_user.role
        )

        # Итоги по заявкам (выручка и прибыль без дублирования: одна заявка = один раз)
        period_totals = SalaryDashboardService.get_salary_period_totals(
            date_from=date_from,
            date_to=date_to,
        )
        cash_reconciliation = SalaryDashboardService.get_cash_reconciliation(
            date_from=date_from,
            date_to=date_to,
        )
        profit_details = SalaryDashboardService.get_profit_details_by_orders(
            date_from=date_from,
            date_to=date_to,
            limit=300,
        )
        not_in_salary = SalaryDashboardService.get_not_in_salary_items(
            date_from=date_from,
            date_to=date_to,
        )

        logger.info(f"Found {len(employees)} employees")

        return jsonify({
            'success': True,
            'employees': employees,
            'period_totals': period_totals,
            'cash_reconciliation': cash_reconciliation,
            'profit_details': profit_details,
            'not_in_salary': not_in_salary,
        })
    except ValidationError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Ошибка при получении списка сотрудников: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500




@bp_api.route('/employee/<int:employee_id>/<role>', methods=['GET'])
@login_required
def api_get_employee(employee_id, role):
    """API для получения данных сотрудника."""
    if not check_salary_access():
        return jsonify({'success': False, 'error': 'Нет прав доступа'}), 403
    
    # Проверка доступа (аналогично employee_detail)
    user_role = current_user.role
    user_id = current_user.id
    
    if _is_master_role(user_role):
        employee_info = SalaryDashboardService.get_employee_id_by_user(user_id, user_role)
        if not employee_info or employee_info[0] != employee_id:
            return jsonify({'success': False, 'error': 'Нет прав доступа'}), 403
    elif _is_manager_role(user_role) and role == 'manager':
        employee_info = SalaryDashboardService.get_employee_id_by_user(user_id, user_role)
        if not employee_info or employee_info[0] != employee_id:
            return jsonify({'success': False, 'error': 'Нет прав доступа'}), 403
    elif not _is_manager_role(user_role) and user_role != 'admin':
        return jsonify({'success': False, 'error': 'Нет прав доступа'}), 403
    
    try:
        period = request.args.get('period', 'today')
        date_from = _normalize_request_date(request.args.get('date_from'))
        date_to = _normalize_request_date(request.args.get('date_to'))
        
        dashboard = SalaryDashboardService.get_employee_dashboard(
            employee_id=employee_id,
            role=role,
            period=period,
            date_from=date_from,
            date_to=date_to
        )
        
        return jsonify({'success': True, 'dashboard': dashboard})
    except ValidationError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Ошибка при получении данных сотрудника: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500


@bp_api.route('/employee/<int:employee_id>/<role>/bonus', methods=['POST'])
@login_required
def api_add_bonus(employee_id, role):
    """API для начисления премии."""
    if not check_salary_access():
        return jsonify({'success': False, 'error': 'Нет прав доступа'}), 403
    
    # Только менеджер и админ могут начислять премии
    if not _is_manager_role(current_user.role) and current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Недостаточно прав для начисления премий'}), 403
    
    # Менеджер может начислять только мастерам
    if _is_manager_role(current_user.role) and role != 'master':
        return jsonify({'success': False, 'error': 'Менеджер может начислять премии только мастерам'}), 403
    
    try:
        data = request.get_json(silent=True) or {}
        amount = float(data.get('amount', 0))
        reason = str(data.get('reason') or '').strip()
        bonus_date = data.get('bonus_date')
        order_id = data.get('order_id')
        try:
            order_id = int(order_id) if order_id is not None else None
        except (TypeError, ValueError):
            order_id = None
        
        if not amount or amount <= 0:
            return jsonify({'success': False, 'error': 'Сумма премии должна быть положительной'}), 400
        if not reason:
            return jsonify({'success': False, 'error': 'Причина премии обязательна'}), 400
        if not bonus_date:
            from datetime import date
            bonus_date = _moscow_today_iso()
        
        amount_cents = int(amount * 100)
        
        bonus_id = SalaryDashboardService.add_bonus(
            user_id=employee_id,
            role=role,
            amount_cents=amount_cents,
            reason=reason,
            bonus_date=bonus_date,
            order_id=order_id,
            created_by_id=current_user.id,
            created_by_username=current_user.username
        )
        
        return jsonify({'success': True, 'bonus_id': bonus_id}), 201
    except ValidationError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except DatabaseError as e:
        logger.error(f"Ошибка при начислении премии: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Ошибка базы данных'}), 500
    except Exception as e:
        logger.error(f"Ошибка при начислении премии: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500


@bp_api.route('/employee/<int:employee_id>/<role>/fine', methods=['POST'])
@login_required
def api_add_fine(employee_id, role):
    """API для начисления штрафа."""
    if not check_salary_access():
        return jsonify({'success': False, 'error': 'Нет прав доступа'}), 403
    
    # Только менеджер и админ могут начислять штрафы
    if not _is_manager_role(current_user.role) and current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Недостаточно прав для начисления штрафов'}), 403
    
    # Менеджер может начислять только мастерам
    if _is_manager_role(current_user.role) and role != 'master':
        return jsonify({'success': False, 'error': 'Менеджер может начислять штрафы только мастерам'}), 403
    
    try:
        data = request.get_json(silent=True) or {}
        amount = float(data.get('amount', 0))
        reason = str(data.get('reason') or '').strip()
        fine_date = data.get('fine_date')
        order_id = data.get('order_id')
        try:
            order_id = int(order_id) if order_id is not None else None
        except (TypeError, ValueError):
            order_id = None
        
        if not amount or amount <= 0:
            return jsonify({'success': False, 'error': 'Сумма штрафа должна быть положительной'}), 400
        if not reason:
            return jsonify({'success': False, 'error': 'Причина штрафа обязательна'}), 400
        if not fine_date:
            from datetime import date
            fine_date = _moscow_today_iso()
        
        amount_cents = int(amount * 100)
        
        fine_id = SalaryDashboardService.add_fine(
            user_id=employee_id,
            role=role,
            amount_cents=amount_cents,
            reason=reason,
            fine_date=fine_date,
            order_id=order_id,
            created_by_id=current_user.id,
            created_by_username=current_user.username
        )
        
        return jsonify({'success': True, 'fine_id': fine_id}), 201
    except ValidationError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except DatabaseError as e:
        logger.error(f"Ошибка при начислении штрафа: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Ошибка базы данных'}), 500
    except Exception as e:
        logger.error(f"Ошибка при начислении штрафа: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500


@bp_api.route('/employee/<int:employee_id>/<role>/payment', methods=['POST'])
@login_required
def api_register_payment(employee_id, role):
    """API для регистрации выплаты зарплаты."""
    if not check_salary_access():
        return jsonify({'success': False, 'error': 'Нет прав доступа'}), 403
    
    # Только менеджер и админ могут регистрировать выплаты
    if not _is_manager_role(current_user.role) and current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Недостаточно прав для регистрации выплат'}), 403
    
    # Менеджер может регистрировать выплаты мастерам и себе (своему кабинету менеджера)
    if _is_manager_role(current_user.role) and role != 'master':
        if role != 'manager':
            return jsonify({'success': False, 'error': 'Менеджер может регистрировать выплаты только мастерам и себе'}), 403
        my_info = SalaryDashboardService.get_employee_id_by_user(current_user.id, 'manager')
        if not my_info or my_info[0] != employee_id:
            return jsonify({'success': False, 'error': 'Менеджер может регистрировать выплаты только мастерам и своему кабинету'}), 403
    
    try:
        data = request.get_json(silent=True) or {}
        amount = float(data.get('amount', 0))
        payment_date = data.get('payment_date')
        period_start = data.get('period_start')
        period_end = data.get('period_end')
        payment_type = data.get('payment_type', 'salary')
        comment = str(data.get('comment') or '').strip()
        
        if not amount or amount <= 0:
            return jsonify({'success': False, 'error': 'Сумма выплаты должна быть положительной'}), 400
        if not payment_date:
            from datetime import date
            payment_date = _moscow_today_iso()
        
        amount_cents = int(amount * 100)
        
        payment_id = SalaryDashboardService.register_payment(
            user_id=employee_id,
            role=role,
            amount_cents=amount_cents,
            payment_date=payment_date,
            period_start=period_start,
            period_end=period_end,
            payment_type=payment_type,
            comment=comment,
            created_by_id=current_user.id,
            created_by_username=current_user.username
        )
        
        return jsonify({'success': True, 'payment_id': payment_id}), 201
    except ValidationError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except DatabaseError as e:
        logger.error(f"Ошибка при регистрации выплаты: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Ошибка базы данных'}), 500
    except Exception as e:
        logger.error(f"Ошибка при регистрации выплаты: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500


@bp_api.route('/employee/<int:employee_id>/<role>/writeoff', methods=['POST'])
@login_required
def api_writeoff_debt(employee_id, role):
    """API для списания долга сотрудника (без кассы)."""
    if not check_salary_access():
        return jsonify({'success': False, 'error': 'Нет прав доступа'}), 403

    # Только менеджер и админ могут списывать долги
    if not _is_manager_role(current_user.role) and current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Недостаточно прав для списания долга'}), 403

    # Менеджер может списывать долги мастерам и себе (своему кабинету менеджера)
    if _is_manager_role(current_user.role) and role != 'master':
        if role != 'manager':
            return jsonify({'success': False, 'error': 'Менеджер может списывать долги только мастерам и себе'}), 403
        my_info = SalaryDashboardService.get_employee_id_by_user(current_user.id, 'manager')
        if not my_info or my_info[0] != employee_id:
            return jsonify({'success': False, 'error': 'Менеджер может списывать долги только мастерам и своему кабинету'}), 403

    try:
        data = request.get_json(silent=True) or {}
        amount = float(data.get('amount', 0))
        reason = str(data.get('reason') or '').strip()

        if not amount or amount <= 0:
            return jsonify({'success': False, 'error': 'Сумма списания должна быть положительной'}), 400

        amount_cents = int(amount * 100)
        writeoff_id = SalaryDashboardService.writeoff_debt(
            user_id=employee_id,
            role=role,
            amount_cents=amount_cents,
            reason=reason or "Списание долга",
            created_by_id=current_user.id,
            created_by_username=current_user.username
        )

        return jsonify({'success': True, 'writeoff_id': writeoff_id}), 201
    except ValidationError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except DatabaseError as e:
        logger.error(f"Ошибка при списании долга: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Ошибка базы данных'}), 500
    except Exception as e:
        logger.error(f"Ошибка при списании долга: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500


@bp_api.route('/debts', methods=['GET'])
@login_required
def api_get_salary_debts():
    """API для получения списка долгов сотрудников."""
    if not check_salary_access():
        return jsonify({'success': False, 'error': 'Нет прав доступа'}), 403

    try:
        role = request.args.get('role')
        status = request.args.get('status', 'active')

        data = SalaryDashboardService.get_salary_debts(role=role, status=status)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        logger.error(f"Ошибка при получении долгов по зарплате: {e}", exc_info=True)
        return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500
