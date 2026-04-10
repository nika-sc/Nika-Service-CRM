"""
Blueprint для работы с комментариями (загрузка файлов).
"""
from flask import Blueprint, request, jsonify, send_file
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
import uuid
from app.config import Config
from app.database.connection import get_db_connection
import sqlite3
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('comments', __name__, url_prefix='/api/comments')


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'txt', 'zip', 'rar'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def allowed_file(filename):
    """Проверяет, разрешен ли тип файла."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@bp.route('/upload', methods=['POST'])
@login_required
def upload_attachment():
    """
    Загружает файл для комментария.
    
    Returns:
        JSON с attachment_id и file_path
    """
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'Файл не загружен'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'Файл не выбран'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'Недопустимый тип файла'}), 400
        
        # Проверяем размер файла
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > MAX_FILE_SIZE:
            return jsonify({'success': False, 'error': 'Файл слишком большой (максимум 10 MB)'}), 400
        
        # Сохраняем файл
        upload_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'uploads', 'comments')
        os.makedirs(upload_dir, exist_ok=True)
        
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        file_path = os.path.join(upload_dir, unique_filename)
        
        file.save(file_path)
        
        # Сохраняем информацию о файле в БД
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO comment_attachments 
                (filename, file_path, file_size, mime_type, created_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (filename, file_path, file_size, file.content_type))
            conn.commit()
            attachment_id = cursor.lastrowid
        
        return jsonify({
            'success': True,
            'attachment_id': attachment_id,
            'filename': filename,
            'file_path': f'/api/comments/attachment/{attachment_id}'
        }), 201
    except Exception as e:
        logger.error(f"Ошибка при загрузке файла: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/attachment/<int:attachment_id>', methods=['GET'])
@login_required
def get_attachment(attachment_id):
    """Получает файл вложения."""
    try:
        with get_db_connection(row_factory=sqlite3.Row) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT filename, file_path, mime_type
                FROM comment_attachments
                WHERE id = ?
            ''', (attachment_id,))
            row = cursor.fetchone()
            
            if not row:
                return jsonify({'success': False, 'error': 'Файл не найден'}), 404
            
            file_path = row['file_path']
            if not os.path.exists(file_path):
                return jsonify({'success': False, 'error': 'Файл не найден на диске'}), 404
            
            return send_file(
                file_path,
                mimetype=row['mime_type'] or 'application/octet-stream',
                as_attachment=True,
                download_name=row['filename']
            )
    except Exception as e:
        logger.error(f"Ошибка при получении файла: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
