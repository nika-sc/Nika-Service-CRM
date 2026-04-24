"""
Blueprint для глобального поиска.
"""
from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required
from app.services.search_service import SearchService
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('search', __name__, url_prefix='/search')


@bp.route('', methods=['GET'])
@login_required
def search_results():
    """Страница результатов поиска."""
    query = request.args.get('q', '').strip()
    # Пустой список = «из шапки» — ищем по всем типам; непустой = фильтр с формы результатов.
    type_filters = request.args.getlist('type')
    entity_types = type_filters if type_filters else None

    if not query:
        return render_template(
            'search/results.html',
            query='',
            results={},
            type_filters=type_filters,
        )

    results = SearchService.global_search(
        query=query,
        limit=50,
        entity_types=entity_types,
    )

    return render_template(
        'search/results.html',
        query=query,
        results=results,
        type_filters=type_filters,
    )


@bp.route('/api/autocomplete', methods=['GET'])
@login_required
def autocomplete():
    """API для автодополнения."""
    query = request.args.get('q', '').strip()
    entity_type = request.args.get('type')  # orders, customers, parts
    
    if not query or len(query) < 2:
        return jsonify({'success': True, 'results': []})
    
    try:
        results = SearchService.autocomplete(query, entity_type, limit=10)
        return jsonify({'success': True, 'results': results})
    except Exception as e:
        logger.error(f"Ошибка автодополнения: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api', methods=['GET'])
@login_required
def search_api():
    """API для поиска."""
    query = request.args.get('q', '').strip()
    entity_types = request.args.getlist('type')
    limit = int(request.args.get('limit', 50))
    
    if not query:
        return jsonify({'success': True, 'results': {}})
    
    try:
        results = SearchService.global_search(
            query=query,
            limit=limit,
            entity_types=entity_types if entity_types else None
        )
        return jsonify({'success': True, 'results': results})
    except Exception as e:
        logger.error(f"Ошибка поиска: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
