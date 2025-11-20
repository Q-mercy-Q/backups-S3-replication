import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from typing import Callable, Any

from app.models.schedule import Schedule

class JobScheduler:
    """Сервис для управления планировщиком заданий"""
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.logger = logging.getLogger(__name__)
    
    def start(self):
        """Запуск планировщика"""
        if not self.scheduler.running:
            self.scheduler.start()
            self.logger.info("Scheduler started")
    
    def shutdown(self):
        """Остановка планировщика"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            self.logger.info("Scheduler stopped")
    
    def schedule_job(self, schedule: Schedule, job_func: Callable, args: tuple) -> bool:
        """Планирование задачи"""
        try:
            job_id = schedule.id
            
            if schedule.schedule_type == 'interval':
                trigger = IntervalTrigger(minutes=int(schedule.interval))
                self.logger.debug(f"Scheduling interval job: {schedule.name} every {schedule.interval} minutes")
            elif schedule.schedule_type == 'cron':
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