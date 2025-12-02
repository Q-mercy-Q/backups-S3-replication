"""
Маршруты для страниц веб-интерфейса
"""

from flask import Flask, render_template
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flask_socketio import SocketIO

from flask_login import login_required, current_user

from app.utils.config import get_config, get_ext_tag_map
from app.services.scheduler_service import scheduler_service


# Глобальная переменная для отслеживания запуска планировщика
_scheduler_started = False


def init_routes(app: Flask) -> None:
    """Инициализация маршрутов страниц"""
    
    @app.route('/')
    @login_required
    def index():
        """Главная страница (Dashboard)"""
        return render_template('dashboard.html')
    
    @app.route('/upload-manager')
    @login_required
    def upload_manager_page():
        """Страница менеджера загрузки"""
        return render_template('upload-manager.html', config=get_config(user_id=current_user.id))
    
    @app.route('/scheduler')
    @login_required
    def scheduler_page():
        """Страница планировщика"""
        category_options = sorted(set(get_ext_tag_map(user_id=current_user.id).values()))
        return render_template('scheduler.html', config=get_config(user_id=current_user.id), category_options=category_options)
    
    @app.route('/config')
    @login_required
    def config_page():
        """Страница настроек (персональная конфигурация пользователя)"""
        category_options = sorted(set(get_ext_tag_map(user_id=current_user.id).values()))
        return render_template('config.html', config=get_config(user_id=current_user.id), category_options=category_options)
    
    @app.route('/s3-browser')
    @login_required
    def s3_browser_page():
        """Страница просмотра S3 бакета"""
        from app.utils.config import get_s3_bucket
        return render_template('s3-browser.html', bucket=get_s3_bucket(user_id=current_user.id))
    
    @app.route('/s3-management')
    @login_required
    def s3_management_page():
        """Страница расширенного управления S3"""
        return render_template('s3-management.html')
    
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

