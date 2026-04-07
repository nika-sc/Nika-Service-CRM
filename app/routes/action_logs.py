"""
Blueprint для просмотра логов действий.
"""
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app.routes.main import permission_required
from app.services.action_log_service import ActionLogService
from app.utils.exceptions import ValidationError, NotFoundError, DatabaseError
import logging

bp = Blueprint('action_logs', __name__)
logger = logging.getLogger(__name__)


@bp.route('/action-logs')
@login_required
@permission_required('view_action_logs')
def action_logs():
    """Список логов действий."""
    user_id = request.args.get('user_id', type=int)
    action_type = request.args.get('action_type')
    entity_type = request.args.get('entity_type')
    entity_id = request.args.get('entity_id', type=int)
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    page = int(request.args.get('page', 1))
    per_page = 50
    
    paginator = ActionLogService.get_action_logs(
        user_id=user_id,
        action_type=action_type,
        entity_type=entity_type,
        entity_id=entity_id,
        date_from=date_from,
        date_to=date_to,
        search_query=None,
        page=page,
        per_page=per_page
    )
    
    return render_template('action_logs.html',
        logs=paginator.items,
        user_id=user_id,
        action_type=action_type,
        entity_type=entity_type,
        entity_id=entity_id,
        date_from=date_from,
        date_to=date_to,
        page=paginator.page,
        pages=paginator.pages,
        total=paginator.total
    )


@bp.route('/action-logs/<entity_type>/<int:entity_id>')
@login_required
@permission_required('view_action_logs')
def entity_logs(entity_type, entity_id):
    """Логи по конкретной сущности."""
    logs = ActionLogService.get_entity_logs(entity_type, entity_id)
    
    return render_template('action_logs.html',
        logs=logs,
        entity_type=entity_type,
        entity_id=entity_id
    )

