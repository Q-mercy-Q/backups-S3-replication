"""
API маршруты для проверки состояния приложения
"""

from flask import Flask, jsonify
from typing import Dict, Any, Tuple
from datetime import datetime

from app.services.scheduler_service import scheduler_service
from app.services.s3_client import test_connection
from app.utils.config import upload_stats


def init_routes(app: Flask) -> None:
    """Инициализация маршрутов проверки здоровья"""
    
    @app.route('/api/health')
    def api_health():
        """API для проверки состояния приложения"""
        try:
            health_info = {
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'version': '1.0.0',
                'services': {
                    'scheduler': 'running' if scheduler_service.job_scheduler.scheduler.running else 'stopped',
                    'upload_manager': 'running' if upload_stats.is_running else 'idle'
                }
            }
            
            # Проверяем доступность S3
            try:
                s3_accessible = test_connection()
                health_info['services']['s3'] = 'connected' if s3_accessible else 'disconnected'
            except Exception as e:
                health_info['services']['s3'] = f'error: {str(e)}'
            
            return jsonify(health_info), 200
            
        except Exception as e:
            app.logger.error(f"Health check failed: {e}", exc_info=True)
            return jsonify({'status': 'error', 'message': str(e)}), 500

