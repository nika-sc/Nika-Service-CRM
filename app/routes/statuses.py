"""
Роуты для управления статусами заявок.
"""
from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from app.services.status_service import StatusService
from app.utils.exceptions import ValidationError, NotFoundError, DatabaseError
from app.routes.main import permission_required
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('statuses', __name__, url_prefix='/api/statuses')
def _normalize_flag(value):
    """Нормализует значения флагов из JSON (true/false/1/0/'1'/'0'/'on'/'off')."""
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return 1 if int(value) != 0 else 0
    if isinstance(value, str):
        v = value.strip().lower()
        if v in ('1', 'true', 'yes', 'on'):
            return 1
        if v in ('0', 'false', 'no', 'off', ''):
            return 0
    return 0


# Страничный роут (для настроек)
bp_page = Blueprint('statuses_page', __name__)


@bp_page.route('/settings/statuses', methods=['GET'])
@login_required
@permission_required('manage_statuses')
def statuses_settings_page():
    """Страница управления статусами - редирект на /settings#statuses (объединено с базовым управлением)."""
    from flask import redirect, url_for
    return redirect(url_for('main.settings', _anchor='statuses'))


@bp.route('', methods=['GET'])
@login_required
@permission_required('view_orders')
def get_statuses():
    """Получает список статусов."""
    try:
        include_archived = request.args.get('include_archived', '0') == '1'
        logger.info(f"Запрос статусов: include_archived={include_archived}, args={request.args}")
        # Очищаем кэш при запросе архивных, чтобы гарантировать свежие данные
        if include_archived:
            from app.utils.cache import clear_cache
            clear_cache(key_prefix='ref_order_statuses')
        statuses = StatusService.get_all_statuses(include_archived=include_archived)
        
        # Преобразуем статусы в словари, если они еще не словари
        statuses_list = []
        for status in statuses:
            if isinstance(status, dict):
                statuses_list.append(status)
            else:
                # Если это объект Row, преобразуем в словарь
                statuses_list.append(dict(status))
        
        # Логируем количество архивных статусов
        archived_count = sum(1 for s in statuses_list if s.get('is_archived') == 1 or s.get('is_archived') is True)
        logger.info(f"Возвращено статусов: всего {len(statuses_list)}, архивных: {archived_count}")
        
        return jsonify({'success': True, 'statuses': statuses_list})
    except Exception as e:
        logger.error(f"Ошибка при получении статусов: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/<int:status_id>', methods=['GET'])
@login_required
@permission_required('view_orders')
def get_status(status_id):
    """Получает статус по ID."""
    try:
        status = StatusService.get_status_by_id(status_id)
        return jsonify({'success': True, 'status': status})
    except NotFoundError as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Ошибка при получении статуса {status_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('', methods=['POST'])
@login_required
@permission_required('manage_statuses')
def create_status():
    """Создает новый статус."""
    try:
        data = request.get_json() or {}
        logger.info(f"Создание статуса, полученные данные: {data}")
        
        # Нормализуем флаги - всегда передаем значения (0 или 1)
        triggers_payment_modal = _normalize_flag(data.get('triggers_payment_modal')) or 0
        accrues_salary = _normalize_flag(data.get('accrues_salary')) or 0
        is_archived = _normalize_flag(data.get('is_archived')) or 0
        is_final = _normalize_flag(data.get('is_final')) or 0
        blocks_edit = _normalize_flag(data.get('blocks_edit')) or 0
        requires_warranty = _normalize_flag(data.get('requires_warranty')) or 0
        requires_comment = _normalize_flag(data.get('requires_comment')) or 0
        
        # Обрабатываем name и group_name - обрезаем пробелы и проверяем на пустоту
        name = data.get('name', '').strip() if data.get('name') else None
        group_name_raw = data.get('group_name')
        
        # Обрабатываем group_name - проверяем все возможные варианты
        logger.info(f"DEBUG: group_name_raw получен: {repr(group_name_raw)}, тип: {type(group_name_raw)}")
        
        if group_name_raw is not None:
            # Преобразуем в строку если это не строка
            if not isinstance(group_name_raw, str):
                group_name_raw = str(group_name_raw)
            group_name = group_name_raw.strip()
            if not group_name:  # Если после обрезки пусто, устанавливаем None
                group_name = None
        else:
            group_name = None
        
        logger.info(f"Обработка данных: name='{name}', group_name_raw={repr(group_name_raw)}, group_name={repr(group_name)}")
        
        # Если name пустой, это ошибка
        if not name:
            raise ValidationError("Название статуса не может быть пустым")
        
        status_id = StatusService.create_status(
            name=name,
            code=data.get('code'),
            color=data.get('color', '#007bff'),
            group_name=group_name,
            is_default=int(data.get('is_default', 0)),
            sort_order=int(data.get('sort_order', 0)),
            triggers_payment_modal=triggers_payment_modal,
            accrues_salary=accrues_salary,
            is_archived=is_archived,
            is_final=is_final,
            blocks_edit=blocks_edit,
            requires_warranty=requires_warranty,
            requires_comment=requires_comment,
            client_name=data.get('client_name'),
            client_description=data.get('client_description')
        )
        
        # Очищаем кэш справочников статусов
        from app.utils.cache import clear_cache
        clear_cache(key_prefix='ref_order_statuses')
        
        logger.info(f"Статус создан с ID: {status_id}, group_name: {group_name}")
        return jsonify({'success': True, 'status_id': status_id}), 201
    except ValidationError as e:
        logger.error(f"Ошибка валидации при создании статуса: {e}")
        return jsonify({'success': False, 'error': str(e)}), 400
    except DatabaseError as e:
        logger.error(f"Ошибка БД при создании статуса: {e}")
        # Преобразуем технические ошибки БД в понятные сообщения
        error_msg = str(e)
        if 'UNIQUE constraint failed' in error_msg and 'code' in error_msg:
            return jsonify({'success': False, 'error': 'Статус с таким кодом уже существует. Пожалуйста, используйте другой код.'}), 400
        return jsonify({'success': False, 'error': f'Ошибка базы данных: {error_msg}'}), 500
    except Exception as e:
        logger.error(f"Ошибка при создании статуса: {e}", exc_info=True)
        # Преобразуем технические ошибки в понятные сообщения
        error_msg = str(e)
        if 'UNIQUE constraint failed' in error_msg and 'code' in error_msg:
            return jsonify({'success': False, 'error': 'Статус с таким кодом уже существует. Пожалуйста, используйте другой код.'}), 400
        return jsonify({'success': False, 'error': f'Ошибка: {error_msg}'}), 500


@bp.route('/<int:status_id>', methods=['PATCH'])
@login_required
@permission_required('manage_statuses')
def update_status(status_id):
    """Обновляет статус."""
    try:
        data = request.get_json() or {}
        logger.info(f"Обновление статуса {status_id}, полученные данные: {data}")
        
        # Нормализуем флаги - всегда передаем, даже если 0 (чтобы сбросить флаг)
        # Если поле не передано в запросе, оставляем None (не обновляем)
        triggers_payment_modal = _normalize_flag(data.get('triggers_payment_modal')) if 'triggers_payment_modal' in data else None
        accrues_salary = _normalize_flag(data.get('accrues_salary')) if 'accrues_salary' in data else None
        is_archived = _normalize_flag(data.get('is_archived')) if 'is_archived' in data else None
        is_final = _normalize_flag(data.get('is_final')) if 'is_final' in data else None
        blocks_edit = _normalize_flag(data.get('blocks_edit')) if 'blocks_edit' in data else None
        requires_warranty = _normalize_flag(data.get('requires_warranty')) if 'requires_warranty' in data else None
        requires_comment = _normalize_flag(data.get('requires_comment')) if 'requires_comment' in data else None
        is_default = int(data.get('is_default', 0)) if 'is_default' in data else None
        
        # Обрабатываем name и group_name - обрезаем пробелы
        name = data.get('name')
        if name is not None:
            name = name.strip()
            if not name:  # Если после обрезки пусто, это ошибка
                raise ValidationError("Название статуса не может быть пустым")
        
        group_name = data.get('group_name')
        if group_name is not None:
            group_name = group_name.strip()
            if not group_name:  # Если после обрезки пусто, устанавливаем None
                group_name = None
        
        success = StatusService.update_status(
            status_id=status_id,
            name=name,
            color=data.get('color'),
            group_name=group_name,
            sort_order=data.get('sort_order'),
            is_default=is_default,
            triggers_payment_modal=triggers_payment_modal,
            accrues_salary=accrues_salary,
            is_archived=is_archived,
            is_final=is_final,
            blocks_edit=blocks_edit,
            requires_warranty=requires_warranty,
            requires_comment=requires_comment,
            client_name=data.get('client_name'),
            client_description=data.get('client_description')
        )
        
        # Очищаем кэш справочников статусов
        if success:
            from app.utils.cache import clear_cache
            clear_cache(key_prefix='ref_order_statuses')
        
        logger.info(f"Статус {status_id} обновлен: success={success}, name={name}, group_name={group_name}")
        return jsonify({'success': success})
    except NotFoundError as e:
        logger.error(f"Статус {status_id} не найден: {e}")
        return jsonify({'success': False, 'error': str(e)}), 404
    except ValidationError as e:
        logger.error(f"Ошибка валидации при обновлении статуса {status_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Ошибка при обновлении статуса {status_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/<int:status_id>/archive', methods=['POST'])
@login_required
@permission_required('manage_statuses')
def archive_status(status_id):
    """Архивирует статус."""
    try:
        success = StatusService.archive_status(status_id)
        if success:
            from app.utils.cache import clear_cache
            clear_cache(key_prefix='ref_order_statuses')
        return jsonify({'success': success})
    except NotFoundError as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Ошибка при архивации статуса {status_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/<int:status_id>/unarchive', methods=['POST'])
@login_required
@permission_required('manage_statuses')
def unarchive_status(status_id):
    """Разархивирует статус."""
    try:
        success = StatusService.unarchive_status(status_id)
        if success:
            from app.utils.cache import clear_cache
            clear_cache(key_prefix='ref_order_statuses')
        return jsonify({'success': success})
    except NotFoundError as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Ошибка при разархивации статуса {status_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/<int:status_id>', methods=['DELETE'])
@login_required
@permission_required('manage_statuses')
def delete_status(status_id):
    """Удаляет статус."""
    try:
        success = StatusService.delete_status(status_id)
        if success:
            from app.utils.cache import clear_cache
            clear_cache(key_prefix='ref_order_statuses')
        return jsonify({'success': success})
    except NotFoundError as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except ValidationError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Ошибка при удалении статуса {status_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/reorder', methods=['POST'])
@login_required
@permission_required('manage_statuses')
def reorder_statuses():
    """Изменяет порядок статусов."""
    try:
        data = request.get_json() or {}
        status_ids = data.get('status_ids', [])
        
        if not isinstance(status_ids, list):
            return jsonify({'success': False, 'error': 'status_ids должен быть массивом'}), 400
        
        success = StatusService.reorder_statuses(status_ids)
        return jsonify({'success': success})
    except ValidationError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Ошибка при изменении порядка статусов: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


