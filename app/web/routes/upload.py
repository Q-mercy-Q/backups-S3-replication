"""
API маршруты для управления загрузкой файлов
"""

import threading
from flask import Flask, jsonify, request
from typing import TYPE_CHECKING, Dict, Any, Tuple

if TYPE_CHECKING:
    from flask_socketio import SocketIO

from app.utils.config import get_config, update_config, upload_stats
from app.services.s3_client import test_connection
from app.web.background_tasks import run_upload, scan_files_with_config, get_stats_data
from app.utils.upload_control import upload_control
import humanize


def init_routes(app: Flask, socketio: 'SocketIO' = None) -> None:
    """Инициализация маршрутов загрузки
    
    Args:
        app: Flask приложение
        socketio: SocketIO экземпляр (не используется, но требуется для совместимости с API)
    """
    
    @app.route('/api/start_upload', methods=['POST'])
    def api_start_upload():
        """API для запуска загрузки"""
        return _handle_start_upload(app)
    
    @app.route('/api/stop_upload', methods=['POST'])
    def api_stop_upload():
        """API для остановки загрузки"""
        return _handle_stop_upload(app)
    
    @app.route('/api/test_connection', methods=['POST'])
    def api_test_connection():
        """API для тестирования соединения"""
        return _handle_test_connection(app)
    
    @app.route('/api/scan_files', methods=['POST'])
    def api_scan_files():
        """API для сканирования файлов"""
        return _handle_scan_files(app)
    
    @app.route('/api/statistics')
    def api_statistics():
        """API для получения статистики"""
        return jsonify(get_stats_data()), 200
    
    def _handle_start_upload(app: Flask) -> Tuple[Dict[str, Any], int]:
        """Обработка запуска загрузки"""
        from app.web.background_tasks import stop_event
        
        if upload_stats.is_running:
            return jsonify({'status': 'error', 'message': 'Upload already in progress'}), 409
        
        # Обновляем конфигурацию из запроса
        config_data = request.get_json(silent=True) or {}
        if config_data:
            try:
                update_config(config_data)
            except Exception as e:
                return jsonify({'status': 'error', 'message': f'Invalid configuration: {e}'}), 400
        
        # Проверяем наличие обязательных полей для S3
        current_config = get_config()
        s3_required = ['S3_ACCESS_KEY', 'S3_SECRET_KEY']
        missing_s3_fields = [field for field in s3_required if not current_config.get(field)]
        
        if missing_s3_fields:
            return jsonify({
                'status': 'error', 
                'message': f'Missing S3 credentials: {", ".join(missing_s3_fields)}. Please update configuration.'
            }), 400
        
        # Сброс события остановки
        stop_event.clear()
        
        # Запуск загрузки в отдельном потоке
        upload_thread = threading.Thread(target=run_upload, daemon=True)
        upload_thread.start()
        
        return jsonify({'status': 'success', 'message': 'Upload started'}), 200
    
    def _handle_stop_upload(app: Flask) -> Tuple[Dict[str, Any], int]:
        """Обработка остановки загрузки"""
        from app.web.background_tasks import stop_event
        
        if not upload_stats.is_running:
            return jsonify({'status': 'error', 'message': 'No upload in progress'}), 409
        
        data = request.get_json(silent=True) or {}
        mode = data.get('mode', 'graceful')
        finish_current = mode != 'force'
        
        upload_control.request_stop(finish_current=finish_current)
        
        if not finish_current:
            upload_stats.is_running = False
        
        stop_event.set()
        
        app.logger.info("Upload stop requested (%s mode)", "graceful" if finish_current else "force")
        
        message = (
            'Upload stop requested. Current operations will complete.'
            if finish_current else
            'Upload stop requested. Stopping all active operations immediately.'
        )
        
        return jsonify({'status': 'success', 'message': message}), 200
    
    def _handle_test_connection(app: Flask) -> Tuple[Dict[str, Any], int]:
        """Обработка тестирования соединения"""
        try:
            # Обновляем конфигурацию из запроса если есть
            config_data = request.get_json(silent=True) or {}
            if config_data:
                update_config(config_data)
            
            # Проверяем наличие обязательных полей для S3
            current_config = get_config()
            s3_required = ['S3_ACCESS_KEY', 'S3_SECRET_KEY']
            missing_s3_fields = [field for field in s3_required if not current_config.get(field)]
            
            if missing_s3_fields:
                return jsonify({
                    'status': 'error', 
                    'message': f'Missing S3 credentials: {", ".join(missing_s3_fields)}. Please update configuration.'
                }), 400
                
            if test_connection():
                return jsonify({'status': 'success', 'message': 'Connection test successful'}), 200
            else:
                return jsonify({'status': 'error', 'message': 'Connection test failed'}), 500
        except Exception as e:
            app.logger.error(f"Connection test error: {e}", exc_info=True)
            return jsonify({'status': 'error', 'message': f'Connection test failed: {e}'}), 500
    
    def _handle_scan_files(app: Flask) -> Tuple[Dict[str, Any], int]:
        """Обработка сканирования файлов"""
        try:
            # Обновляем конфигурацию из запроса
            config_data = request.get_json(silent=True) or {}
            if config_data:
                update_config(config_data)
                
            files = scan_files_with_config()
            
            if files is not None and len(files) > 0:
                return jsonify({
                    'status': 'success', 
                    'message': f'Found {len(files)} files for upload',
                    'files_count': len(files),
                    'skipped_existing': upload_stats.skipped_existing,
                    'skipped_time': upload_stats.skipped_time,
                    'total_size': humanize.naturalsize(upload_stats.total_bytes)
                }), 200
            else:
                return jsonify({
                    'status': 'warning', 
                    'message': 'No files found for upload',
                    'skipped_existing': upload_stats.skipped_existing,
                    'skipped_time': upload_stats.skipped_time
                }), 200
        except Exception as e:
            app.logger.error(f"File scan error: {e}", exc_info=True)
            return jsonify({'status': 'error', 'message': f'File scan error: {e}'}), 500

