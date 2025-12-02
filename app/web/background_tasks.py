import threading
import time
import logging
from datetime import datetime
import humanize

from typing import Optional, List
from app.utils.config import upload_stats, validate_environment, get_file_categories
from app.services.file_scanner import scan_backup_files
from app.services.s3_client import test_connection, get_existing_s3_files
from app.services.upload_manager import upload_files

# Глобальные переменные для управления загрузкой
upload_thread = None
stop_event = threading.Event()
stats_thread = None
socketio_instance = None

def init_app(app, socketio):
    """Инициализация фоновых задач"""
    global socketio_instance
    socketio_instance = socketio
    
    # Инициализируем WebLogHandler
    from app.web.log_handler import WebLogHandler
    web_handler = WebLogHandler(socketio)
    
    # Добавляем обработчик к корневому логгеру
    logging.getLogger().addHandler(web_handler)
    
    # Запускаем мониторинг статистики
    start_stats_monitor()

def run_upload(
    user_id: int,
    files_to_upload: Optional[List] = None,
    upload_mode: str = 'auto',
    storage_class: Optional[str] = None
):
    """
    Запуск процесса загрузки в отдельном потоке с конфигурацией пользователя
    
    Args:
        user_id: ID пользователя для загрузки конфигурации
        files_to_upload: Список файлов для загрузки (если None, выполняется автоматическое сканирование)
        upload_mode: Режим загрузки ('auto' - автоматическое сканирование, 'manual' - загрузка указанных файлов)
        storage_class: Класс хранения для загружаемых файлов (если None, используется из конфигурации)
    """
    global upload_thread
    
    try:
        # ИСПРАВЛЕНО: правильная инициализация объекта
        upload_stats.reset()
        upload_stats.start_time = time.time()
        upload_stats.is_running = True
        upload_stats.user_id = user_id
        
        # Сохраняем storage_class в статистику
        if storage_class:
            upload_stats.storage_class = storage_class
            logging.info(f"=== Upload Started (user_id: {user_id}, mode: {upload_mode}, storage_class: {storage_class}) ===")
        else:
            # Если не передан, используем из конфигурации
            from app.utils.config import get_storage_class
            storage_class = get_storage_class(user_id=user_id)
            upload_stats.storage_class = storage_class
            logging.info(f"=== Upload Started (user_id: {user_id}, mode: {upload_mode}, storage_class from config: {storage_class}) ===")
        
        # Валидация окружения пользователя
        validate_environment(user_id=user_id)
        logging.info("Environment validation successful")
        
        # Тест соединения с конфигурацией пользователя
        if not test_connection(user_id=user_id):
            logging.error("Connection test failed. Check credentials and endpoint.")
            return
        
        # Если файлы не переданы, выполняем автоматическое сканирование
        if files_to_upload is None or upload_mode == 'auto':
            # Получаем список существующих файлов в S3 с конфигурацией пользователя
            logging.info("Scanning existing files in S3 bucket...")
            existing_files = get_existing_s3_files(user_id=user_id)
            
            # Сканируем файлы для загрузки с конфигурацией пользователя
            logging.info("Scanning backup files...")
            files_to_upload = scan_backup_files(existing_files, get_file_categories(user_id=user_id), user_id=user_id)
        
        if not files_to_upload:
            logging.info("No files to upload. Exiting.")
            return
        
        logging.info(f"Starting upload of {len(files_to_upload)} files with storage_class: {storage_class}")
        
        # Запускаем загрузку с конфигурацией пользователя и storage_class
        successful, failed = upload_files(files_to_upload, user_id=user_id, storage_class=storage_class)
        
        logging.info("=== Upload Finished ===")
        
    except Exception as e:
        logging.error(f"Upload error: {e}")
        import traceback
        logging.error(traceback.format_exc())
    finally:
        upload_stats.is_running = False

def scan_files_with_config(user_id: int = None):
    """Сканирование файлов с конфигурацией пользователя
    
    Args:
        user_id: ID пользователя (если None, будет использована конфигурация по умолчанию)
    """
    try:
        # Временно устанавливаем is_running для сканирования
        original_running = upload_stats.is_running
        upload_stats.is_running = True
        
        # Сбрасываем статистику сканирования
        upload_stats.total_files = 0
        upload_stats.total_bytes = 0
        upload_stats.skipped_existing = 0
        upload_stats.skipped_time = 0
        
        existing_files = get_existing_s3_files(user_id=user_id)
        files = scan_backup_files(existing_files, get_file_categories(user_id=user_id), user_id=user_id)
        
        # Восстанавливаем состояние
        upload_stats.is_running = original_running
        
        return files
        
    except Exception as e:
        logging.error(f"Scan error: {e}")
        upload_stats.is_running = original_running
        return []

def send_stats_update():
    """Отправка обновления статистики в веб-интерфейс"""
    try:
        stats_data = get_stats_data()
        if socketio_instance:
            socketio_instance.emit('stats_update', stats_data)
    except Exception as e:
        logging.error(f"Error sending stats update: {e}")

def get_stats_data():
    """Получение данных статистики для веб-интерфейс"""
    # ИСПРАВЛЕНО: правильное использование атрибутов объекта
    if upload_stats.start_time == 0.0 or upload_stats.total_files == 0:
        return {
            'overall_progress': 0,
            'current_file_progress': 0,
            'total_files': 0,
            'files_to_upload': 0,
            'successful': 0,
            'failed': 0,
            'skipped_existing': 0,
            'skipped_time': 0,
            'total_size': "0 B",
            'uploaded_size': "0 B",
            'upload_speed': "0 B/s",
            'elapsed_time': "00:00:00",
            'is_running': upload_stats.is_running,
            'detailed_stats': "No active upload" if not upload_stats.is_running else "Initializing..."
        }
        
    elapsed_time = time.time() - upload_stats.start_time
    processed_files = upload_stats.successful + upload_stats.failed
    
    progress_percent = 0
    if upload_stats.total_files > 0:
        progress_percent = (processed_files / upload_stats.total_files) * 100
    
    bytes_per_second = upload_stats.uploaded_bytes / elapsed_time if elapsed_time > 0 else 0
    
    # Форматирование времени
    if elapsed_time > 0:
        hours = int(elapsed_time // 3600)
        minutes = int((elapsed_time % 3600) // 60)
        seconds = int(elapsed_time % 60)
        elapsed_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    else:
        elapsed_str = "00:00:00"
    
    return {
        'overall_progress': progress_percent,
        'current_file_progress': 0,
        'total_files': upload_stats.total_files + upload_stats.skipped_existing + upload_stats.skipped_time,
        'files_to_upload': upload_stats.total_files,
        'successful': upload_stats.successful,
        'failed': upload_stats.failed,
        'skipped_existing': upload_stats.skipped_existing,
        'skipped_time': upload_stats.skipped_time,
        'total_size': humanize.naturalsize(upload_stats.total_bytes),
        'uploaded_size': humanize.naturalsize(upload_stats.uploaded_bytes),
        'upload_speed': f"{humanize.naturalsize(bytes_per_second)}/s",
        'elapsed_time': elapsed_str,
        'is_running': upload_stats.is_running,
        'detailed_stats': get_detailed_stats()
    }

def get_detailed_stats():
    """Получение детальной статистики"""
    # ИСПРАВЛЕНО: правильное использование атрибутов объекта
    if upload_stats.start_time == 0.0 or upload_stats.total_files == 0:
        return "No active upload"
        
    elapsed_time = time.time() - upload_stats.start_time
    processed_files = upload_stats.successful + upload_stats.failed
    
    progress_percent = 0
    if upload_stats.total_files > 0:
        progress_percent = (processed_files / upload_stats.total_files) * 100
        
    bytes_per_second = upload_stats.uploaded_bytes / elapsed_time if elapsed_time > 0 else 0
    
    return f"""
Overall Progress:
  Files: {processed_files}/{upload_stats.total_files} ({progress_percent:.1f}%)
  Successful: {upload_stats.successful} | Failed: {upload_stats.failed}
  Skipped: {upload_stats.skipped_existing} (existing) + {upload_stats.skipped_time} (time filter)

Upload Speed:
  Current: {humanize.naturalsize(bytes_per_second)}/s
  Average: {humanize.naturalsize(upload_stats.uploaded_bytes / elapsed_time) if elapsed_time > 0 else '0 B'}/s

Data Transfer:
  Total to upload: {humanize.naturalsize(upload_stats.total_bytes)}
  Uploaded: {humanize.naturalsize(upload_stats.uploaded_bytes)}
  Remaining: {humanize.naturalsize(upload_stats.total_bytes - upload_stats.uploaded_bytes)}

Time Information:
  Elapsed: {humanize.naturaldelta(elapsed_time) if elapsed_time > 0 else '0 seconds'}
  Started: {datetime.fromtimestamp(upload_stats.start_time).strftime('%Y-%m-%d %H:%M:%S') if upload_stats.start_time else 'N/A'}
""".strip()

def start_stats_monitor():
    """Запуск мониторинга статистики"""
    def stats_monitor():
        while not stop_event.is_set():
            try:
                send_stats_update()
                time.sleep(2)
            except Exception as e:
                logging.error(f"Stats monitor error: {e}")
                time.sleep(5)
    
    global stats_thread
    stats_thread = threading.Thread(target=stats_monitor, daemon=True)
    stats_thread.start()