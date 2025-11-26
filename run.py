#!/usr/bin/env python3
"""
Точка входа для S3 Backup Manager
"""

import os
import sys
import logging
import atexit
from datetime import datetime
from typing import Optional, Tuple

from app.web.app import create_app_with_socketio
from app.services.scheduler_service import scheduler_service


def setup_logging(use_timestamped_log: bool = False) -> None:
    """
    Настройка логирования приложения
    
    Args:
        use_timestamped_log: Если True, создает лог-файл с временной меткой
    """
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    handlers = [logging.StreamHandler(sys.stdout)]
    
    if use_timestamped_log:
        log_file = f"{log_dir}/web_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
        handlers.append(logging.FileHandler(log_file, encoding='utf-8'))
    else:
        handlers.append(logging.FileHandler(f"{log_dir}/app.log", encoding='utf-8'))
    
    # Используем улучшенный форматтер
    from app.utils.structured_logger import StructuredFormatter
    formatter = StructuredFormatter()
    
    for handler in handlers:
        handler.setFormatter(formatter)
    
    logging.basicConfig(
        level=logging.INFO,
        handlers=handlers,
        force=True
    )
    
    # Настраиваем логирование для загрузки
    from app.utils.structured_logger import setup_upload_logging
    setup_upload_logging(log_dir)
    
    # Уменьшаем уровень логирования для некоторых библиотек
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('engineio').setLevel(logging.WARNING)
    logging.getLogger('socketio').setLevel(logging.WARNING)


def ensure_directories() -> None:
    """Создает необходимые директории если они не существуют"""
    os.makedirs('data', exist_ok=True)
    os.makedirs('logs', exist_ok=True)


def get_server_config() -> Tuple[str, int, bool]:
    """
    Получает конфигурацию сервера из переменных окружения
    
    Returns:
        Кортеж (host, port, debug)
    """
    host = os.getenv('FLASK_HOST') or os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT') or os.getenv('PORT', '5000'))
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    
    return host, port, debug


def register_shutdown_handlers() -> None:
    """Регистрирует обработчики для корректного завершения приложения"""
    def shutdown_scheduler():
        try:
            if scheduler_service.job_scheduler.scheduler.running:
                scheduler_service.shutdown()
                logging.info("Scheduler service stopped during shutdown")
        except Exception as e:
            logging.error(f"Error during scheduler shutdown: {e}")
    
    atexit.register(shutdown_scheduler)


def main() -> None:
    """Основная функция запуска приложения"""
    # Определяем режим работы (timestamped log для разработки)
    use_timestamped_log = os.getenv('USE_TIMESTAMPED_LOG', 'false').lower() == 'true'
    
    setup_logging(use_timestamped_log)
    ensure_directories()
    
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("Starting S3 Backup Manager Web Application...")
        
        # Создаем приложение с SocketIO
        app, socketio = create_app_with_socketio()
        
        # Регистрируем обработчики завершения
        register_shutdown_handlers()
        
        # Получаем конфигурацию сервера
        host, port, debug = get_server_config()
        
        logger.info(f"Starting web server on {host}:{port} (debug: {debug})")
        
        # Запускаем приложение
        socketio.run(
            app,
            host=host,
            port=port,
            debug=debug,
            use_reloader=debug,
            allow_unsafe_werkzeug=True
        )
        
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    except Exception as e:
        logger.error(f"Failed to start application: {e}", exc_info=True)
        sys.exit(1)
    finally:
        # Обеспечиваем остановку планировщика
        try:
            if scheduler_service.job_scheduler.scheduler.running:
                scheduler_service.shutdown()
                logger.info("Scheduler service stopped during shutdown")
        except Exception as e:
            logger.error(f"Error during scheduler shutdown: {e}")


if __name__ == '__main__':
    main()