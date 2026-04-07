"""
Точка входа приложения.
"""
import os

# Загружаем переменные из .env (если файл есть и установлен python-dotenv)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from app import create_app, socketio
from app.config import config

# Определяем окружение (development или production)
env = os.environ.get('FLASK_ENV', 'development')
app = create_app(config.get(env, config['default']))

if __name__ == '__main__':
    # Запуск приложения (DEBUG выключен по умолчанию для безопасности)
    import sys
    import logging
    app.config['DEBUG'] = False
    app.logger.setLevel(logging.INFO)
    for handler in app.logger.handlers:
        handler.setLevel(logging.INFO)
    sys.stderr.write("=" * 80 + "\n")
    sys.stderr.write("Запуск приложения Flask\n")
    sys.stderr.write("=" * 80 + "\n")
    sys.stderr.write("DEBUG режим: False\n")
    sys.stderr.flush()
    
    host = os.environ.get('APP_HOST', '127.0.0.1')
    port = int(os.environ.get('APP_PORT', '5000'))

    if socketio is not None:
        socketio.run(
            app,
            host=host,
            port=port,
            debug=False,
            use_reloader=False
        )
    else:
        app.run(
            host=host,
            port=port,
            debug=False,
            use_reloader=False  # Отключаем reloader для более стабильного вывода
        )
    