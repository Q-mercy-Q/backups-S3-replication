from flask import jsonify, request, render_template
import time
import humanize
import os
import json
import logging
from datetime import datetime, timedelta

from app.utils.config import get_config, update_config, upload_stats
from app.services.file_scanner import scan_backup_files
from app.services.s3_client import test_connection, get_existing_s3_files
from app.services.upload_manager import upload_files
from app.services.scheduler_service import scheduler_service
from app.web.background_tasks import run_upload, scan_files_with_config, get_stats_data, get_detailed_stats

# Глобальная переменная для отслеживания запуска планировщика
_scheduler_started = False

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
    
    # Остальной код routes.py остается без изменений...
    # [весь остальной код из предыдущей полной версии routes.py]
    
    # API для конфигурации
    @app.route('/api/config', methods=['GET', 'POST'])
    def api_config():
        """API для работы с конфигурацией"""
        if request.method == 'POST':
            try:
                config_data = request.get_json()
                app.logger.info(f"Received config update: {list(config_data.keys()) if config_data else 'No data'}")
                
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
                
                # Возвращаем обновленную конфигурацию (всегда из get_config())
                return jsonify({
                    'status': 'success', 
                    'message': 'Configuration updated successfully',
                    'config': get_config()
                })
                
            except Exception as e:
                app.logger.error(f"Error updating configuration: {e}")
                return jsonify({'status': 'error', 'message': f'Error updating configuration: {e}'})
        else:
            # GET request - возвращаем текущую конфигурацию через get_config()
            return jsonify(get_config())
    
    # API для загрузки файлов
    @app.route('/api/start_upload', methods=['POST'])
    def api_start_upload():
        """API для запуска загрузки"""
        from app.web.background_tasks import upload_thread, stop_event
        
        if upload_stats.is_running:
            return jsonify({'status': 'error', 'message': 'Upload already in progress'})
        
        # Обновляем конфигурацию из запроса
        config_data = request.get_json() or {}
        if config_data:
            try:
                update_config(config_data)
            except Exception as e:
                return jsonify({'status': 'error', 'message': f'Invalid configuration: {e}'})
        
        # Проверяем наличие обязательных полей для S3 через get_config()
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
            
            # Проверяем наличие обязательных полей для S3 через get_config()
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
            
            if files is not None and len(files) > 0:
                return jsonify({
                    'status': 'success', 
                    'message': f'Found {len(files)} files for upload',
                    'files_count': len(files),
                    'skipped_existing': upload_stats.skipped_existing,
                    'skipped_time': upload_stats.skipped_time,
                    'total_size': humanize.naturalsize(upload_stats.total_bytes)
                })
            else:
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
    
    # API для планировщика - Статистика планировщика
    @app.route('/api/scheduler/stats')
    def api_scheduler_stats():
        """API для получения статистики планировщика"""
        try:
            stats = {
                'total_schedules': len(scheduler_service.schedules),
                'enabled_schedules': len([s for s in scheduler_service.schedules.values() if s.enabled]),
                'total_runs': len(scheduler_service.sync_history),
                'successful_runs': len([h for h in scheduler_service.sync_history if h.status.value == 'completed']),
                'failed_runs': len([h for h in scheduler_service.sync_history if h.status.value == 'failed']),
                'total_files_uploaded': sum(h.files_uploaded for h in scheduler_service.sync_history if hasattr(h, 'files_uploaded')),
                'total_data_uploaded': humanize.naturalsize(sum(h.uploaded_size for h in scheduler_service.sync_history if hasattr(h, 'uploaded_size'))),
            }
            
            # Вычисляем процент успешных запусков
            if stats['total_runs'] > 0:
                stats['success_rate'] = (stats['successful_runs'] / stats['total_runs']) * 100
            else:
                stats['success_rate'] = 0
                
            return jsonify(stats)
            
        except Exception as e:
            app.logger.error(f"Error getting scheduler stats: {e}")
            return jsonify({'status': 'error', 'message': str(e)})
    
    # API для планировщика - Расписания
    @app.route('/api/scheduler/schedules', methods=['GET', 'POST'])
    def api_scheduler_schedules():
        """API для работы с расписаниями"""
        try:
            if request.method == 'GET':
                # Возвращаем все расписания со статистикой
                schedules_with_stats = {}
                for schedule_id, schedule in scheduler_service.schedules.items():
                    schedule_dict = schedule.to_dict()
                    schedule_dict['stats'] = scheduler_service.get_schedule_stats(schedule_id)
                    schedules_with_stats[schedule_id] = schedule_dict
                    
                return jsonify(schedules_with_stats)
                
            elif request.method == 'POST':
                # Создание нового расписания
                data = request.get_json()
                if not data:
                    return jsonify({'status': 'error', 'message': 'No JSON data provided'})
                    
                required_fields = ['name', 'type', 'interval']
                for field in required_fields:
                    if field not in data:
                        return jsonify({'status': 'error', 'message': f'Missing required field: {field}'})
                
                # Генерируем ID для нового расписания
                import uuid
                schedule_id = f"schedule_{uuid.uuid4().hex[:8]}"
                
                # Добавляем расписание
                success = scheduler_service.add_schedule(
                    schedule_id=schedule_id,
                    name=data['name'],
                    schedule_type=data['type'],
                    interval=data['interval'],
                    enabled=data.get('enabled', True)
                )
                
                if success:
                    return jsonify({'status': 'success', 'message': 'Schedule added successfully'})
                else:
                    return jsonify({'status': 'error', 'message': 'Failed to add schedule'})
                    
        except Exception as e:
            app.logger.error(f"Error in scheduler schedules API: {e}")
            return jsonify({'status': 'error', 'message': str(e)})
    
    # API для планировщика - Конкретное расписание
    @app.route('/api/scheduler/schedules/<schedule_id>', methods=['PUT', 'DELETE'])
    def api_scheduler_schedule(schedule_id):
        """API для работы с конкретным расписанием"""
        try:
            if request.method == 'PUT':
                # Обновление расписания
                data = request.get_json()
                if not data:
                    return jsonify({'status': 'error', 'message': 'No JSON data provided'})
                    
                success = scheduler_service.update_schedule(schedule_id, **data)
                if success:
                    return jsonify({'status': 'success', 'message': 'Schedule updated successfully'})
                else:
                    return jsonify({'status': 'error', 'message': 'Schedule not found or update failed'})
                    
            elif request.method == 'DELETE':
                # Удаление расписания
                success = scheduler_service.delete_schedule(schedule_id)
                if success:
                    return jsonify({'status': 'success', 'message': 'Schedule deleted successfully'})
                else:
                    return jsonify({'status': 'error', 'message': 'Schedule not found'})
                    
        except Exception as e:
            app.logger.error(f"Error in scheduler schedule API: {e}")
            return jsonify({'status': 'error', 'message': str(e)})
    
    # API для планировщика - Запуск расписания вручную
    @app.route('/api/scheduler/run/<schedule_id>', methods=['POST'])
    def api_scheduler_run(schedule_id):
        """API для запуска расписания вручную"""
        try:
            if schedule_id not in scheduler_service.schedules:
                return jsonify({'status': 'error', 'message': 'Schedule not found'})
                
            # Запускаем в отдельном потоке чтобы не блокировать HTTP запрос
            import threading
            schedule = scheduler_service.schedules[schedule_id]
            
            def run_schedule_async():
                try:
                    scheduler_service.run_scheduled_sync(schedule)
                except Exception as e:
                    app.logger.error(f"Error running schedule {schedule_id}: {e}")
            
            thread = threading.Thread(target=run_schedule_async, daemon=True)
            thread.start()
            
            return jsonify({'status': 'success', 'message': 'Schedule started manually'})
            
        except Exception as e:
            app.logger.error(f"Error running schedule: {e}")
            return jsonify({'status': 'error', 'message': str(e)})
    
    # API для планировщика - История синхронизаций
    @app.route('/api/scheduler/history')
    def api_scheduler_history():
        """API для получения истории синхронизаций"""
        try:
            # Получаем параметры фильтрации
            limit = request.args.get('limit', 50, type=int)
            schedule_filter = request.args.get('schedule', 'all')
            period = request.args.get('period', 'all')
            
            # Получаем отфильтрованную историю
            history = scheduler_service.get_sync_history(
                limit=limit,
                schedule_id=schedule_filter if schedule_filter != 'all' else None,
                period=period
            )
            
            # Конвертируем в словари
            history_dicts = [h.to_dict() for h in history]
            
            return jsonify(history_dicts)
            
        except Exception as e:
            app.logger.error(f"Error getting scheduler history: {e}")
            return jsonify({'status': 'error', 'message': str(e)})
    
    # API для планировщика - Отладочные логи
    @app.route('/api/scheduler/debug_logs', methods=['GET', 'DELETE'])
    def api_scheduler_debug_logs():
        """API для работы с отладочными логами"""
        try:
            if request.method == 'GET':
                level = request.args.get('level', 'INFO')
                limit = request.args.get('limit', 100, type=int)
                
                logs = scheduler_service.get_debug_logs(level=level, limit=limit)
                return jsonify({'status': 'success', 'logs': logs})
                
            elif request.method == 'DELETE':
                success = scheduler_service.clear_debug_logs()
                if success:
                    return jsonify({'status': 'success', 'message': 'Debug logs cleared'})
                else:
                    return jsonify({'status': 'error', 'message': 'Failed to clear debug logs'})
                    
        except Exception as e:
            app.logger.error(f"Error in debug logs API: {e}")
            return jsonify({'status': 'error', 'message': str(e)})
    
    # API для проверки здоровья
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
            
            return jsonify(health_info)
            
        except Exception as e:
            app.logger.error(f"Health check failed: {e}")
            return jsonify({'status': 'error', 'message': str(e)})
    
    # Обработчик ошибок 404
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'status': 'error', 'message': 'Endpoint not found'}), 404
    
    # Обработчик ошибок 500
    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f"Internal server error: {error}")
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500
