import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from typing import Callable, Any

from app.models.schedule import Schedule, ScheduleType

class JobScheduler:
    """Сервис для управления планировщиком заданий"""
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.logger = logging.getLogger(__name__)
        self._running = False
    
    def start(self):
        """Запуск планировщика"""
        if not self._running:
            try:
                self.scheduler.start()
                self._running = True
                self.logger.info("Scheduler started")
            except Exception as e:
                self.logger.error(f"Failed to start scheduler: {e}")
                raise
        else:
            self.logger.debug("Scheduler already running")
    
    def shutdown(self):
        """Остановка планировщика"""
        if self._running:
            try:
                self.scheduler.shutdown()
                self._running = False
                self.logger.info("Scheduler stopped")
            except Exception as e:
                self.logger.error(f"Error stopping scheduler: {e}")
                raise
        else:
            self.logger.debug("Scheduler not running, skip shutdown")
    
    @property
    def running(self):
        """Проверка работает ли планировщик"""
        return self._running and self.scheduler.running
    
    def schedule_job(self, schedule: Schedule, job_func: Callable, args: tuple) -> bool:
        """Планирование задачи"""
        try:
            job_id = schedule.id
            
            # ИСПРАВЛЕНИЕ: используем value enum для сравнения
            if schedule.schedule_type.value == 'interval':
                trigger = IntervalTrigger(minutes=int(schedule.interval))
                self.logger.debug(f"Scheduling interval job: {schedule.name} every {schedule.interval} minutes")
            elif schedule.schedule_type.value == 'cron':
                trigger = CronTrigger.from_crontab(schedule.interval)
                self.logger.debug(f"Scheduling cron job: {schedule.name} with expression '{schedule.interval}'")
            else:
                self.logger.error(f"Unknown schedule type: {schedule.schedule_type}")
                return False
                
            self.scheduler.add_job(
                job_func,
                trigger=trigger,
                id=job_id,
                name=schedule.name,
                args=args,
                replace_existing=True
            )
            
            # Обновляем следующее время выполнения
            next_run = self.scheduler.get_job(job_id).next_run_time
            schedule.next_run = next_run.isoformat() if next_run else None
            
            self.logger.info(f"Scheduled job: {schedule.name}, next run: {next_run}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error scheduling job: {e}")
            return False
    
    def unschedule_job(self, job_id: str):
        """Удаление задачи из планировщика"""
        try:
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
                self.logger.debug(f"Unscheduled job: {job_id}")
        except Exception as e:
            self.logger.error(f"Error unscheduling job: {e}")
    
    def get_next_run_time(self, job_id: str) -> datetime:
        """Получение времени следующего запуска задачи"""
        job = self.scheduler.get_job(job_id)
        return job.next_run_time if job else None