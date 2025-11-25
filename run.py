#!/usr/bin/env python3
"""
Точка входа для S3 Backup Manager
"""

import os
import logging
from app.web.app import create_app_with_socketio

def setup_logging():
    """Настройка логирования для Docker"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),  # Вывод в stdout для Docker
            logging.FileHandler('logs/app.log')  # Файл логов
        ]
    )

def main():
    """Основная функция запуска"""
    setup_logging()
    
    # Создаем необходимые директории
    os.makedirs('data', exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("Starting S3 Backup Manager Web Application...")
        
        # Создаем приложение с SocketIO
        app, socketio = create_app_with_socketio()
        
        # Запускаем приложение
        host = os.getenv('HOST', '0.0.0.0')
        port = int(os.getenv('PORT', 5000))
        debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
        
        logger.info(f"Starting web server on {host}:{port} (debug: {debug})")
        
        socketio.run(
            app,
            host=host,
            port=port,
            debug=debug,
            allow_unsafe_werkzeug=True
        )
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise

if __name__ == '__main__':
    main()