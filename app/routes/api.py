"""
Blueprint для общих API endpoints.
"""
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from flask_limiter import Limiter
from app.services.reference_service import ReferenceService
from app.services.action_log_service import ActionLogService
from app.services.user_service import UserService
from app.utils.exceptions import ValidationError, NotFoundError, DatabaseError
import logging

logger = logging.getLogger(__name__)


def log_api_action(action_type: str, entity_type: str, entity_id: int = None, description: str = None, details: dict = None):
    """Логирует действие API."""
    try:
        user_id = current_user.id if current_user.is_authenticated else None
        username = current_user.username if current_user.is_authenticated else None
        ActionLogService.log_action(
            user_id=user_id,
            username=username,
            action_type=action_type,
            entity_type=entity_type,
            entity_id=entity_id,
            description=description,
            details=details
        )
    except Exception as e:
        logger.warning(f"Не удалось записать лог действия: {e}")

bp = Blueprint('api', __name__)

# Инициализация limiter для этого blueprint
limiter = None

def init_limiter(app_limiter):
    """Инициализирует limiter для этого blueprint."""
    global limiter
    limiter = app_limiter

def rate_limit_if_available(limit_str):
    """Декоратор для rate limiting, если limiter доступен."""
    def decorator(f):
        if limiter:
            return limiter.limit(limit_str)(f)
        return f
    return decorator


@bp.before_request
def _generic_api_permission_gate():
    """
    Единый RBAC-гейт для endpoints в generic API blueprint.
    По умолчанию используем права модуля заявок.
    """
    if not request.path.startswith('/api/'):
        return None

    if not current_user.is_authenticated:
        return jsonify({'success': False, 'error': 'auth_required'}), 401

    permission_name = 'view_orders' if request.method in ('GET', 'HEAD', 'OPTIONS') else 'edit_orders'
    if not UserService.check_permission(current_user.id, permission_name):
        return jsonify({
            'success': False,
            'error': 'forbidden',
            'required_permission': permission_name
        }), 403

    return None

# Роуты для статусов заявок перенесены в app/routes/statuses.py
# Старые роуты удалены, так как они не поддерживали новые функции (флаги, архивация и т.д.)
# Все запросы к /api/statuses теперь обрабатываются через statuses_bp

@bp.route('/parts', methods=['GET'])
@login_required
@rate_limit_if_available("200 per hour")
def api_parts():
    """API для получения списка запчастей."""
    try:
        search_query = request.args.get('q', '').strip() or None
        category = request.args.get('category') or None
        
        parts = ReferenceService.get_parts(search_query=search_query, category=category)
        
        # Нормализуем данные: используем retail_price если есть, иначе price
        normalized_parts = []
        for part in parts:
            normalized_part = dict(part)
            # Используем retail_price если есть, иначе price
            if 'retail_price' in normalized_part and normalized_part['retail_price'] is not None:
                normalized_part['price'] = normalized_part['retail_price']
            elif 'price' not in normalized_part or normalized_part['price'] is None:
                normalized_part['price'] = 0.0
            normalized_parts.append(normalized_part)
        
        return jsonify(normalized_parts)
    except Exception as e:
        logger.error(f"Ошибка при получении списка запчастей: {e}")
        return jsonify({'error': 'Internal server error'}), 500

