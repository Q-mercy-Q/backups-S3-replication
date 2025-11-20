import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import humanize
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
        
        self.load_schedules()
    
    def load_schedules(self):
        """Загрузка расписаний"""
        self.schedules, self.sync_history = self.storage.load_schedules()
    
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
        self.debug_logger.info(f"=== Starting scheduled sync: {schedule.name} ===")
        
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
        
        try:
            # ИСПРАВЛЕНО: сохраняем состояние объекта, а не словаря
            original_stats = UploadStats(
                total_files=upload_stats.total_files,
                successful=upload_stats.successful,
                failed=upload_stats.failed,
                total_bytes=upload_stats.total_bytes,
                uploaded_bytes=upload_stats.uploaded_bytes,
                start_time=upload_stats.start_time,
                file_start_times=upload_stats.file_start_times.copy(),
                is_running=upload_stats.is_running,
                skipped_existing=upload_stats.skipped_existing,
                skipped_time=upload_stats.skipped_time
            )
            
            self._init_upload_stats()
            
            # Основная логика синхронизации
            self._validate_environment()
            existing_files = get_existing_s3_files()
            files_to_upload = scan_backup_files(existing_files)
            
            if files_to_upload:
                total_size = sum(f[3] for f in files_to_upload)
                self.debug_logger.info(f"Found {len(files_to_upload)} files to upload, total size: {humanize.naturalsize(total_size)}")
                
                successful, failed = upload_files(files_to_upload)
                
                # Обновляем историю
                history_entry.status = 'completed'
                history_entry.files_processed = len(files_to_upload)
                history_entry.files_uploaded = successful
                history_entry.files_failed = failed
                # ИСПРАВЛЕНО: используем атрибуты объекта
                history_entry.total_size = upload_stats.total_bytes
                history_entry.uploaded_size = upload_stats.uploaded_bytes
                history_entry.duration = time.time() - upload_stats.start_time
                history_entry.end_time = datetime.now().isoformat()
                
                self.debug_logger.info(f"Scheduled sync completed: {successful} successful, {failed} failed, duration: {history_entry.duration:.2f}s")
                
            else:
                history_entry.status = 'completed'
                history_entry.files_processed = 0
                history_entry.end_time = datetime.now().isoformat()
                # ИСПРАВЛЕНО: используем атрибуты объекта
                history_entry.duration = time.time() - upload_stats.start_time
                self.debug_logger.info("Scheduled sync: No files to upload")
            
            # Обновляем расписание
            schedule.last_run = datetime.now().isoformat()
            next_run = self.job_scheduler.get_next_run_time(schedule.id)
            schedule.next_run = next_run.isoformat() if next_run else None
            self.save_schedules()
            
        except Exception as e:
            self.debug_logger.error(f"Scheduled sync error: {e}")
            history_entry.status = 'failed'
            history_entry.error = str(e)
            history_entry.end_time = datetime.now().isoformat()
            # ИСПРАВЛЕНО: используем атрибуты объекта
            history_entry.duration = time.time() - upload_stats.start_time
            self.save_schedules()
        
        finally:
            # ИСПРАВЛЕНО: восстанавливаем состояние объекта
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
            
            self.debug_logger.info(f"=== Scheduled sync finished: {schedule.name} ===")

    def _init_upload_stats(self):
        """Инициализация статистики загрузки - ИСПРАВЛЕНО: используем атрибуты объекта"""
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

    def get_sync_history(self, limit: int = 50, schedule_id: Optional[str] = None, period: str = 'all') -> List[SyncHistory]:
        """Получение истории синхронизаций с фильтрами"""
        filtered_history = self.sync_history
        
        # Фильтр по расписанию
        if schedule_id and schedule_id != 'all':
            filtered_history = [h for h in filtered_history if h.schedule_id == schedule_id]
        
        # Фильтр по периоду времени
        if period != 'all':
            now = datetime.now()
            if period == 'today':
                start_date = datetime(now.year, now.month, now.day)
                filtered_history = [h for h in filtered_history if datetime.fromisoformat(h.start_time) >= start_date]
            elif period == 'week':
                start_date = now - timedelta(days=now.weekday())
                start_date = datetime(start_date.year, start_date.month, start_date.day)
                filtered_history = [h for h in filtered_history if datetime.fromisoformat(h.start_time) >= start_date]
            elif period == 'month':
                start_date = datetime(now.year, now.month, 1)
                filtered_history = [h for h in filtered_history if datetime.fromisoformat(h.start_time) >= start_date]
        
        return filtered_history[-limit:]

    def get_schedule_stats(self, schedule_id: str) -> dict:
        """Получение статистики для расписания"""
        schedule_history = [h for h in self.sync_history if h.schedule_id == schedule_id]
        
        if not schedule_history:
            return {}
            
        successful_runs = [h for h in schedule_history if h.status == 'completed']
        failed_runs = [h for h in schedule_history if h.status == 'failed']
        
        total_files = sum(h.files_uploaded for h in successful_runs)
        total_data = sum(h.uploaded_size for h in successful_runs)
        total_duration = sum(h.duration for h in successful_runs)
        
        avg_duration = total_duration / len(successful_runs) if successful_runs else 0
        
        return {
            'total_runs': len(schedule_history),
            'successful_runs': len(successful_runs),
            'failed_runs': len(failed_runs),
            'success_rate': (len(successful_runs) / len(schedule_history) * 100) if schedule_history else 0,
            'total_files_uploaded': total_files,
            'total_data_uploaded': humanize.naturalsize(total_data),
            'total_data_uploaded_bytes': total_data,
            'average_duration': avg_duration,
            'last_run': schedule_history[-1].to_dict() if schedule_history else None
        }

    def start(self):
        """Запуск планировщика"""
        self.job_scheduler.start()
        
        # Восстанавливаем все включенные задания
        enabled_count = 0
        for schedule in self.schedules.values():
            if schedule.enabled:
                self.job_scheduler.schedule_job(schedule, self.run_scheduled_sync, (schedule,))
                enabled_count += 1
        
        self.debug_logger.info(f"Restored {enabled_count} enabled schedules")

    def shutdown(self):
        """Остановка планировщика"""
        self.job_scheduler.shutdown()

    # Методы для работы с отладочными логами
    def get_debug_logs(self, level: str = 'INFO', limit: int = 100):
        return self.debug_logger.get_logs(level, limit)
    
    def clear_debug_logs(self) -> bool:
        return self.debug_logger.clear_logs()

# Глобальный экземпляр планировщика
scheduler_service = SchedulerService()