"""
Маршруты для страниц веб-интерфейса
"""

from flask import Flask, render_template
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flask_socketio import SocketIO

from app.utils.config import get_config, get_ext_tag_map
from app.services.scheduler_service import scheduler_service


# Глобальная переменная для отслеживания запуска планировщика
_scheduler_started = False


def init_routes(app: Flask) -> None:
    """Инициализация маршрутов страниц"""
    
    @app.route('/')
    def index():
        """Главная страница"""
        return render_template('index.html', config=get_config())
    
    @app.route('/scheduler')
    def scheduler_page():
        """Страница планировщика"""
        category_options = sorted(set(get_ext_tag_map().values()))
        return render_template('scheduler.html', config=get_config(), category_options=category_options)
    
    @app.route('/config')
    def config_page():
        """Страница настроек"""
        category_options = sorted(set(get_ext_tag_map().values()))
        return render_template('config.html', config=get_config(), category_options=category_options)
    
    # Запуск планировщика при первом запросе
    @app.before_request
    def start_scheduler():
        """Запуск планировщика при первом запросе"""
        global _scheduler_started
        if not _scheduler_started:
            try:
                scheduler_service.start()
                app.logger.info("Scheduler service started")
                _scheduler_started = True
            except Exception as e:
                app.logger.error(f"Failed to start scheduler service: {e}")

