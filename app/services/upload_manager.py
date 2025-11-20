import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple

from app.utils.config import get_max_threads, upload_stats
from app.services.s3_client import upload_file_to_s3
from app.utils.file_utils import get_file_modification_time

class UploadManager:
    """Сервис для управления загрузкой файлов"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def upload_files(self, files_with_size: List[Tuple]) -> Tuple[int, int]:
        """Управляет процессом загрузки файлов"""
        successful_uploads = 0
        failed_uploads = 0

        max_threads = get_max_threads()
        self.logger.info(f"Starting upload of {len(files_with_size)} files with {max_threads} threads")

        try:
            # Разделяем на тестовые и основные файлы
            test_files = files_with_size[:5]
            remaining_files = files_with_size[5:]
            
            # Тестовая загрузка
            successful_uploads, failed_uploads = self._upload_batch(test_files, min(max_threads, 3))
            
            # Проверяем флаг остановки перед основной загрузкой
            # ИСПРАВЛЕНО: используем атрибуты объекта
            if not upload_stats.is_running:
                self.logger.info("Upload stopped before main batch")
                return successful_uploads, failed_uploads
            
            # Основная загрузка
            # ИСПРАВЛЕНО: используем атрибуты объекта
            if upload_stats.is_running and successful_uploads > 0 and remaining_files:
                self.logger.info("Initial test successful, proceeding with all files...")
                success, failed = self._upload_batch(remaining_files, max_threads)
                successful_uploads += success
                failed_uploads += failed
        
        except KeyboardInterrupt:
            self.logger.info("Upload interrupted by user")
            # ИСПРАВЛЕНО: используем атрибуты объекта
            upload_stats.is_running = False
        except Exception as e:
            self.logger.error(f"Upload manager error: {e}")
            failed_uploads += len(files_with_size) - (successful_uploads + failed_uploads)
        
        return successful_uploads, failed_uploads
    
    def _upload_batch(self, files_batch: List[Tuple], workers: int) -> Tuple[int, int]:
        """Загружает пакет файлов"""
        successful = 0
        failed = 0
        
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = self._create_upload_futures(pool, files_batch)
            successful, failed = self._process_upload_futures(futures)
        
        return successful, failed
    
    def _create_upload_futures(self, pool: ThreadPoolExecutor, files_batch: List[Tuple]) -> dict:
        """Создает futures для загрузки файлов"""
        futures = {}
        for full, rel, tag, size in files_batch:
            # Проверка флага остановки - ИСПРАВЛЕНО: используем атрибуты объекта
            if not upload_stats.is_running:
                self.logger.info("Stopping batch upload due to stop request")
                break
                
            # Получаем информацию о файле для метаданных
            file_stats = {
                'modification_time': get_file_modification_time(full)
            }
            
            future = pool.submit(upload_file_to_s3, full, rel, tag, size, file_stats)
            futures[future] = (full, rel, tag, size)
        
        return futures
    
    def _process_upload_futures(self, futures: dict) -> Tuple[int, int]:
        """Обрабатывает завершенные задачи загрузки"""
        successful = 0
        failed = 0
        
        for future in as_completed(futures):
            # Проверяем флаг остановки между завершением задач - ИСПРАВЛЕНО: используем атрибуты объекта
            if not upload_stats.is_running:
                self._cancel_pending_uploads(futures)
                break
                
            full, rel, tag, size = futures[future]
            try:
                if future.result():
                    successful += 1
                else:
                    failed += 1
            except Exception as e:
                self.logger.error(f"Unhandled exception during upload of {rel}: {e}")
                failed += 1
        
        return successful, failed
    
    def _cancel_pending_uploads(self, futures: dict):
        """Отменяет ожидающие загрузки"""
        for future in futures:
            if not future.done(): 
                future.cancel()
        self.logger.info("Cancelled remaining uploads due to stop request")

# Глобальный экземпляр для обратной совместимости
upload_manager = UploadManager()

# Функции для обратной совместимости
def upload_files(files_with_size):
    return upload_manager.upload_files(files_with_size)