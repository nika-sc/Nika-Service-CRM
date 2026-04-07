"""
Blueprint для отчетов.
"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from flask_login import login_required, current_user
from app.routes.main import permission_required
from app.services.reports_service import ReportsService
from app.services.order_service import OrderService
from app.services.action_log_service import ActionLogService
from app.services.dashboard_service import DashboardService
from app.services.finance_service import FinanceService
from app.services.user_service import UserService
from app.utils.report_period import normalize_date_range
from app.utils.datetime_utils import get_moscow_now
from app.utils.exceptions import ValidationError, NotFoundError, DatabaseError
import logging

bp = Blueprint('reports', __name__)
logger = logging.getLogger(__name__)


@bp.before_request
def _reports_api_permission_gate():
    """Единый RBAC-гейт для /reports/api/*."""
    if not request.path.startswith('/reports/api/'):
        return None

    if not current_user.is_authenticated:
        return jsonify({'success': False, 'error': 'auth_required'}), 401

    # Сейчас reports API read-only; для write операций будет нужен manage_reports.
    permission_name = 'view_reports'
    if not UserService.check_permission(current_user.id, permission_name):
        return jsonify({
            'success': False,
            'error': 'forbidden',
            'required_permission': permission_name
        }), 403

    return None


@bp.route('/stock')
@login_required
@permission_required('view_reports')
def stock_report():
    """Отчет по остаткам товаров."""
    category = request.args.get('category')
    low_stock_only = request.args.get('low_stock', '0') == '1'

    report = ReportsService.get_stock_report(
        category=category,
        low_stock_only=low_stock_only
    )

    return render_template('reports/stock.html', report=report)


@bp.route('/purchases')
@login_required
@permission_required('view_reports')
def purchases_report():
    """Отчет по закупкам."""
    date_from, date_to = normalize_date_range(
        request.args.get('date_from'),
        request.args.get('date_to'),
        default="today",
    )
    supplier_id = request.args.get('supplier_id', type=int)

    report = ReportsService.get_purchases_report(
        date_from=date_from,
        date_to=date_to,
        supplier_id=supplier_id
    )

    return render_template('reports/purchases.html', report=report, date_from=date_from, date_to=date_to)


@bp.route('/sales')
@login_required
@permission_required('view_reports')
def sales_report():
    """Отчет по продажам."""
    date_from, date_to = normalize_date_range(
        request.args.get('date_from'),
        request.args.get('date_to'),
        default="today",
    )
    customer_id = request.args.get('customer_id', type=int)

    report = ReportsService.get_sales_report(
        date_from=date_from,
        date_to=date_to,
        customer_id=customer_id
    )

    return render_template('reports/sales.html', report=report, date_from=date_from, date_to=date_to)


@bp.route('/profitability')
@login_required
@permission_required('view_reports')
def profitability_report():
    """Отчет по маржинальности."""
    date_from, date_to = normalize_date_range(
        request.args.get('date_from'),
        request.args.get('date_to'),
        default="today",
    )

    report = ReportsService.get_profitability_report(
        date_from=date_from,
        date_to=date_to
    )

    return render_template('reports/profitability.html', report=report, date_from=date_from, date_to=date_to)


@bp.route('/profit')
@login_required
@permission_required('view_reports')
def profit_report():
    """Отчёт по прибыли (доход, расход, себестоимость, чистая прибыль)."""
    date_from, date_to = normalize_date_range(
        request.args.get('date_from'),
        request.args.get('date_to'),
        default='today',
    )
    report = FinanceService.get_profit_report(date_from=date_from, date_to=date_to)
    return render_template(
        'reports/profit.html',
        report=report,
        date_from=date_from,
        date_to=date_to,
    )


@bp.route('/analytics')
@login_required
@permission_required('view_reports')
def analytics_report():
    """Аналитика по товарам и услугам (топ продаж, рентабельность)."""
    date_from, date_to = normalize_date_range(
        request.args.get('date_from'),
        request.args.get('date_to'),
        default='today',
    )
    analytics_data = FinanceService.get_product_analytics(
        date_from=date_from,
        date_to=date_to,
    )
    return render_template(
        'reports/analytics.html',
        analytics=analytics_data,
        date_from=date_from,
        date_to=date_to,
    )


@bp.route('/categories')
@login_required
@permission_required('view_reports')
def categories_report():
    """Отчет по статьям доходов и расходов."""
    date_from, date_to = normalize_date_range(
        request.args.get('date_from'),
        request.args.get('date_to'),
        default="today",
    )
    category_type = request.args.get('category_type')  # 'income' или 'expense'

    report = ReportsService.get_categories_report(
        date_from=date_from,
        date_to=date_to,
        category_type=category_type
    )

    return render_template('reports/categories.html', report=report, date_from=date_from, date_to=date_to, category_type=category_type)


@bp.route('/customers')
@login_required
@permission_required('view_reports')
def customers_report():
    """Отчет по статистике клиентов."""
    date_from, date_to = normalize_date_range(
        request.args.get('date_from'),
        request.args.get('date_to'),
        default="today",
    )

    customers = ReportsService.get_customer_statistics_report(
        date_from=date_from,
        date_to=date_to
    )

    return render_template('reports/customers.html', customers=customers, date_from=date_from, date_to=date_to)


@bp.route('/cash')
@login_required
@permission_required('view_reports')
def cash_report():
    """Касса: поступления по оплатам за период."""
    date_from, date_to = normalize_date_range(
        request.args.get('date_from'),
        request.args.get('date_to'),
        default="today",
    )

    report = ReportsService.get_cash_report(
        date_from=date_from,
        date_to=date_to
    )

    return render_template('reports/cash.html', report=report, date_from=date_from, date_to=date_to)


@bp.route('/orders-log')
@login_required
@permission_required('view_reports')
def orders_log_report():
    """Журнал заявок (по дате создания)."""
    date_from, date_to = normalize_date_range(
        request.args.get('date_from'),
        request.args.get('date_to'),
        default="today",
    )

    filters = {}
    if date_from:
        filters['date_from'] = date_from
    if date_to:
        filters['date_to'] = date_to

    try:
        page = int(request.args.get('page', 1))
        if page < 1:
            page = 1
    except (ValueError, TypeError):
        page = 1

    per_page = 100

    paginator = OrderService.get_orders_with_details(filters, page, per_page)
    orders = sorted(paginator.items, key=lambda o: o.get('created_at'), reverse=True)

    return render_template(
        'reports/orders_log.html',
        orders=orders,
        page=paginator.page,
        per_page=paginator.per_page,
        total=paginator.total,
        pages=paginator.pages,
        date_from=date_from,
        date_to=date_to,
    )


@bp.route('/summary')
@login_required
@permission_required('view_reports')
def summary_report():
    """Сводный отчёт (устаревший URL)."""
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    if date_from or date_to:
        date_from, date_to = normalize_date_range(date_from, date_to, default="none")
        return redirect(url_for('reports.dashboard', date_from=date_from, date_to=date_to))
    return redirect(url_for('reports.dashboard'))


@bp.route('/action-logs')
@login_required
@permission_required('view_reports')
def action_logs_report():
    """Логи действий (интегрированы в отчёты)."""
    # НЕ логируем просмотр action-logs, чтобы избежать бесконечного цикла
    # и засорения собственных логов бесполезными записями

    user_id = request.args.get('user_id', type=int)
    action_type = request.args.get('action_type')
    entity_type = request.args.get('entity_type')
    entity_id = request.args.get('entity_id', type=int)
    date_from, date_to = normalize_date_range(
        request.args.get('date_from'),
        request.args.get('date_to'),
        default="today",
    )
    search_query = request.args.get('search_query', '').strip() or None
    page = int(request.args.get('page', 1))
    per_page = 50

    # Улучшенная логика фильтрации - исключаем системные операции, если не запрошены специально
    include_system = request.args.get('include_system', '').lower() in ('1', 'true', 'yes', 'on')
    exclude_system_actions = not include_system

    paginator = ActionLogService.get_action_logs(
        user_id=user_id,
        action_type=action_type,
        entity_type=entity_type,
        entity_id=entity_id,
        date_from=date_from,
        date_to=date_to,
        search_query=search_query,
        page=page,
        per_page=per_page,
        exclude_system_actions=exclude_system_actions
    )

    return render_template('reports/action_logs.html',
        logs=paginator.items,
        user_id=user_id,
        action_type=action_type,
        entity_type=entity_type,
        entity_id=entity_id,
        date_from=date_from,
        date_to=date_to,
        search_query=search_query,
        page=paginator.page,
        pages=paginator.pages,
        total=paginator.total,
        include_system=not exclude_system_actions
    )


@bp.route('/dashboard')
@login_required
@permission_required('view_reports')
def dashboard():
    """
    Сводный отчёт по компании (Dashboard).

    Метрики: выручка, заказы, магазин, сотрудники.
    Фильтры: период (пресеты + произвольный).
    По умолчанию — сегодня.
    """
    preset = request.args.get('preset')
    date_from, date_to = normalize_date_range(
        request.args.get('date_from'),
        request.args.get('date_to'),
        default="today",
    )
    if date_from and date_to and preset is None:
        today_str = get_moscow_now().date().isoformat()
        if date_from == today_str and date_to == today_str:
            preset = 'today'
        else:
            preset = None

    try:
        data = DashboardService.get_full_dashboard(
            preset=preset,
            date_from=date_from,
            date_to=date_to
        )
    except Exception as e:
        logger.error(f"Ошибка получения данных dashboard: {e}")
        data = {
            'summary': None,
            'created_orders': {},
            'revenue_chart': {},
            'orders_chart': {},
            'orders_by_status': {},
            'overdue_orders': {'count': 0, 'total_sum': 0, 'orders': []},
            'orders_by_master': [],
            'cashflow': {},
            'receivables': {},
            'customers': {},
            'warehouse': {},
            'salary': {},
        }

    period_presets = [
        ('today', 'Сегодня'),
        ('yesterday', 'Вчера'),
        ('last_7_days', 'Последние 7 дней'),
        ('last_30_days', 'Последние 30 дней'),
        ('current_month', 'Текущий месяц'),
        ('last_month', 'Прошлый месяц'),
        ('year_to_date', 'С начала года'),
    ]

    return render_template('reports/dashboard.html',
        data=data,
        preset=preset,
        date_from=date_from,
        date_to=date_to,
        period_presets=period_presets
    )


@bp.route('/api/dashboard')
@login_required
def api_dashboard():
    """API для получения данных dashboard. По умолчанию период — сегодня."""
    preset = request.args.get('preset')
    date_from, date_to = normalize_date_range(
        request.args.get('date_from'),
        request.args.get('date_to'),
        default="today",
    )
    if date_from and date_to and (request.args.get('date_from') or request.args.get('date_to')):
        preset = None

    try:
        data = DashboardService.get_full_dashboard(
            preset=preset,
            date_from=date_from,
            date_to=date_to
        )
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        logger.error(f"API Dashboard error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/dashboard/send-to-director', methods=['POST'])
@login_required
def api_dashboard_send_to_director():
    """
    Отправляет сводный отчёт по компании на email директора (из настроек «Уведомления директору»).
    Период берётся из тела запроса: preset, date_from, date_to (как на странице сводного отчёта).
    """
    from app.services.notification_service import NotificationService

    payload = request.get_json(silent=True) or {}
    preset = payload.get('preset') or request.form.get('preset')
    date_from = payload.get('date_from') or request.form.get('date_from')
    date_to = payload.get('date_to') or request.form.get('date_to')
    date_from, date_to = normalize_date_range(date_from, date_to, default="today")
    if (date_from or date_to) and (payload.get('date_from') or payload.get('date_to') or request.form.get('date_from') or request.form.get('date_to')):
        preset = None

    success, err_msg = NotificationService.send_director_dashboard_report(
        preset=preset,
        date_from=date_from,
        date_to=date_to,
    )
    if success:
        return jsonify({'success': True, 'message': 'Отчёт отправлен на email директора.'})
    return jsonify({'success': False, 'error': err_msg or 'Ошибка отправки'}), 400


@bp.route('/salary')
@login_required
@permission_required('view_reports')
def salary_report():
    """Отчет по зарплате с учетом прав доступа."""
    from app.services.master_service import MasterService
    from app.services.manager_service import ManagerService
    from app.services.salary_dashboard_service import SalaryDashboardService

    date_from, date_to = normalize_date_range(
        request.args.get('date_from'),
        request.args.get('date_to'),
        default="today",
    )

    user_role = current_user.role
    user_id = current_user.id

    masters = []
    managers = []

    if user_role == 'master':
        employee_info = SalaryDashboardService.get_employee_id_by_user(user_id, 'master')
        if employee_info:
            master_id, _ = employee_info
            master = MasterService.get_master_by_id(master_id)
            if master:
                masters = [master]

    elif user_role == 'manager':
        masters = MasterService.get_all_masters(active_only=True)
        employee_info = SalaryDashboardService.get_employee_id_by_user(user_id, 'manager')
        if employee_info:
            manager_id, _ = employee_info
            manager = ManagerService.get_manager_by_id(manager_id)
            if manager:
                managers = [manager]

    elif user_role == 'admin':
        masters = MasterService.get_all_masters(active_only=True)
        managers = ManagerService.get_all_managers(active_only=True)

    return render_template('salary/report.html',
                         masters=masters,
                         managers=managers,
                         current_user_role=user_role,
                         date_from=date_from,
                         date_to=date_to)


@bp.route('/salary-debts')
@login_required
@permission_required('view_reports')
def salary_debts_report():
    """Отчет по долгам сотрудников."""
    from app.services.salary_dashboard_service import SalaryDashboardService

    role = request.args.get('role')
    status = request.args.get('status', 'active')

    data = SalaryDashboardService.get_salary_debts(role=role, status=status)
    return render_template(
        'reports/salary_debts.html',
        items=data.get('items', []),
        totals=data.get('totals', {}),
        role=role,
        status=status
    )
