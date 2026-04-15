"""
Blueprint для работы с уведомлениями.
"""
from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from app.routes.main import permission_required
from app.services.notification_service import NotificationService
from app.utils.exceptions import ValidationError, NotFoundError
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('notifications', __name__, url_prefix='/api/notifications')


@bp.route('', methods=['GET'])
@login_required
def get_notifications():
    """
    Получает уведомления текущего пользователя.
    
    Query params:
        unread_only: Только непрочитанные (1/0)
        limit: Лимит записей (по умолчанию 50)
    """
    try:
        unread_only = request.args.get('unread_only', '0') == '1'
        limit = int(request.args.get('limit', 50))
        if limit > 200:
            limit = 200
        
        notifications = NotificationService.get_user_notifications(
            user_id=current_user.id,
            unread_only=unread_only,
            limit=limit
        )

        # Нормализуем created_at в timezone-aware ISO, чтобы "N ч. назад" считалось корректно в браузере.
        try:
            from app.utils.datetime_utils import parse_datetime_to_moscow
            normalized = []
            for n in notifications:
                item = dict(n)
                created_at = item.get('created_at')
                if created_at:
                    try:
                        item['created_at'] = parse_datetime_to_moscow(str(created_at)).isoformat()
                    except Exception:
                        pass
                normalized.append(item)
            notifications = normalized
        except Exception:
            pass
        
        return jsonify({'success': True, 'notifications': notifications})
    except Exception as e:
        logger.error(f"Ошибка при получении уведомлений: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/unread-count', methods=['GET'])
@login_required
def get_unread_count():
    """Получает количество непрочитанных уведомлений."""
    try:
        count = NotificationService.get_unread_count(current_user.id)
        return jsonify({'success': True, 'count': count})
    except Exception as e:
        logger.error(f"Ошибка при получении количества непрочитанных уведомлений: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/<int:notification_id>/read', methods=['POST'])
@login_required
def mark_as_read(notification_id):
    """Отмечает уведомление как прочитанное."""
    try:
        success = NotificationService.mark_as_read(notification_id, current_user.id)
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Уведомление не найдено'}), 404
    except Exception as e:
        logger.error(f"Ошибка при отметке уведомления как прочитанного: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/read-all', methods=['POST'])
@login_required
def mark_all_as_read():
    """Отмечает все уведомления как прочитанные."""
    try:
        count = NotificationService.mark_all_as_read(current_user.id)
        return jsonify({'success': True, 'count': count})
    except Exception as e:
        logger.error(f"Ошибка при отметке всех уведомлений как прочитанных: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/preferences', methods=['GET'])
@login_required
def get_preferences():
    """Получает настройки уведомлений пользователя."""
    try:
        preferences = NotificationService.get_notification_preferences(current_user.id)
        return jsonify({'success': True, 'preferences': preferences})
    except Exception as e:
        logger.error(f"Ошибка при получении настроек уведомлений: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/preferences', methods=['POST'])
@login_required
def set_preferences():
    """
    Устанавливает настройки уведомлений.
    
    Body:
        notification_type: Тип уведомления
        enabled: Включены ли уведомления (true/false)
        email_enabled: Включены ли email уведомления (true/false)
        push_enabled: Включены ли push уведомления (true/false)
    """
    try:
        data = request.get_json() or {}
        notification_type = data.get('notification_type')
        
        if not notification_type:
            return jsonify({'success': False, 'error': 'Тип уведомления обязателен'}), 400
        
        success = NotificationService.set_notification_preference(
            user_id=current_user.id,
            notification_type=notification_type,
            enabled=data.get('enabled', True),
            email_enabled=data.get('email_enabled', True),
            push_enabled=data.get('push_enabled', True)
        )
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Не удалось сохранить настройки'}), 500
    except Exception as e:
        logger.error(f"Ошибка при установке настроек уведомлений: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
