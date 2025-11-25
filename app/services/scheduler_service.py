import time
import humanize
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from app.models.stats import UploadStats  
from app.models.schedule import Schedule
from app.models.sync_history import SyncHistory
from app.utils.config import validate_environment, upload_stats, get_config
from app.services.file_scanner import scan_backup_files
from app.services.s3_client import test_connection, get_existing_s3_files
from app.services.upload_manager import upload_files
from app.services.job_scheduler import JobScheduler
from app.utils.debug_logger import DebugLogger
from app.utils.schedule_storage import ScheduleStorage

class SchedulerService:
    """Основной сервис управления расписаниями"""
    
    def __init__(self, schedule_file: str = 'data/schedules.json'):
        self.job_scheduler = JobScheduler()
        self.storage = ScheduleStorage(schedule_file)
        self.debug_logger = DebugLogger()
        
        self.schedules: Dict[str, Schedule] = {}
        self.sync_history: List[SyncHistory] = []
        self.max_history_entries = 100
        
        # Добавляем ссылку на socketio для отправки обновлений
        self.socketio = None
        self._stop_stats_monitor = False
        
        self.load_schedules()
    
    def set_socketio(self, socketio):
        """Устанавливает socketio для отправки обновлений"""
        self.socketio = socketio
    
    def load_schedules(self):
        """Загрузка расписаний"""
        self.schedules, self.sync_history = self.storage.load_schedules()
        self.debug_logger.info(f"Loaded {len(self.schedules)} schedules and {len(self.sync_history)} history entries")
    
    def save_schedules(self):
        """Сохранение расписаний"""
        self.storage.save_schedules(self.schedules, self.sync_history, self.max_history_entries)
    
    def add_schedule(self, schedule_id: str, name: str, schedule_type: str, interval: str, enabled: bool = True) -> bool:
        """Добавление нового расписания"""
        try:
            # Валидация интервала
            if schedule_type == 'interval':
                try:
                    interval_minutes = int(interval)
                    if interval_minutes <= 0:
                        raise ValueError("Interval must be positive")
                except (ValueError, TypeError):
                    self.debug_logger.error(f"Invalid interval value: {interval}")
                    return False

            schedule = Schedule(
                id=schedule_id,
                name=name,
                schedule_type=schedule_type,
                interval=interval,
                enabled=enabled
            )
            
            # Валидация расписания
            schedule.validate()
            
            self.schedules[schedule_id] = schedule
            
            if enabled:
                self.job_scheduler.schedule_job(schedule, self.run_scheduled_sync, (schedule,))
            
            self.save_schedules()
            self.debug_logger.info(f"Added schedule: {name} ({schedule_type}: {interval})")
            return True
            
        except Exception as e:
            self.debug_logger.error(f"Error adding schedule: {e}")
            return False

    def update_schedule(self, schedule_id: str, **kwargs) -> bool:
        """Обновление расписания"""
        if schedule_id not in self.schedules:
            return False
            
        try:
            old_enabled = self.schedules[schedule_id].enabled
            
            # Обновляем атрибуты
            for key, value in kwargs.items():
                if hasattr(self.schedules[schedule_id], key):
                    setattr(self.schedules[schedule_id], key, value)
            
            # Валидация обновленного расписания
            self.schedules[schedule_id].validate()
            
            new_enabled = self.schedules[schedule_id].enabled
            
            # Перезапускаем задание если оно включено
            if new_enabled:
                self.job_scheduler.unschedule_job(schedule_id)
                self.job_scheduler.schedule_job(self.schedules[schedule_id], self.run_scheduled_sync, (self.schedules[schedule_id],))
            else:
                self.job_scheduler.unschedule_job(schedule_id)
                
            self.save_schedules()
            self.debug_logger.info(f"Updated schedule: {schedule_id}")
            return True
            
        except Exception as e:
            self.debug_logger.error(f"Error updating schedule: {e}")
            return False

    def delete_schedule(self, schedule_id: str) -> bool:
        """Удаление расписания"""
        if schedule_id in self.schedules:
            schedule_name = self.schedules[schedule_id].name
            self.job_scheduler.unschedule_job(schedule_id)
            del self.schedules[schedule_id]
            self.save_schedules()
            self.debug_logger.info(f"Deleted schedule: {schedule_name}")
            return True
        return False

    def run_scheduled_sync(self, schedule: Schedule):
        """Запуск запланированной синхронизации"""
        self.debug_logger.info(f"=== 🚀 STARTING SCHEDULED SYNC: {schedule.name} ({schedule.id}) ===")
        self.debug_logger.info(f"📅 Schedule details: type={schedule.schedule_type.value}, interval={schedule.interval}, enabled={schedule.enabled}")
        
        # Создаем запись в истории
        history_entry = SyncHistory(
            id=f"{schedule.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            schedule_id=schedule.id,
            schedule_name=schedule.name,
            start_time=datetime.now().isoformat(),
            status='running'
        )
        
        self.sync_history.append(history_entry)
        self.save_schedules()
        self.debug_logger.info("✅ History entry created and saved")
        
        # Сохраняем оригинальное состояние статистики ДО try блока
        original_stats = None
        
        try:
            # Сохраняем текущее состояние статистики
            original_stats = UploadStats(
                total_files=upload_stats.total_files,
                successful=upload_stats.successful,
                failed=upload_stats.failed,
                total_bytes=upload_stats.total_bytes,
                uploaded_bytes=upload_stats.uploaded_bytes,
                start_time=upload_stats.start_time,
                file_start_times=upload_stats.file_start_times.copy() if upload_stats.file_start_times else {},
                is_running=upload_stats.is_running,
                skipped_existing=upload_stats.skipped_existing,
                skipped_time=upload_stats.skipped_time
            )
            
            # Шаг 1: Инициализация статистики
            self._init_upload_stats()
            self.debug_logger.info(" Upload stats initialized")
            
            # Отправляем начальное обновление статистики
            self._send_stats_update()
            
            # Шаг 2: Валидация окружения
            self.debug_logger.info("🔧 Validating environment...")
            self._validate_environment()
            self.debug_logger.info(" Environment validation passed")
            
            # Шаг 3: Получение существующих файлов S3
            self.debug_logger.info(" Getting existing S3 files...")
            existing_files = get_existing_s3_files()
            self.debug_logger.info(f" Found {len(existing_files)} existing files in S3")
            
            # Шаг 4: Сканирование файлов бэкапа
            self.debug_logger.info(" Scanning backup files...")
            files_to_upload = scan_backup_files(existing_files)
            self.debug_logger.info(f" Scan completed: {len(files_to_upload)} files to upload")
            
            # Обновляем статистику после сканирования
            self._send_stats_update()
            
            if files_to_upload:
                total_size = sum(f[3] for f in files_to_upload)
                self.debug_logger.info(f" Starting upload of {len(files_to_upload)} files, total size: {humanize.naturalsize(total_size)}")
                
                # Запускаем мониторинг статистики для этой задачи
                stats_monitor_thread = self._start_stats_monitor()
                
                # Шаг 5: ЗАПУСК ЗАГРУЗКИ
                self.debug_logger.info(" CALLING upload_files()...")
                successful, failed = upload_files(files_to_upload)
                self.debug_logger.info(f" upload_files() returned: {successful} successful, {failed} failed")
                
                # ЖДЕМ ЗАВЕРШЕНИЯ ВСЕХ ПОТОКОВ ЗАГРУЗКИ
                self.debug_logger.info(" Waiting for all upload threads to complete...")
                max_wait_time = 3600  # 1 час максимум
                wait_interval = 5     # проверяем каждые 5 секунд
                waited = 0
                
                while upload_stats.is_running and waited < max_wait_time:
                    time.sleep(wait_interval)
                    waited += wait_interval
                    if waited % 30 == 0:  # Логируем каждые 30 секунд
                        self.debug_logger.info(f"⏱ Waiting for upload to complete... {waited}s elapsed")
                
                if upload_stats.is_running:
                    self.debug_logger.warning(" Upload timeout reached, forcing stop")
                    upload_stats.is_running = False
                
                # Останавливаем мониторинг статистики
                self._stop_stats_monitor = True
                if stats_monitor_thread and stats_monitor_thread.is_alive():
                    stats_monitor_thread.join(timeout=5)
                
                # Обновляем историю с актуальной статистикой
                history_entry.mark_completed(
                    files_uploaded=upload_stats.successful,
                    files_failed=upload_stats.failed,
                    total_size=upload_stats.total_bytes,
                    uploaded_size=upload_stats.uploaded_bytes,
                    duration=time.time() - upload_stats.start_time
                )
                
                self.debug_logger.info(f" Scheduled sync completed: {upload_stats.successful} successful, {upload_stats.failed} failed, duration: {history_entry.duration:.2f}s")
                
            else:
                history_entry.mark_completed(
                    files_uploaded=0,
                    files_failed=0,
                    total_size=0,
                    uploaded_size=0,
                    duration=time.time() - upload_stats.start_time
                )
                self.debug_logger.info(" Scheduled sync: No files to upload")
            
            # Обновляем расписание
            schedule.last_run = datetime.now().isoformat()
            next_run = self.job_scheduler.get_next_run_time(schedule.id)
            schedule.next_run = next_run.isoformat() if next_run else None
            self.save_schedules()
            self.debug_logger.info(" Schedule updated with last_run and next_run")
            
        except Exception as e:
            self.debug_logger.error(f" Scheduled sync error: {e}")
            import traceback
            self.debug_logger.error(f" Stack trace: {traceback.format_exc()}")
            
            if history_entry:
                history_entry.mark_failed(
                    error=str(e),
                    duration=time.time() - (upload_stats.start_time if hasattr(upload_stats, 'start_time') else time.time())
                )
            self.save_schedules()
            
        finally:
            # Восстанавливаем оригинальное состояние статистики только если оно было сохранено
            if original_stats:
                self.debug_logger.info(" Restoring original upload stats...")
                upload_stats.total_files = original_stats.total_files
                upload_stats.successful = original_stats.successful
                upload_stats.failed = original_stats.failed
                upload_stats.total_bytes = original_stats.total_bytes
                upload_stats.uploaded_bytes = original_stats.uploaded_bytes
                upload_stats.start_time = original_stats.start_time
                upload_stats.file_start_times = original_stats.file_start_times
                upload_stats.is_running = original_stats.is_running
                upload_stats.skipped_existing = original_stats.skipped_existing
                upload_stats.skipped_time = original_stats.skipped_time
                self.debug_logger.info(" Original upload stats restored")
            
            # Отправляем финальное обновление статистики
            self._send_stats_update()
            
            self.debug_logger.info(f"===  SCHEDULED SYNC FINISHED: {schedule.name} ===\n")

    def _init_upload_stats(self):
        """Инициализация статистики загрузки"""
        upload_stats.total_files = 0
        upload_stats.successful = 0
        upload_stats.failed = 0
        upload_stats.total_bytes = 0
        upload_stats.uploaded_bytes = 0
        upload_stats.start_time = time.time()
        upload_stats.file_start_times = {}
        upload_stats.is_running = True
        upload_stats.skipped_existing = 0
        upload_stats.skipped_time = 0

    def _validate_environment(self):
        """Валидация окружения"""
        validate_environment()
        
        if not test_connection():
            raise Exception("S3 connection test failed")

    def _start_stats_monitor(self):
        """Запуск мониторинга статистики для запланированной задачи"""
        self._stop_stats_monitor = False
        
        def stats_monitor():
            while not self._stop_stats_monitor and upload_stats.is_running:
                try:
                    self._send_stats_update()
                    time.sleep(2)  # Отправляем каждые 2 секунды
                except Exception as e:
                    self.debug_logger.error(f"Error in stats monitor: {e}")
                    time.sleep(5)
        
        import threading
        thread = threading.Thread(target=stats_monitor, daemon=True)
        thread.start()
        return thread

    def _send_stats_update(self):
        """Отправка обновления статистики через Socket.IO"""
        try:
            if self.socketio:
                from app.web.background_tasks import get_stats_data
                stats_data = get_stats_data()
                self.socketio.emit('stats_update', stats_data)
                self.debug_logger.debug(" Stats update sent to web interface")
        except Exception as e:
            self.debug_logger.error(f"Error sending stats update: {e}")

    def get_sync_history(self, limit: int = 50, schedule_id: Optional[str] = None, period: str = 'all') -> List[SyncHistory]:
        """Получение истории синхронизаций с фильтрами"""
        filtered_history = self.sync_history.copy()
        
        # Фильтр по расписанию
        if schedule_id and schedule_id != 'all':
            filtered_history = [h for h in filtered_history if h.schedule_id == schedule_id]
        
        # Фильтр по периоду времени
        if period != 'all':
            now = datetime.now()
            if period == 'today':
                start_date = datetime(now.year, now.month, now.day)
                filtered_history = [h for h in filtered_history if datetime.fromisoformat(h.start_time.replace('Z', '+00:00')) >= start_date]
            elif period == 'week':
                start_date = now - timedelta(days=now.weekday())
                start_date = datetime(start_date.year, start_date.month, start_date.day)
                filtered_history = [h for h in filtered_history if datetime.fromisoformat(h.start_time.replace('Z', '+00:00')) >= start_date]
            elif period == 'month':
                start_date = datetime(now.year, now.month, 1)
                filtered_history = [h for h in filtered_history if datetime.fromisoformat(h.start_time.replace('Z', '+00:00')) >= start_date]
        
        # Сортируем по времени и ограничиваем количество
        filtered_history.sort(key=lambda x: x.start_time)
        return filtered_history[-limit:]

    def get_schedule_stats(self, schedule_id: str) -> dict:
        """Получение статистики для расписания"""
        schedule_history = [h for h in self.sync_history if h.schedule_id == schedule_id]
        
        if not schedule_history:
            return {}
            
        successful_runs = [h for h in schedule_history if h.status.value == 'completed']
        failed_runs = [h for h in schedule_history if h.status.value == 'failed']
        
        total_files = sum(h.files_uploaded for h in successful_runs if hasattr(h, 'files_uploaded'))
        total_data = sum(h.uploaded_size for h in successful_runs if hasattr(h, 'uploaded_size'))
        total_duration = sum(h.duration for h in successful_runs if hasattr(h, 'duration'))
        
        avg_duration = total_duration / len(successful_runs) if successful_runs else 0
        
        last_run = schedule_history[-1] if schedule_history else None
        
        return {
            'total_runs': len(schedule_history),
            'successful_runs': len(successful_runs),
            'failed_runs': len(failed_runs),
            'success_rate': (len(successful_runs) / len(schedule_history) * 100) if schedule_history else 0,
            'total_files_uploaded': total_files,
            'total_data_uploaded': humanize.naturalsize(total_data) if total_data > 0 else "0 B",
            'total_data_uploaded_bytes': total_data,
            'average_duration': avg_duration,
            'last_run': last_run.to_dict() if last_run else None
        }

    def get_all_schedules_stats(self) -> dict:
        """Получение статистики для всех расписаний"""
        stats = {
            'total_schedules': len(self.schedules),
            'enabled_schedules': len([s for s in self.schedules.values() if s.enabled]),
            'total_runs': len(self.sync_history),
            'successful_runs': len([h for h in self.sync_history if h.status.value == 'completed']),
            'failed_runs': len([h for h in self.sync_history if h.status.value == 'failed']),
            'total_files_uploaded': sum(h.files_uploaded for h in self.sync_history if hasattr(h, 'files_uploaded')),
            'total_data_uploaded_bytes': sum(h.uploaded_size for h in self.sync_history if hasattr(h, 'uploaded_size')),
        }
        
        # Вычисляем процент успешных запусков
        if stats['total_runs'] > 0:
            stats['success_rate'] = (stats['successful_runs'] / stats['total_runs']) * 100
        else:
            stats['success_rate'] = 0
            
        stats['total_data_uploaded'] = humanize.naturalsize(stats['total_data_uploaded_bytes'])
        
        return stats

    def start(self):
        """Запуск планировщика"""
        self.job_scheduler.start()
        
        # Восстанавливаем все включенные задания
        enabled_count = 0
        for schedule in self.schedules.values():
            if schedule.enabled:
                try:
                    self.job_scheduler.schedule_job(schedule, self.run_scheduled_sync, (schedule,))
                    enabled_count += 1
                    self.debug_logger.info(f" Restored schedule: {schedule.name}")
                except Exception as e:
                    self.debug_logger.error(f" Failed to restore schedule {schedule.name}: {e}")
        
        self.debug_logger.info(f"🚀 Scheduler started, restored {enabled_count} enabled schedules")

    def shutdown(self):
        """Остановка планировщика"""
        try:
            if hasattr(self.job_scheduler, 'scheduler') and self.job_scheduler.scheduler.running:
                self.job_scheduler.shutdown()
                self.debug_logger.info(" Scheduler service stopped")
            else:
                self.debug_logger.debug("ℹ Scheduler was not running, skip shutdown")
        except Exception as e:
            self.debug_logger.error(f" Error stopping scheduler service: {e}")

    def get_storage_info(self) -> dict:
        """Получение информации о хранилище"""
        return self.storage.get_storage_info()

    # Методы для работы с отладочными логами
    def get_debug_logs(self, level: str = 'INFO', limit: int = 100):
        """Получение отладочных логов"""
        return self.debug_logger.get_logs(level, limit)
    
    def clear_debug_logs(self) -> bool:
        """Очистка отладочных логов"""
        return self.debug_logger.clear_logs()
    
    def info(self, message: str):
        """Логирование информационного сообщения"""
        self.debug_logger.info(message)
    
    def error(self, message: str):
        """Логирование ошибки"""
        self.debug_logger.error(message)
    
    def debug(self, message: str):
        """Логирование отладочного сообщения"""
        self.debug_logger.debug(message)

    def run_schedule_immediately(self, schedule_id: str) -> bool:
        """Немедленный запуск расписания"""
        if schedule_id not in self.schedules:
            return False
            
        try:
            schedule = self.schedules[schedule_id]
            self.debug_logger.info(f" Manually running schedule: {schedule.name}")
            
            # Запускаем в отдельном потоке
            import threading
            thread = threading.Thread(target=self.run_scheduled_sync, args=(schedule,), daemon=True)
            thread.start()
            
            return True
        except Exception as e:
            self.debug_logger.error(f" Error running schedule immediately: {e}")
            return False

    def get_schedule_by_id(self, schedule_id: str) -> Optional[Schedule]:
        """Получение расписания по ID"""
        return self.schedules.get(schedule_id)

    def get_next_run_time(self, schedule_id: str) -> Optional[datetime]:
        """Получение времени следующего запуска"""
        return self.job_scheduler.get_next_run_time(schedule_id)

    def is_schedule_enabled(self, schedule_id: str) -> bool:
        """Проверка включено ли расписание"""
        schedule = self.schedules.get(schedule_id)
        return schedule.enabled if schedule else False

    def enable_schedule(self, schedule_id: str) -> bool:
        """Включение расписания"""
        return self.update_schedule(schedule_id, enabled=True)

    def disable_schedule(self, schedule_id: str) -> bool:
        """Отключение расписания"""
        return self.update_schedule(schedule_id, enabled=False)

    def validate_schedule_config(self, schedule_type: str, interval: str) -> bool:
        """Валидация конфигурации расписания"""
        try:
            if schedule_type == 'interval':
                interval_minutes = int(interval)
                if interval_minutes <= 0:
                    return False
            elif schedule_type == 'cron':
                # Базовая валидация cron выражения
                if not interval or len(interval.split()) != 5:
                    return False
            else:
                return False
            return True
        except (ValueError, TypeError):
            return False

    def get_schedule_display_info(self, schedule_id: str) -> Optional[dict]:
        """Получение информации о расписании для отображения"""
        schedule = self.schedules.get(schedule_id)
        if not schedule:
            return None
            
        stats = self.get_schedule_stats(schedule_id)
        
        return {
            'id': schedule.id,
            'name': schedule.name,
            'type': schedule.schedule_type.value,
            'interval': schedule.interval,
            'enabled': schedule.enabled,
            'created_at': schedule.created_at,
            'last_run': schedule.last_run,
            'next_run': schedule.next_run,
            'description': schedule.description,
            'interval_display': schedule.get_interval_display(),
            'stats': stats
        }

    def cleanup_old_history(self, max_age_days: int = 30) -> int:
        """Очистка старой истории"""
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        initial_count = len(self.sync_history)
        
        self.sync_history = [
            h for h in self.sync_history 
            if datetime.fromisoformat(h.start_time.replace('Z', '+00:00')) >= cutoff_date
        ]
        
        removed_count = initial_count - len(self.sync_history)
        if removed_count > 0:
            self.save_schedules()
            self.debug_logger.info(f" Cleaned up {removed_count} old history entries")
        
        return removed_count

# Глобальный экземпляр планировщика
scheduler_service = SchedulerService()