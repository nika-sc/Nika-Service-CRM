"""
Blueprint для API шаблонов заявок.
Функционал отключен.
"""
from flask import Blueprint, jsonify
from flask_login import login_required

bp = Blueprint('templates', __name__, url_prefix='/api/templates')


def _templates_disabled_response():
    return jsonify({
        'success': False,
        'error': 'Функционал шаблонов заявок отключен'
    }), 410


@bp.route('', methods=['GET', 'POST'])
@login_required
def templates_root_disabled():
    return _templates_disabled_response()


@bp.route('/<int:template_id>', methods=['GET', 'PUT', 'PATCH', 'DELETE'])
@login_required
def template_item_disabled(template_id):
    return _templates_disabled_response()
