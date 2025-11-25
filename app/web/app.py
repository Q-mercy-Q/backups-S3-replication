import os
import logging
import atexit
from flask import Flask
from flask_socketio import SocketIO

# Отключаем лишние логи Flask и SocketIO
logging.getLogger('werkzeug').setLevel(logging.WARNING)
logging.getLogger('engineio').setLevel(logging.WARNING)
logging.getLogger('socketio').setLevel(logging.WARNING)

def create_app():
    """Фабрика для создания Flask приложения"""
    app = Flask(__name__, 
                template_folder='templates',
                static_folder='static')
    app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 's3-upload-manager-secret-key')
    app.config['DEBUG'] = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    
    return app

def create_app_with_socketio():
    """Создание приложения с SocketIO для запуска"""
    app = create_app()
    socketio = SocketIO(
        app, 
        cors_allowed_origins="*", 
        async_mode='threading', 
        logger=False, 
        engineio_logger=False
    )
    
    # Регистрируем обработчики
    from app.web import routes, socket_events, background_tasks
    
    # Инициализируем маршруты
    routes.init_routes(app)
    
    # Инициализируем SocketIO события
    socket_events.init_socket_events(socketio)
    
    # Инициализируем фоновые задачи
    background_tasks.init_app(app, socketio)
    
    # Запускаем планировщик при создании приложения
    try:
        from app.services.scheduler_service import scheduler_service
        
        # Устанавливаем socketio в scheduler_service для отправки обновлений
        scheduler_service.set_socketio(socketio)
        
        if not scheduler_service.job_scheduler.scheduler.running:
            scheduler_service.start()
            app.logger.info("Scheduler service started during app initialization")
            
            # Регистрируем остановку при завершении приложения
            def shutdown_scheduler():
                if scheduler_service.job_scheduler.scheduler.running:
                    scheduler_service.shutdown()
                    app.logger.info("Scheduler service stopped on application exit")
            
            atexit.register(shutdown_scheduler)
        else:
            app.logger.info("Scheduler service already running")
    except Exception as e:
        app.logger.error(f"Failed to start scheduler service: {e}")
    
    return app, socketio