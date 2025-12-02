"""
Модуль маршрутов веб-приложения
"""

from flask import Flask
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flask_socketio import SocketIO

from . import config, upload, scheduler, health, pages, files, admin, nfs, s3_browser, s3_management


def init_routes(app: Flask, socketio: 'SocketIO') -> None:
    """
    Инициализация всех маршрутов приложения
    
    Args:
        app: Flask приложение
        socketio: SocketIO экземпляр
    """
    # Регистрируем маршруты страниц
    pages.init_routes(app)
    
    # Регистрируем API маршруты
    config.init_routes(app)
    upload.init_routes(app, socketio)
    scheduler.init_routes(app)
    health.init_routes(app)
    files.init_routes(app)
    admin.init_routes(app)
    nfs.init_routes(app)
    s3_browser.init_routes(app)
    s3_management.init_routes(app)
    
    # Регистрируем обработчики ошибок
    _register_error_handlers(app)


def _register_error_handlers(app: Flask) -> None:
    """Регистрация обработчиков ошибок"""
    
    @app.errorhandler(404)
    def not_found(error):
        from flask import jsonify
        return jsonify({'status': 'error', 'message': 'Endpoint not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f"Internal server error: {error}", exc_info=True)
        from flask import jsonify
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

