import os
import time
import logging
import humanize
from concurrent.futures import ThreadPoolExecutor, as_completed, CancelledError
from typing import List, Tuple, Optional

from app.utils.config import (
    get_max_threads, get_upload_retries, get_retry_delay,
    get_storage_class, get_enable_tape_storage, upload_stats
)
from app.services.s3_client import upload_file_to_s3
from app.utils.structured_logger import UploadLogger
from app.utils.upload_control import upload_control

# Логгер
logger = logging.getLogger(__name__)

# Создаем специализированный логгер для загрузки
upload_logger = UploadLogger()

def upload_files(files_to_upload: List[Tuple]) -> Tuple[int, int]:
    """Основная функция загрузки файлов в S3"""
    
    if not files_to_upload:
        logger.warning("No files to upload")
        return 0, 0

    if upload_stats.start_time == 0:
        logger.error("Upload stats not initialized!")
        return 0, 0

    max_threads = get_max_threads()
    max_retries = get_upload_retries()
    retry_delay = get_retry_delay()

    upload_stats.total_files = len(files_to_upload)
    upload_stats.total_bytes = sum(file[3] for file in files_to_upload)
    upload_stats.is_running = True

    upload_control.reset()
    upload_logger.start_upload_session(upload_stats.total_files, upload_stats.total_bytes)

    logger.info(
        f"Upload manager started: {upload_stats.total_files} files, "
        f"{humanize.naturalsize(upload_stats.total_bytes)}, "
        f"max_threads={max_threads}, max_retries={max_retries}, retry_delay={retry_delay}s"
    )

    successful_uploads = 0
    failed_uploads = 0
    last_progress_log = time.time()
    progress_log_interval = 30

    executor = ThreadPoolExecutor(max_workers=max_threads)
    upload_control.register_executor(executor)

    try:
        future_to_file = {}
        for file_info in files_to_upload:
            if upload_control.stop_requested():
                logger.warning("Stop requested: skipping remaining files")
                break

            future = executor.submit(upload_single_file_with_retry, file_info, max_retries, retry_delay)
            future_to_file[future] = file_info

        logger.info(f"Submitted {len(future_to_file)} files for upload")

        completed_count = 0
        for future in as_completed(future_to_file):
            file_info = future_to_file[future]
            filename = os.path.basename(file_info[0])

            try:
                result = future.result()
                if result:
                    successful_uploads += 1
                    upload_stats.successful += 1
                else:
                    failed_uploads += 1
                    upload_stats.failed += 1
            except CancelledError:
                logger.warning(f"Upload task cancelled: {filename}")
                failed_uploads += 1
                upload_stats.failed += 1
            except Exception as e:
                failed_uploads += 1
                upload_stats.failed += 1
                logger.error(f"Exception during upload of {filename}: {e}", exc_info=True)

            completed_count += 1

            current_time = time.time()
            if current_time - last_progress_log >= progress_log_interval:
                upload_logger.log_progress(
                    processed=completed_count,
                    successful=successful_uploads,
                    failed=failed_uploads,
                    uploaded_bytes=upload_stats.uploaded_bytes,
                    total_bytes=upload_stats.total_bytes
                )
                last_progress_log = current_time

        upload_logger.end_upload_session(
            successful=successful_uploads,
            failed=failed_uploads,
            uploaded_bytes=upload_stats.uploaded_bytes,
            total_bytes=upload_stats.total_bytes
        )

    except Exception as e:
        logger.error(f"Critical error in upload_files: {e}", exc_info=True)
        failed_uploads = len(files_to_upload)
    finally:
        upload_control.clear_executor()
        executor.shutdown(wait=True, cancel_futures=False)
        upload_stats.is_running = False
        logger.info("Upload manager finished")

    return successful_uploads, failed_uploads

def upload_single_file_with_retry(file_info: Tuple, max_retries: int, retry_delay: int) -> bool:
    """Загрузка одного файла с повторными попытками"""
    full_path, relative_path, tag, file_size = file_info
    filename = os.path.basename(full_path)
    file_start_time: Optional[float] = None
    
    for attempt in range(max_retries + 1):
        if upload_control.force_stop() or not upload_stats.is_running:
            upload_logger.log_file_stopped(filename, "Upload force-stopped")
            return False
        
        try:
            # Логируем начало попытки
            if attempt == 0:
                upload_logger.log_file_start(filename, file_size, attempt + 1)
            else:
                upload_logger.log_file_retry(filename, attempt, retry_delay)
            
            # Записываем время начала загрузки файла
            file_start_time = time.time()
            upload_stats.file_start_times[full_path] = file_start_time
            
            # Пытаемся загрузить файл
            success = upload_file_to_s3(full_path, relative_path, tag, file_size, {})
            
            if success:
                # Вычисляем время загрузки
                upload_time = time.time() - file_start_time if file_start_time else 0
                
                # Обновляем статистику
                upload_stats.uploaded_bytes += file_size
                upload_stats.file_start_times.pop(full_path, None)
                
                # Логируем успех
                upload_logger.log_file_success(filename, file_size, upload_time, attempt + 1)
                return True
            else:
                # Логируем неудачу (но не останавливаем, будет повторная попытка)
                if attempt < max_retries:
                    # Не логируем как ошибку, если будут еще попытки
                    pass
                else:
                    upload_logger.log_file_failure(filename, attempt + 1, "Upload returned False")
                
        except Exception as e:
            error_msg = str(e)
            upload_logger.log_file_failure(filename, attempt + 1, error_msg)
            logger.debug(f"Exception details for {filename}: {e}", exc_info=True)
        
        # Если это не последняя попытка - ждем перед повторной попыткой
        if attempt < max_retries:
            for _ in range(retry_delay):
                if upload_control.force_stop() or not upload_stats.is_running:
                    upload_logger.log_file_stopped(filename, "Upload process stopped during retry delay")
                    return False
                time.sleep(1)
    
    # Все попытки исчерпаны
    upload_logger.log_file_failure(filename, max_retries + 1, "All retry attempts exhausted")
    return False

class UploadManager:
    """Менеджер загрузки файлов (для обратной совместимости)"""
    
    @staticmethod
    def upload_files(files_to_upload: List[Tuple]) -> Tuple[int, int]:
        """Статический метод для обратной совместимости"""
        return upload_files(files_to_upload)