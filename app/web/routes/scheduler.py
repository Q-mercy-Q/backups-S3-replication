"""
API маршруты для работы с планировщиком
"""

import threading
import uuid
from flask import Flask, jsonify, request
from typing import Dict, Any, Tuple
from datetime import datetime

import humanize

from app.services.scheduler_service import scheduler_service


def init_routes(app: Flask) -> None:
    """Инициализация маршрутов планировщика"""
    
    @app.route('/api/scheduler/stats')
    def api_scheduler_stats():
        """API для получения статистики планировщика"""
        return _handle_scheduler_stats()
    
    @app.route('/api/scheduler/schedules', methods=['GET', 'POST'])
    def api_scheduler_schedules():
        """API для работы с расписаниями"""
        if request.method == 'GET':
            return _handle_get_schedules()
        else:
            return _handle_create_schedule(app)
    
    @app.route('/api/scheduler/schedules/<schedule_id>', methods=['PUT', 'DELETE'])
    def api_scheduler_schedule(schedule_id: str):
        """API для работы с конкретным расписанием"""
        if request.method == 'PUT':
            return _handle_update_schedule(app, schedule_id)
        else:
            return _handle_delete_schedule(app, schedule_id)
    
    @app.route('/api/scheduler/run/<schedule_id>', methods=['POST'])
    def api_scheduler_run(schedule_id: str):
        """API для запуска расписания вручную"""
        return _handle_run_schedule(app, schedule_id)
    
    @app.route('/api/scheduler/history')
    def api_scheduler_history():
        """API для получения истории синхронизаций"""
        return _handle_get_history()
    
    @app.route('/api/scheduler/debug_logs', methods=['GET', 'DELETE'])
    def api_scheduler_debug_logs():
        """API для работы с отладочными логами"""
        if request.method == 'GET':
            return _handle_get_debug_logs()
        else:
            return _handle_clear_debug_logs(app)
    
    def _handle_scheduler_stats() -> Tuple[Dict[str, Any], int]:
        """Обработка получения статистики планировщика"""
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
                
            return jsonify(stats), 200
            
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error getting scheduler stats: {e}", exc_info=True)
            return jsonify({'status': 'error', 'message': str(e)}), 500
    
    def _handle_get_schedules() -> Tuple[Dict[str, Any], int]:
        """Обработка получения всех расписаний"""
        try:
            schedules_with_stats = {}
            for schedule_id, schedule in scheduler_service.schedules.items():
                schedule_dict = schedule.to_dict()
                schedule_dict['stats'] = scheduler_service.get_schedule_stats(schedule_id)
                schedules_with_stats[schedule_id] = schedule_dict
                
            return jsonify(schedules_with_stats), 200
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error getting schedules: {e}", exc_info=True)
            return jsonify({'status': 'error', 'message': str(e)}), 500
    
    def _handle_create_schedule(app: Flask) -> Tuple[Dict[str, Any], int]:
        """Обработка создания нового расписания"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'status': 'error', 'message': 'No JSON data provided'}), 400
                
            required_fields = ['name', 'type', 'interval']
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                return jsonify({
                    'status': 'error', 
                    'message': f'Missing required fields: {", ".join(missing_fields)}'
                }), 400
            
            # Генерируем ID для нового расписания
            schedule_id = f"schedule_{uuid.uuid4().hex[:8]}"
            
            # Добавляем расписание
            categories = data.get('categories') if isinstance(data.get('categories'), list) else None
            success = scheduler_service.add_schedule(
                schedule_id=schedule_id,
                name=data['name'],
                schedule_type=data['type'],
                interval=data['interval'],
                enabled=data.get('enabled', True),
                categories=categories
            )
            
            if success:
                return jsonify({'status': 'success', 'message': 'Schedule added successfully'}), 201
            else:
                return jsonify({'status': 'error', 'message': 'Failed to add schedule'}), 500
                
        except Exception as e:
            app.logger.error(f"Error creating schedule: {e}", exc_info=True)
            return jsonify({'status': 'error', 'message': str(e)}), 500
    
    def _handle_update_schedule(app: Flask, schedule_id: str) -> Tuple[Dict[str, Any], int]:
        """Обработка обновления расписания"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({'status': 'error', 'message': 'No JSON data provided'}), 400
                
            if 'categories' in data and not isinstance(data['categories'], list):
                data['categories'] = []

            success = scheduler_service.update_schedule(schedule_id, **data)
            if success:
                return jsonify({'status': 'success', 'message': 'Schedule updated successfully'}), 200
            else:
                return jsonify({'status': 'error', 'message': 'Schedule not found or update failed'}), 404
                
        except Exception as e:
            app.logger.error(f"Error updating schedule: {e}", exc_info=True)
            return jsonify({'status': 'error', 'message': str(e)}), 500
    
    def _handle_delete_schedule(app: Flask, schedule_id: str) -> Tuple[Dict[str, Any], int]:
        """Обработка удаления расписания"""
        try:
            success = scheduler_service.delete_schedule(schedule_id)
            if success:
                return jsonify({'status': 'success', 'message': 'Schedule deleted successfully'}), 200
            else:
                return jsonify({'status': 'error', 'message': 'Schedule not found'}), 404
                
        except Exception as e:
            app.logger.error(f"Error deleting schedule: {e}", exc_info=True)
            return jsonify({'status': 'error', 'message': str(e)}), 500
    
    def _handle_run_schedule(app: Flask, schedule_id: str) -> Tuple[Dict[str, Any], int]:
        """Обработка запуска расписания вручную"""
        try:
            if schedule_id not in scheduler_service.schedules:
                return jsonify({'status': 'error', 'message': 'Schedule not found'}), 404
                
            # Запускаем в отдельном потоке чтобы не блокировать HTTP запрос
            schedule = scheduler_service.schedules[schedule_id]
            
            def run_schedule_async():
                try:
                    scheduler_service.run_scheduled_sync(schedule)
                except Exception as e:
                    app.logger.error(f"Error running schedule {schedule_id}: {e}", exc_info=True)
            
            thread = threading.Thread(target=run_schedule_async, daemon=True)
            thread.start()
            
            return jsonify({'status': 'success', 'message': 'Schedule started manually'}), 200
            
        except Exception as e:
            app.logger.error(f"Error running schedule: {e}", exc_info=True)
            return jsonify({'status': 'error', 'message': str(e)}), 500
    
    def _handle_get_history() -> Tuple[Dict[str, Any], int]:
        """Обработка получения истории синхронизаций"""
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
            
            return jsonify(history_dicts), 200
            
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error getting scheduler history: {e}", exc_info=True)
            return jsonify({'status': 'error', 'message': str(e)}), 500
    
    def _handle_get_debug_logs() -> Tuple[Dict[str, Any], int]:
        """Обработка получения отладочных логов"""
        try:
            level = request.args.get('level', 'INFO')
            limit = request.args.get('limit', 100, type=int)
            
            logs = scheduler_service.get_debug_logs(level=level, limit=limit)
            return jsonify({'status': 'success', 'logs': logs}), 200
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error getting debug logs: {e}", exc_info=True)
            return jsonify({'status': 'error', 'message': str(e)}), 500
    
    def _handle_clear_debug_logs(app: Flask) -> Tuple[Dict[str, Any], int]:
        """Обработка очистки отладочных логов"""
        try:
            success = scheduler_service.clear_debug_logs()
            if success:
                return jsonify({'status': 'success', 'message': 'Debug logs cleared'}), 200
            else:
                return jsonify({'status': 'error', 'message': 'Failed to clear debug logs'}), 500
        except Exception as e:
            app.logger.error(f"Error clearing debug logs: {e}", exc_info=True)
            return jsonify({'status': 'error', 'message': str(e)}), 500

