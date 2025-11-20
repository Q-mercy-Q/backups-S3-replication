from flask import jsonify, request, render_template
import time
import humanize
import os

from app.utils.config import get_config, update_config, upload_stats
from app.services.file_scanner import scan_backup_files
from app.services.s3_client import test_connection, get_existing_s3_files
from app.services.upload_manager import upload_files
from app.services.scheduler_service import scheduler_service
from app.web.background_tasks import run_upload, scan_files_with_config, get_stats_data, get_detailed_stats

def init_routes(app):
    """Инициализация маршрутов"""
    
    @app.route('/')
    def index():
        """Главная страница"""
        return render_template('index.html', config=get_config())
    
    @app.route('/scheduler')
    def scheduler():
        """Страница планировщика"""
        return render_template('scheduler.html', config=get_config())
    
    # API для конфигурации
    @app.route('/api/config', methods=['GET', 'POST'])
    def api_config():
        """API для работы с конфигурацией"""
        if request.method == 'POST':
            try:
                config_data = request.get_json()
                if not config_data:
                    return jsonify({'status': 'error', 'message': 'No JSON data provided'})
                
                # Валидация обязательных полей
                required_fields = ['NFS_PATH', 'S3_ENDPOINT', 'S3_BUCKET']
                missing_fields = []
                for field in required_fields:
                    if field not in config_data or not config_data[field]:
                        missing_fields.append(field)
                
                if missing_fields:
                    return jsonify({
                        'status': 'error', 
                        'message': f'Missing required fields: {", ".join(missing_fields)}'
                    })
                
                # Проверяем существование NFS пути
                nfs_path = config_data['NFS_PATH']
                if not os.path.exists(nfs_path):
                    return jsonify({
                        'status': 'error', 
                        'message': f'NFS path does not exist: {nfs_path}'
                    })
                
                # Обновляем конфигурацию
                update_config(config_data)
                app.logger.info("Configuration updated successfully")
                
                # Возвращаем обновленную конфигурацию
                return jsonify({
                    'status': 'success', 
                    'message': 'Configuration updated successfully',
                    'config': get_config()
                })
                
            except Exception as e:
                app.logger.error(f"Error updating configuration: {e}")
                return jsonify({'status': 'error', 'message': f'Error updating configuration: {e}'})
        else:
            return jsonify(get_config())
    
    # API для загрузки файлов
    @app.route('/api/start_upload', methods=['POST'])
    def api_start_upload():
        """API для запуска загрузки"""
        from app.web.background_tasks import upload_thread, stop_event
        
        # Используем атрибуты объекта
        if upload_stats.is_running:
            return jsonify({'status': 'error', 'message': 'Upload already in progress'})
        
        # Обновляем конфигурацию из запроса
        config_data = request.get_json() or {}
        if config_data:
            try:
                update_config(config_data)
            except Exception as e:
                return jsonify({'status': 'error', 'message': f'Invalid configuration: {e}'})
        
        # Проверяем наличие обязательных полей для S3
        current_config = get_config()
        s3_required = ['S3_ACCESS_KEY', 'S3_SECRET_KEY']
        missing_s3_fields = [field for field in s3_required if not current_config.get(field)]
        
        if missing_s3_fields:
            return jsonify({
                'status': 'error', 
                'message': f'Missing S3 credentials: {", ".join(missing_s3_fields)}. Please update configuration.'
            })
        
        # Сброс события остановки
        stop_event.clear()
        
        # Запуск загрузки в отдельном потоке
        import threading
        upload_thread = threading.Thread(target=run_upload, daemon=True)
        upload_thread.start()
        
        return jsonify({'status': 'success', 'message': 'Upload started'})
    
    @app.route('/api/stop_upload', methods=['POST'])
    def api_stop_upload():
        """API для остановки загрузки"""
        from app.web.background_tasks import stop_event
        
        # Используем атрибуты объекта
        if not upload_stats.is_running:
            return jsonify({'status': 'error', 'message': 'No upload in progress'})
        
        # Устанавливаем флаг остановки
        upload_stats.is_running = False
        stop_event.set()
        
        app.logger.info("Upload stop requested - stopping all operations")
        
        return jsonify({'status': 'success', 'message': 'Upload stop requested. Current operations will complete.'})
    
    # API для тестирования соединения
    @app.route('/api/test_connection', methods=['POST'])
    def api_test_connection():
        """API для тестирования соединения"""
        try:
            # Обновляем конфигурацию из запроса если есть
            config_data = request.get_json() or {}
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
                })
                
            if test_connection():
                return jsonify({'status': 'success', 'message': 'Connection test successful'})
            else:
                return jsonify({'status': 'error', 'message': 'Connection test failed'})
        except Exception as e:
            return jsonify({'status': 'error', 'message': f'Connection test failed: {e}'})
    
    # API для сканирования файлов
    @app.route('/api/scan_files', methods=['POST'])
    def api_scan_files():
        """API для сканирования файлов"""
        try:
            # Обновляем конфигурацию из запроса
            config_data = request.get_json() or {}
            if config_data:
                update_config(config_data)
                
            files = scan_files_with_config()
            
            # Исправлено: проверяем, что files не None
            if files is not None and len(files) > 0:
                # Используем атрибуты объекта
                return jsonify({
                    'status': 'success', 
                    'message': f'Found {len(files)} files for upload',
                    'files_count': len(files),
                    'skipped_existing': upload_stats.skipped_existing,
                    'skipped_time': upload_stats.skipped_time,
                    'total_size': humanize.naturalsize(upload_stats.total_bytes)
                })
            else:
                # Используем атрибуты объекта
                return jsonify({
                    'status': 'warning', 
                    'message': 'No files found for upload',
                    'skipped_existing': upload_stats.skipped_existing,
                    'skipped_time': upload_stats.skipped_time
                })
        except Exception as e:
            return jsonify({'status': 'error', 'message': f'File scan error: {e}'})
    
    # API для статистики
    @app.route('/api/statistics')
    def api_statistics():
        """API для получения статистики"""
        return jsonify(get_stats_data())
    
    # API для планировщика
    @app.route('/api/scheduler/schedules', methods=['GET', 'POST'])
    def api_scheduler_schedules():
        """API для работы с расписаниями"""
        if request.method == 'GET':
            schedules = scheduler_service.schedules
            # Добавляем статистику для каждого расписания
            for schedule_id in schedules:
                stats = scheduler_service.get_schedule_stats(schedule_id)
                schedules[schedule_id]['stats'] = stats
            return jsonify(schedules)
        else:  # POST
            try:
                data = request.get_json()
                if not data:
                    return jsonify({'status': 'error', 'message': 'No data provided'})
                
                schedule_id = data.get('id', f"schedule_{int(time.time())}")
                
                # Для interval расписаний конвертируем в минуты
                if data.get('type') == 'interval':
                    # Предполагаем, что данные приходят в формате {value: число, unit: строка}
                    if isinstance(data.get('interval'), dict):
                        value = data['interval'].get('value', 1)
                        unit = data['interval'].get('unit', 'hours')
                        # Конвертируем в минуты
                        if unit == 'minutes':
                            interval_minutes = value
                        elif unit == 'hours':
                            interval_minutes = value * 60
                        elif unit == 'days':
                            interval_minutes = value * 24 * 60
                        elif unit == 'weeks':
                            interval_minutes = value * 7 * 24 * 60
                        else:
                            interval_minutes = value
                        data['interval'] = str(interval_minutes)
                    # Если interval уже строка, оставляем как есть
                    elif isinstance(data.get('interval'), str):
                        # Убедимся, что это число
                        try:
                            int(data['interval'])
                        except ValueError:
                            return jsonify({'status': 'error', 'message': 'Invalid interval format'})
                
                success = scheduler_service.add_schedule(
                    schedule_id=schedule_id,
                    name=data['name'],
                    schedule_type=data['type'],
                    interval=data['interval'],
                    enabled=data.get('enabled', True)
                )
                
                if success:
                    return jsonify({'status': 'success', 'message': 'Schedule added'})
                else:
                    return jsonify({'status': 'error', 'message': 'Failed to add schedule'})
                    
            except Exception as e:
                return jsonify({'status': 'error', 'message': str(e)})
    
    @app.route('/api/scheduler/schedules/<schedule_id>', methods=['PUT', 'DELETE'])
    def api_scheduler_schedule(schedule_id):
        """API для обновления/удаления расписания"""
        if request.method == 'PUT':
            try:
                data = request.get_json()
                if not data:
                    return jsonify({'status': 'error', 'message': 'No data provided'})
                    
                success = scheduler_service.update_schedule(schedule_id, **data)
                if success:
                    return jsonify({'status': 'success', 'message': 'Schedule updated'})
                else:
                    return jsonify({'status': 'error', 'message': 'Schedule not found'})
            except Exception as e:
                return jsonify({'status': 'error', 'message': str(e)})
        else:  # DELETE
            success = scheduler_service.delete_schedule(schedule_id)
            if success:
                return jsonify({'status': 'success', 'message': 'Schedule deleted'})
            else:
                return jsonify({'status': 'error', 'message': 'Schedule not found'})
    
    @app.route('/api/scheduler/history')
    def api_scheduler_history():
        """API для получения истории синхронизаций с фильтрами"""
        try:
            limit = int(request.args.get('limit', 50))
            schedule_filter = request.args.get('schedule', None)
            period = request.args.get('period', 'all')
            
            history = scheduler_service.get_sync_history(limit, schedule_filter, period)
            return jsonify(history)
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)})
    
    @app.route('/api/scheduler/run/<schedule_id>', methods=['POST'])
    def api_scheduler_run(schedule_id):
        """API для ручного запуска расписания"""
        try:
            if schedule_id in scheduler_service.schedules:
                schedule = scheduler_service.schedules[schedule_id]
                # Запускаем в отдельном потоке
                import threading
                thread = threading.Thread(
                    target=scheduler_service.run_scheduled_sync,
                    args=(schedule,),
                    daemon=True
                )
                thread.start()
                return jsonify({'status': 'success', 'message': 'Schedule started manually'})
            else:
                return jsonify({'status': 'error', 'message': 'Schedule not found'})
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)})
    
    @app.route('/api/scheduler/stats')
    def api_scheduler_stats():
        """API для получения общей статистики планировщика"""
        try:
            total_schedules = len(scheduler_service.schedules)
            enabled_schedules = len([s for s in scheduler_service.schedules.values() if s.get('enabled', True)])
            
            total_runs = len(scheduler_service.sync_history)
            successful_runs = len([h for h in scheduler_service.sync_history if h['status'] == 'completed'])
            failed_runs = len([h for h in scheduler_service.sync_history if h['status'] == 'failed'])
            
            total_files = sum(h.get('files_uploaded', 0) for h in scheduler_service.sync_history)
            total_data = sum(h.get('uploaded_size', 0) for h in scheduler_service.sync_history)
            
            stats = {
                'total_schedules': total_schedules,
                'enabled_schedules': enabled_schedules,
                'disabled_schedules': total_schedules - enabled_schedules,
                'total_runs': total_runs,
                'successful_runs': successful_runs,
                'failed_runs': failed_runs,
                'success_rate': (successful_runs / total_runs * 100) if total_runs > 0 else 0,
                'total_files_uploaded': total_files,
                'total_data_uploaded': humanize.naturalsize(total_data),
                'last_sync': scheduler_service.sync_history[-1] if scheduler_service.sync_history else None
            }
            
            return jsonify(stats)
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)})
    
    # API для отладочных логов
    @app.route('/api/scheduler/debug_logs', methods=['GET', 'DELETE'])
    def api_scheduler_debug_logs():
        """API для работы с отладочными логами"""
        if request.method == 'DELETE':
            success = scheduler_service.clear_debug_logs()
            if success:
                return jsonify({'status': 'success', 'message': 'Debug logs cleared'})
            else:
                return jsonify({'status': 'error', 'message': 'Failed to clear debug logs'})
        else:
            # GET
            level = request.args.get('level', 'INFO')
            limit = int(request.args.get('limit', 100))
            logs = scheduler_service.get_debug_logs(level, limit)
            return jsonify({'status': 'success', 'logs': logs})