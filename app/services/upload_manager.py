import os
import time
import logging
import humanize
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple

from app.utils.config import (
    get_max_threads, get_upload_retries, get_retry_delay, 
    get_storage_class, get_enable_tape_storage, upload_stats
)
from app.services.s3_client import upload_file_to_s3

# Логгер
logger = logging.getLogger(__name__)

def upload_files(files_to_upload: List[Tuple]) -> Tuple[int, int]:
    """Основная функция загрузки файлов в S3"""
    
    logger.info(f" UPLOAD MANAGER: Starting upload process for {len(files_to_upload)} files")
    
    if not files_to_upload:
        logger.warning(" No files to upload")
        return 0, 0
    
    # Проверяем, что статистика инициализирована
    if upload_stats.start_time == 0:
        logger.error(" Upload stats not initialized!")
        return 0, 0
    
    logger.info(" Upload stats verified")
    
    # Получаем настройки
    max_threads = get_max_threads()
    max_retries = get_upload_retries()
    retry_delay = get_retry_delay()
    
    logger.info(f" Upload settings: max_threads={max_threads}, max_retries={max_retries}, retry_delay={retry_delay}")
    
    successful_uploads = 0
    failed_uploads = 0
    
    try:
        # Обновляем общую статистику
        upload_stats.total_files = len(files_to_upload)
        upload_stats.total_bytes = sum(file[3] for file in files_to_upload)
        upload_stats.is_running = True
        
        logger.info(f" Total files: {upload_stats.total_files}, Total size: {humanize.naturalsize(upload_stats.total_bytes)}")
        
        # Используем ThreadPoolExecutor для параллельной загрузки
        with ThreadPoolExecutor(max_workers=max_threads) as executor:
            logger.info(f" Created ThreadPoolExecutor with {max_threads} workers")
            
            # Запускаем загрузку каждого файла
            future_to_file = {}
            for file_info in files_to_upload:
                if not upload_stats.is_running:
                    logger.warning(" Upload stopped by user")
                    break
                    
                future = executor.submit(upload_single_file_with_retry, file_info, max_retries, retry_delay)
                future_to_file[future] = file_info
            
            logger.info(f" Submitted {len(future_to_file)} files for upload")
        
            # Обрабатываем завершенные задачи
            for future in as_completed(future_to_file):
                file_info = future_to_file[future]
                file_path = file_info[0]
                
                try:
                    result = future.result()
                    if result:
                        successful_uploads += 1
                        upload_stats.successful += 1
                        logger.info(f" Successfully uploaded: {os.path.basename(file_path)}")
                    else:
                        failed_uploads += 1
                        upload_stats.failed += 1
                        logger.error(f" Failed to upload: {os.path.basename(file_path)}")
                        
                except Exception as e:
                    failed_uploads += 1
                    upload_stats.failed += 1
                    logger.error(f" Exception during upload of {os.path.basename(file_path)}: {e}")
        
        logger.info(f" Upload process completed: {successful_uploads} successful, {failed_uploads} failed")
        
    except Exception as e:
        logger.error(f" Critical error in upload_files: {e}")
        import traceback
        logger.error(f" Stack trace: {traceback.format_exc()}")
        failed_uploads = len(files_to_upload)
    
    finally:
        upload_stats.is_running = False
        logger.info(" Upload manager finished")
    
    return successful_uploads, failed_uploads

def upload_single_file_with_retry(file_info: Tuple, max_retries: int, retry_delay: int) -> bool:
    """Загрузка одного файла с повторными попытками"""
    full_path, relative_path, tag, file_size = file_info
    filename = os.path.basename(full_path)
    
    logger.info(f" Starting upload: {filename} (size: {humanize.naturalsize(file_size)})")
    
    for attempt in range(max_retries + 1):
        try:
            if not upload_stats.is_running:
                logger.warning(f" Upload stopped during attempt {attempt + 1} for {filename}")
                return False
            
            # Записываем время начала загрузки файла
            upload_stats.file_start_times[full_path] = time.time()
            
            # Пытаемся загрузить файл
            success = upload_file_to_s3(full_path, relative_path, tag, file_size, {})
            
            if success:
                # Обновляем статистику
                upload_stats.uploaded_bytes += file_size
                upload_stats.file_start_times.pop(full_path, None)
                logger.info(f" Upload successful: {filename} (attempt {attempt + 1})")
                return True
            else:
                logger.warning(f" Upload failed: {filename} (attempt {attempt + 1})")
                
        except Exception as e:
            logger.error(f" Exception during upload of {filename} (attempt {attempt + 1}): {e}")
        
        # Если это не последняя попытка - ждем перед повторной попыткой
        if attempt < max_retries:
            logger.info(f" Waiting {retry_delay}s before retry {attempt + 2} for {filename}")
            time.sleep(retry_delay)
    
    logger.error(f" All {max_retries + 1} attempts failed for {filename}")
    return False

class UploadManager:
    """Менеджер загрузки файлов (для обратной совместимости)"""
    
    @staticmethod
    def upload_files(files_to_upload: List[Tuple]) -> Tuple[int, int]:
        """Статический метод для обратной совместимости"""
        return upload_files(files_to_upload)