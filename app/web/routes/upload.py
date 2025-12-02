"""
API маршруты для управления загрузкой файлов
"""

import threading
from flask import Flask, jsonify, request
from typing import TYPE_CHECKING, Dict, Any, Tuple

if TYPE_CHECKING:
    from flask_socketio import SocketIO

from flask_login import login_required, current_user

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
    @login_required
    def api_start_upload():
        """API для запуска загрузки"""
        return _handle_start_upload(app)
    
    @app.route('/api/stop_upload', methods=['POST'])
    @login_required
    def api_stop_upload():
        """API для остановки загрузки"""
        return _handle_stop_upload(app)
    
    @app.route('/api/test_connection', methods=['POST'])
    @login_required
    def api_test_connection():
        """API для тестирования соединения"""
        return _handle_test_connection(app)
    
    @app.route('/api/scan_files', methods=['POST'])
    @login_required
    def api_scan_files():
        """API для сканирования файлов"""
        return _handle_scan_files(app)
    
    @app.route('/api/statistics')
    @login_required
    def api_statistics():
        """API для получения статистики"""
        return jsonify(get_stats_data()), 200
    
    def _handle_start_upload(app: Flask) -> Tuple[Dict[str, Any], int]:
        """Обработка запуска загрузки"""
        from app.web.background_tasks import stop_event
        
        if upload_stats.is_running and upload_stats.user_id != current_user.id:
            return jsonify({
                'status': 'error', 
                'message': f'Upload already in progress by another user (user_id: {upload_stats.user_id})'
            }), 409
        
        # Получаем config_id из запроса, если указан
        config_data = request.get_json(silent=True) or {}
        config_id = config_data.get('CONFIG_ID')
        
        # ВАЖНО: Получаем персональную конфигурацию пользователя из БД
        # Если указан config_id, загружаем конкретный конфиг, иначе конфиг по умолчанию
        if config_id:
            from app.utils.user_config import get_user_config
            user_config_obj = get_user_config(user_id=current_user.id, config_id=int(config_id))
            if user_config_obj:
                current_config = user_config_obj.to_dict()
            else:
                return jsonify({'status': 'error', 'message': 'Configuration not found'}), 404
        else:
            current_config = get_config(user_id=current_user.id)
        
        # Логируем наличие S3 credentials (без значений для безопасности)
        has_access_key = bool(current_config.get('S3_ACCESS_KEY', '').strip())
        has_secret_key = bool(current_config.get('S3_SECRET_KEY', '').strip())
        app.logger.info(
            f"Loaded user config for user_id={current_user.id}: "
            f"NFS_PATH={current_config.get('NFS_PATH')}, "
            f"S3_ENDPOINT={current_config.get('S3_ENDPOINT')}, "
            f"S3_BUCKET={current_config.get('S3_BUCKET')}, "
            f"S3_ACCESS_KEY present={has_access_key}, "
            f"S3_SECRET_KEY present={has_secret_key}"
        )
        
        # Обновляем конфигурацию из запроса, если она передана
        # ВАЖНО: Обновляем только если переданы реальные поля конфигурации (не служебные)
        config_data = request.get_json(silent=True) or {}
        
        # Определяем, есть ли реальные поля конфигурации (исключая служебные: upload_mode, files_to_upload)
        config_keys = [k for k in config_data.keys() if k.startswith(('NFS_', 'S3_', 'BACKUP_', 'MAX_', 'STORAGE_', 'ENABLE_', 'UPLOAD_', 'RETRY_', 'FILE_', 'EXT_'))]
        
        # Обновляем конфигурацию только если есть реальные поля (не только STORAGE_CLASS из интерфейса)
        if config_data and config_keys:
            try:
                app.logger.info(f"Updating user config from request for user_id={current_user.id}: {config_keys}")
                update_config(config_data, user_id=current_user.id)
                # Обновляем текущую конфигурацию после сохранения
                current_config = get_config(user_id=current_user.id)
                has_access_key = bool(current_config.get('S3_ACCESS_KEY', '').strip())
                has_secret_key = bool(current_config.get('S3_SECRET_KEY', '').strip())
                app.logger.info(
                    f"Config updated for user_id={current_user.id}: "
                    f"S3_ENDPOINT={current_config.get('S3_ENDPOINT', 'NOT SET')[:50]}, "
                    f"S3_ACCESS_KEY present={has_access_key}, "
                    f"S3_SECRET_KEY present={has_secret_key}"
                )
            except Exception as e:
                app.logger.error(f"Error updating config for user_id={current_user.id}: {e}", exc_info=True)
                return jsonify({'status': 'error', 'message': f'Invalid configuration: {e}'}), 400
        
        # Проверяем наличие обязательных полей для S3 в конфигурации пользователя
        # Проверяем не только наличие ключа, но и что значение не пустое
        s3_required = ['S3_ACCESS_KEY', 'S3_SECRET_KEY']
        missing_s3_fields = [
            field for field in s3_required 
            if not current_config.get(field) or not str(current_config.get(field, '')).strip()
        ]
        
        if missing_s3_fields:
            app.logger.error(
                f"Missing S3 credentials for user_id={current_user.id}: {missing_s3_fields}. "
                f"S3_ACCESS_KEY value length: {len(str(current_config.get('S3_ACCESS_KEY', '')))}, "
                f"S3_SECRET_KEY value length: {len(str(current_config.get('S3_SECRET_KEY', '')))}"
            )
            return jsonify({
                'status': 'error', 
                'message': f'Missing S3 credentials: {", ".join(missing_s3_fields)}. Please update your configuration in the Configuration page.'
            }), 400
        
        # Сохраняем user_id в статистику
        upload_stats.user_id = current_user.id
        
        # Сброс события остановки
        stop_event.clear()
        
        # Определяем режим загрузки и файлы
        upload_mode = config_data.get('upload_mode', 'auto')
        files_to_upload = config_data.get('files_to_upload', None)
        storage_class = config_data.get('STORAGE_CLASS', None)
        
        # Если storage_class не передан, используем из конфигурации пользователя
        if not storage_class:
            storage_class = current_config.get('STORAGE_CLASS', 'STANDARD')
        
        app.logger.info(f"Starting upload with storage_class: {storage_class} for user_id={current_user.id}")
        
        # Если указаны конкретные файлы, используем режим manual
        if files_to_upload and isinstance(files_to_upload, list) and len(files_to_upload) > 0:
            upload_mode = 'manual'
            # Преобразуем список файлов в формат для загрузки
            # Формат: [{path, full_path, tag, size}]
            from app.services.file_scanner import scan_specific_files
            from app.services.s3_client import get_existing_s3_files
            
            file_paths = [f.get('path') if isinstance(f, dict) else f for f in files_to_upload]
            existing_files = get_existing_s3_files(user_id=current_user.id)
            files_to_upload = scan_specific_files(
                file_paths=file_paths,
                existing_s3_files=existing_files,
                user_id=current_user.id
            )
            
            if not files_to_upload:
                return jsonify({
                    'status': 'error',
                    'message': 'No valid files found to upload. All files may already exist in S3.'
                }), 400
        
        # Запуск загрузки в отдельном потоке
        upload_thread = threading.Thread(
            target=run_upload, 
            args=(current_user.id, files_to_upload, upload_mode, storage_class), 
            daemon=True
        )
        upload_thread.start()
        
        return jsonify({'status': 'success', 'message': 'Upload started'}), 200
    
    def _handle_stop_upload(app: Flask) -> Tuple[Dict[str, Any], int]:
        """Обработка остановки загрузки"""
        from app.web.background_tasks import stop_event
        from app.services.s3_client import clear_minio_client_cache
        
        if not upload_stats.is_running:
            return jsonify({'status': 'error', 'message': 'No upload in progress'}), 409
        
        data = request.get_json(silent=True) or {}
        mode = data.get('mode', 'graceful')
        finish_current = mode != 'force'
        
        app.logger.info(f"Upload stop requested (mode: {mode})")
        
        if not finish_current:
            # Force stop - немедленно прерываем загрузку
            upload_control.request_stop(finish_current=False)
            
            # Немедленно помечаем все оставшиеся файлы как отмененные
            remaining = upload_stats.total_files - (upload_stats.successful + upload_stats.failed)
            if remaining > 0:
                upload_stats.failed += remaining
                app.logger.info(f"Force stop: marked {remaining} pending files as cancelled")
            
            # Обновляем статистику немедленно
            upload_stats.is_running = False
            
            # Закрываем активные соединения S3 для прерывания сетевых операций
            try:
                user_id = getattr(upload_stats, 'user_id', None)
                clear_minio_client_cache(user_id=user_id)
                app.logger.info(f"Force stop: cleared S3 client cache for user_id={user_id}")
            except Exception as e:
                app.logger.warning(f"Error clearing S3 client cache: {e}")
            
            stop_event.set()
            
            message = 'Загрузка прервана немедленно. Все активные операции остановлены.'
        else:
            # Graceful stop - даем завершить текущие загрузки
            upload_control.request_stop(finish_current=True)
            stop_event.set()
            message = 'Остановка загрузки запрошена. Текущие операции будут завершены.'
        
        return jsonify({'status': 'success', 'message': message}), 200
    
    def _handle_test_connection(app: Flask) -> Tuple[Dict[str, Any], int]:
        """Обработка тестирования соединения"""
        try:
            # Получаем персональную конфигурацию пользователя из БД
            current_config = get_config(user_id=current_user.id)
            
            # Обновляем конфигурацию из запроса, если она передана
            config_data = request.get_json(silent=True) or {}
            if config_data and any(key.startswith(('NFS_', 'S3_', 'BACKUP_', 'MAX_', 'STORAGE_', 'ENABLE_', 'UPLOAD_', 'RETRY_', 'FILE_', 'EXT_')) for key in config_data.keys()):
                update_config(config_data, user_id=current_user.id)
                # Обновляем текущую конфигурацию после сохранения
                current_config = get_config(user_id=current_user.id)
            
            # Проверяем наличие обязательных полей для S3 в конфигурации пользователя
            s3_required = ['S3_ACCESS_KEY', 'S3_SECRET_KEY']
            missing_s3_fields = [field for field in s3_required if not current_config.get(field)]
            
            if missing_s3_fields:
                return jsonify({
                    'status': 'error', 
                    'message': f'Missing S3 credentials: {", ".join(missing_s3_fields)}. Please update your configuration.'
                }), 400
                
            if test_connection(user_id=current_user.id):
                return jsonify({'status': 'success', 'message': 'Connection test successful'}), 200
            else:
                return jsonify({'status': 'error', 'message': 'Connection test failed'}), 500
        except Exception as e:
            app.logger.error(f"Connection test error: {e}", exc_info=True)
            return jsonify({'status': 'error', 'message': f'Connection test failed: {e}'}), 500
    
    def _handle_scan_files(app: Flask) -> Tuple[Dict[str, Any], int]:
        """Обработка сканирования файлов"""
        try:
            # Получаем персональную конфигурацию пользователя из БД
            # (scan_files_with_config использует конфигурацию пользователя через user_id)
            
            # Обновляем конфигурацию из запроса, если она передана
            config_data = request.get_json(silent=True) or {}
            if config_data and any(key.startswith(('NFS_', 'S3_', 'BACKUP_', 'MAX_', 'STORAGE_', 'ENABLE_', 'UPLOAD_', 'RETRY_', 'FILE_', 'EXT_')) for key in config_data.keys()):
                update_config(config_data, user_id=current_user.id)
                
            files = scan_files_with_config(user_id=current_user.id)
            
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

