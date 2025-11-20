#!/usr/bin/env python3
"""
Точка входа для Web версии S3 Backup Manager
"""
import logging
from app.web.app import create_app_with_socketio

def main():
    """Основная функция Web"""
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    try:
        # Создаем приложение и SocketIO
        app, socketio = create_app_with_socketio()
        
        logger.info("=== S3 Backup Manager Web Interface Starting ===")
        print("\nStarting S3 Backup Manager Web Interface...")
        print("Access at: http://localhost:5000")
        print("Press Ctrl+C to stop the application.\n")
        
        # Запускаем планировщик
        from app.services.scheduler_service import scheduler_service
        scheduler_service.start()
        logger.info("Scheduler service started")
        
        # Запускаем веб-сервер с SocketIO
        socketio.run(app, host='0.0.0.0', port=5000, use_reloader=False, allow_unsafe_werkzeug=True)
        
    except Exception as e:
        logger.error(f"Web application error: {e}")
        return 1
    finally:
        # Останавливаем планировщик при завершении
        try:
            from app.services.scheduler_service import scheduler_service
            scheduler_service.shutdown()
        except:
            pass
    
    return 0

if __name__ == '__main__':
    exit(main())