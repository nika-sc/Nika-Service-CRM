"""
Роуты для работы с зарплатой.
"""
from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from app.services.salary_service import SalaryService
from app.utils.exceptions import ValidationError, NotFoundError
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('salary', __name__, url_prefix='/api/salary')


@bp.route('/report', methods=['GET'])
@login_required
def get_salary_report():
    """Получает отчет по зарплате с учетом прав доступа."""
    try:
        from app.services.salary_dashboard_service import SalaryDashboardService
        
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        user_id = request.args.get('user_id', type=int)
        role = request.args.get('role')
        master_id = request.args.get('master_id', type=int)
        manager_id = request.args.get('manager_id', type=int)
        
        current_user_id = current_user.id
        current_user_role = current_user.role
        
        # Применяем ограничения доступа
        if current_user_role == 'master':
            # Мастер видит только свои начисления
            employee_info = SalaryDashboardService.get_employee_id_by_user(current_user_id, 'master')
            if not employee_info:
                return jsonify({'success': False, 'error': 'Профиль мастера не найден'}), 403
            user_id = employee_info[0]  # Переопределяем user_id на ID мастера
            role = 'master'
            
        elif current_user_role == 'manager':
            # Менеджер видит только свои начисления (не других менеджеров)
            # Если указан master_id - разрешаем (менеджер может видеть мастеров)
            # Если указан manager_id - проверяем, что это он сам
            if manager_id:
                employee_info = SalaryDashboardService.get_employee_id_by_user(current_user_id, 'manager')
                if not employee_info or employee_info[0] != manager_id:
                    return jsonify({'success': False, 'error': 'Нет прав для просмотра начислений других менеджеров'}), 403
                user_id = manager_id
                role = 'manager'
            elif master_id:
                # Разрешаем просмотр начислений мастера
                user_id = master_id
                role = 'master'
            else:
                # Если не указан фильтр - показываем только свои начисления
                employee_info = SalaryDashboardService.get_employee_id_by_user(current_user_id, 'manager')
                if employee_info:
                    user_id = employee_info[0]
                    role = 'manager'
                else:
                    # Если менеджер не найден - показываем пустой отчет
                    return jsonify({
                        'success': True,
                        'report': {
                            'accruals': [],
                            'summary': {
                                'total_accruals': 0,
                                'total_amount_cents': 0,
                                'total_profit_cents': 0,
                                'total_revenue_cents': 0,
                                'total_owner_net_cents': 0,
                                'unique_users': 0,
                                'unique_orders': 0
                            }
                        }
                    })
        # Для admin - без ограничений
        
        # Если указан мастер или менеджер через параметры, используем их ID как user_id
        if master_id:
            user_id = master_id
            role = 'master'
        elif manager_id:
            user_id = manager_id
            role = 'manager'
        
        report = SalaryService.get_salary_report(
            date_from=date_from,
            date_to=date_to,
            user_id=user_id,
            role=role
        )
        
        return jsonify({'success': True, 'report': report})
    except Exception as e:
        logger.error(f"Ошибка при получении отчета по зарплате: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/recalculate/<int:order_id>', methods=['POST'])
@login_required
def recalculate_salary(order_id):
    """Пересчитывает зарплату по заявке."""
    try:
        accrual_ids = SalaryService.accrue_salary_for_order(order_id, force_recalculate=True)
        return jsonify({'success': True, 'accrual_ids': accrual_ids})
    except NotFoundError as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Ошибка при пересчете зарплаты для заявки {order_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/order/<int:order_id>/details', methods=['GET'])
@login_required
def get_order_accrual_details(order_id):
    """Получает полную детализацию начислений по заявке для модального окна."""
    try:
        from app.services.user_service import UserService

        if not current_user.is_authenticated or not UserService.check_permission(current_user.id, 'salary.view'):
            return jsonify({'success': False, 'error': 'Нет прав доступа'}), 403

        details = SalaryService.get_order_accrual_details(order_id)
        return jsonify({'success': True, 'details': details})
    except Exception as e:
        logger.error(f"Ошибка при получении детализации заявки {order_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/order/<int:order_id>', methods=['GET'])
@login_required
def get_order_accruals(order_id):
    """Получает начисления зарплаты по заявке."""
    try:
        accruals = SalaryService.get_accruals_for_order(order_id)
        return jsonify({'success': True, 'accruals': accruals})
    except Exception as e:
        logger.error(f"Ошибка при получении начислений для заявки {order_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


# Отдельный blueprint для страниц (без /api префикса) - больше не используется
# Роут для страницы отчета перенесен в app/routes/reports.py
bp_page = Blueprint('salary_page', __name__)

