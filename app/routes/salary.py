"""
Роуты для работы с зарплатой.
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.services.salary_service import SalaryService
from app.services.salary_dashboard_service import (
    SalaryDashboardService,
    _is_master_role,
    _is_manager_role,
)
from app.services.order_service import OrderService
from app.services.user_service import UserService
from app.utils.exceptions import NotFoundError
from app.utils.error_handlers import api_internal_error
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('salary', __name__, url_prefix='/api/salary')


def _salary_forbidden():
    return jsonify({'success': False, 'error': 'Нет прав доступа'}), 403


def _is_admin_role(role) -> bool:
    return (role or '').strip() == 'admin'


def _require_salary_view():
    if not current_user.is_authenticated:
        return jsonify({'success': False, 'error': 'Нет прав доступа'}), 401
    if not UserService.check_permission(current_user.id, 'salary.view'):
        return _salary_forbidden()
    return None


def _can_recalculate_salary(role) -> bool:
    """Only admin/manager may force-recalculate payroll; masters cannot."""
    return _is_admin_role(role) or _is_manager_role(role)


def _master_owns_order(order_id: int) -> bool:
    employee_info = SalaryDashboardService.get_employee_id_by_user(
        current_user.id, current_user.role
    )
    if not employee_info:
        return False
    order = OrderService.get_order(order_id)
    if not order:
        return False
    return int(getattr(order, 'master_id', 0) or 0) == int(employee_info[0])


def _can_view_order_salary(order_id: int):
    denied = _require_salary_view()
    if denied:
        return denied
    if _is_master_role(current_user.role) and not _master_owns_order(order_id):
        return _salary_forbidden()
    return None


@bp.route('/report', methods=['GET'])
@login_required
def get_salary_report():
    """Получает отчет по зарплате с учетом прав доступа."""
    denied = _require_salary_view()
    if denied:
        return denied

    try:
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        user_id = request.args.get('user_id', type=int)
        role = request.args.get('role')
        master_id = request.args.get('master_id', type=int)
        manager_id = request.args.get('manager_id', type=int)

        current_user_id = current_user.id
        current_user_role = current_user.role

        if _is_master_role(current_user_role):
            employee_info = SalaryDashboardService.get_employee_id_by_user(
                current_user_id, current_user_role
            )
            if not employee_info:
                return jsonify({'success': False, 'error': 'Профиль мастера не найден'}), 403
            user_id = employee_info[0]
            role = 'master'

        elif _is_manager_role(current_user_role):
            if manager_id:
                employee_info = SalaryDashboardService.get_employee_id_by_user(
                    current_user_id, current_user_role
                )
                if not employee_info or employee_info[0] != manager_id:
                    return jsonify({
                        'success': False,
                        'error': 'Нет прав для просмотра начислений других менеджеров',
                    }), 403
                user_id = manager_id
                role = 'manager'
            elif master_id:
                user_id = master_id
                role = 'master'
            else:
                employee_info = SalaryDashboardService.get_employee_id_by_user(
                    current_user_id, current_user_role
                )
                if employee_info:
                    user_id = employee_info[0]
                    role = 'manager'
                else:
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
                                'unique_orders': 0,
                            },
                        },
                    })

        elif _is_admin_role(current_user_role):
            if master_id:
                user_id = master_id
                role = 'master'
            elif manager_id:
                user_id = manager_id
                role = 'manager'

        else:
            return _salary_forbidden()

        report = SalaryService.get_salary_report(
            date_from=date_from,
            date_to=date_to,
            user_id=user_id,
            role=role,
        )

        return jsonify({'success': True, 'report': report})
    except Exception as e:
        logger.error(f"Ошибка при получении отчета по зарплате: {e}", exc_info=True)
        return api_internal_error(e)


@bp.route('/recalculate/<int:order_id>', methods=['POST'])
@login_required
def recalculate_salary(order_id):
    """Пересчитывает зарплату по заявке."""
    denied = _require_salary_view()
    if denied:
        return denied
    if not _can_recalculate_salary(current_user.role):
        return _salary_forbidden()

    try:
        accrual_ids = SalaryService.accrue_salary_for_order(order_id, force_recalculate=True)
        return jsonify({'success': True, 'accrual_ids': accrual_ids})
    except NotFoundError as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Ошибка при пересчете зарплаты для заявки {order_id}: {e}", exc_info=True)
        return api_internal_error(e)


@bp.route('/order/<int:order_id>/details', methods=['GET'])
@login_required
def get_order_accrual_details(order_id):
    """Получает полную детализацию начислений по заявке для модального окна."""
    denied = _can_view_order_salary(order_id)
    if denied:
        return denied

    try:
        details = SalaryService.get_order_accrual_details(order_id)
        return jsonify({'success': True, 'details': details})
    except Exception as e:
        logger.error(f"Ошибка при получении детализации заявки {order_id}: {e}", exc_info=True)
        return api_internal_error(e)


@bp.route('/order/<int:order_id>', methods=['GET'])
@login_required
def get_order_accruals(order_id):
    """Получает начисления зарплаты по заявке."""
    denied = _can_view_order_salary(order_id)
    if denied:
        return denied

    try:
        accruals = SalaryService.get_accruals_for_order(order_id)
        return jsonify({'success': True, 'accruals': accruals})
    except Exception as e:
        logger.error(f"Ошибка при получении начислений для заявки {order_id}: {e}", exc_info=True)
        return api_internal_error(e)


# Отдельный blueprint для страниц (без /api префикса) - больше не используется
# Роут для страницы отчета перенесен в app/routes/reports.py
bp_page = Blueprint('salary_page', __name__)
