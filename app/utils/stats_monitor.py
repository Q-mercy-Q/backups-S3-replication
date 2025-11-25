"""
Statistics and monitoring utilities for S3 Backup Manager
"""

import time
import logging
import threading
from datetime import datetime
from typing import Dict, Any

from app.utils.config import upload_stats
from app.utils.file_utils import format_size

# Глобальная переменная для остановки мониторинга
_stats_monitor_running = False
_stats_thread = None

def start_stats_monitor() -> threading.Event:
    """Запуск мониторинга статистики"""
    global _stats_monitor_running, _stats_thread
    
    stop_event = threading.Event()
    _stats_monitor_running = True
    
    def stats_monitor():
        logger = logging.getLogger(__name__)
        while not stop_event.is_set() and _stats_monitor_running:
            try:
                # Здесь может быть логика обновления статистики
                # если нужно отправлять куда-то статистику
                time.sleep(2)
            except Exception as e:
                logger.error(f"Stats monitor error: {e}")
                time.sleep(5)
    
    _stats_thread = threading.Thread(target=stats_monitor, daemon=True)
    _stats_thread.start()
    
    return stop_event

def stop_stats_monitor():
    """Остановка мониторинга статистики"""
    global _stats_monitor_running
    _stats_monitor_running = False

def print_final_statistics():
    """Вывод финальной статистики"""
    logger = logging.getLogger(__name__)
    
    # ИСПРАВЛЕНО: правильная проверка атрибута объекта
    if upload_stats.start_time == 0.0:
        logger.info("No upload statistics available")
        return
    
    elapsed_time = time.time() - upload_stats.start_time
    processed_files = upload_stats.successful + upload_stats.failed
    
    logger.info("=== UPLOAD FINISHED ===")
    logger.info(f"Total files processed: {processed_files}")
    logger.info(f"Successful: {upload_stats.successful}")
    logger.info(f"Failed: {upload_stats.failed}")
    logger.info(f"Skipped (existing): {upload_stats.skipped_existing}")
    logger.info(f"Skipped (time filter): {upload_stats.skipped_time}")
    
    if elapsed_time > 0:
        bytes_per_second = upload_stats.uploaded_bytes / elapsed_time
        logger.info(f"Upload speed: {format_size(bytes_per_second)}/s")
        logger.info(f"Total duration: {_format_duration(elapsed_time)}")
    
    if processed_files > 0:
        success_rate = (upload_stats.successful / processed_files) * 100
        logger.info(f"Success rate: {success_rate:.1f}%")

def _format_duration(seconds: float) -> str:
    """Форматирование длительности"""
    if seconds < 60:
        return f"{seconds:.1f} seconds"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"

def get_detailed_stats() -> Dict[str, Any]:
    """Получение детальной статистики для отображения"""
    # ИСПРАВЛЕНО: правильная проверка атрибута объекта
    if upload_stats.start_time == 0.0 or upload_stats.total_files == 0:
        return {"message": "No active upload"}
    
    elapsed_time = time.time() - upload_stats.start_time
    processed_files = upload_stats.successful + upload_stats.failed
    
    progress_percent = 0
    if upload_stats.total_files > 0:
        progress_percent = (processed_files / upload_stats.total_files) * 100
        
    bytes_per_second = upload_stats.uploaded_bytes / elapsed_time if elapsed_time > 0 else 0
    
    return {
        'overall_progress': progress_percent,
        'files_processed': processed_files,
        'total_files': upload_stats.total_files,
        'successful': upload_stats.successful,
        'failed': upload_stats.failed,
        'skipped_existing': upload_stats.skipped_existing,
        'skipped_time': upload_stats.skipped_time,
        'total_size': format_size(upload_stats.total_bytes),
        'uploaded_size': format_size(upload_stats.uploaded_bytes),
        'upload_speed': f"{format_size(bytes_per_second)}/s",
        'elapsed_time': _format_duration(elapsed_time),
        'start_time': datetime.fromtimestamp(upload_stats.start_time).strftime('%Y-%m-%d %H:%M:%S') if upload_stats.start_time else 'N/A'
    }