import os
import time
import logging
from datetime import datetime
from typing import Set

from minio import Minio
from minio.error import S3Error

from app.utils.config import (
    get_s3_endpoint, get_aws_access_key_id, get_aws_secret_access_key, 
    get_s3_bucket, get_storage_class, get_enable_tape_storage,
    get_upload_retries, get_retry_delay, upload_stats
)
from app.utils.file_utils import normalize_s3_key

class S3Client:
    """Клиент для работы с S3-совместимым хранилищем"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def get_minio_client(self) -> Minio:
        """Создает клиент MinIO"""
        return Minio(
            get_s3_endpoint(),
            access_key=get_aws_access_key_id(),
            secret_key=get_aws_secret_access_key(),
            secure=False
        )
    
    def test_connection(self) -> bool:
        """Тестирование соединения с S3"""
        try:
            minio_client = self.get_minio_client()
            if not minio_client.bucket_exists(get_s3_bucket()):
                self.logger.error(f"Bucket {get_s3_bucket()} does not exist")
                return False
            
            self.logger.info("✓ Bucket access confirmed")
            return True
            
        except Exception as e:
            self.logger.error(f"✗ Connection test failed: {e}")
            return False
    
    def get_existing_s3_files(self) -> Set[str]:
        """Получает список файлов, уже существующих в S3 бакете"""
        existing_files = set()
        try:
            self.logger.info("Scanning existing files in S3 bucket...")
            minio_client = self.get_minio_client()
            objects = minio_client.list_objects(get_s3_bucket(), recursive=True)
            
            for obj in objects:
                # Извлекаем оригинальное имя файла из S3 ключа
                if '/' in obj.object_name:
                    original_path = '/'.join(obj.object_name.split('/')[1:])
                    existing_files.add(original_path)
            
            self.logger.info(f"Found {len(existing_files)} existing files in S3 bucket")
            return existing_files
            
        except Exception as e:
            self.logger.error(f"Error scanning S3 bucket: {e}")
            return set()
    
    def upload_file_to_s3(self, full_path: str, relative_path: str, tag: str, 
                         file_size: int, file_stats: dict) -> bool:
        """Загружает файл в S3"""
        # ИСПРАВЛЕНО: используем атрибуты объекта
        if not upload_stats.is_running:
            return False
            
        safe_key = normalize_s3_key(tag, relative_path)
        
        if not os.path.exists(full_path):
            self.logger.error(f"File not found: {full_path}")
            return False
        
        file_start_time = time.time()
        # ИСПРАВЛЕНО: используем атрибуты объекта
        upload_stats.file_start_times[relative_path] = file_start_time
        
        import humanize
        file_time = file_stats['modification_time']
        self.logger.info(f"Uploading {relative_path} ({humanize.naturalsize(file_size)}) - {file_time.strftime('%Y-%m-%d %H:%M')} to {safe_key}")
        
        minio_client = self.get_minio_client()
        
        for attempt in range(1, get_upload_retries() + 1):
            # ИСПРАВЛЕНО: используем атрибуты объекта
            if not upload_stats.is_running:
                self._cleanup_upload(relative_path)
                return False
                
            if self._attempt_upload(minio_client, full_path, safe_key, relative_path, 
                                  file_size, file_time, attempt):
                return True
        
        self._handle_upload_failure(relative_path, file_size)
        return False
    
    def _attempt_upload(self, minio_client: Minio, full_path: str, safe_key: str, 
                       relative_path: str, file_size: int, file_time: datetime, 
                       attempt: int) -> bool:
        """Попытка загрузки файла"""
        try:
            metadata = self._create_metadata(relative_path, file_time)
            
            minio_client.fput_object(
                get_s3_bucket(),
                safe_key,
                full_path,
                metadata=metadata
            )
            
            self._cleanup_upload(relative_path)
            self.logger.info(f"✓ Upload complete: {safe_key}")
            # ИСПРАВЛЕНО: используем атрибуты объекта
            upload_stats.successful += 1
            upload_stats.uploaded_bytes += file_size
            return True
            
        except S3Error as e:
            return self._handle_upload_error(e, relative_path, attempt)
        except Exception as e:
            return self._handle_upload_error(e, relative_path, attempt)
    
    def _create_metadata(self, relative_path: str, file_time: datetime) -> dict:
        """Создает метаданные для загрузки"""
        metadata = {
            'x-amz-meta-original-filename': relative_path,
            'x-amz-meta-upload-time': datetime.now().isoformat(),
            'x-amz-meta-file-modified': file_time.isoformat()
        }
        
        if get_enable_tape_storage():
            metadata['x-amz-storage-class'] = get_storage_class()
        
        return metadata
    
    def _handle_upload_error(self, error: Exception, relative_path: str, attempt: int) -> bool:
        """Обрабатывает ошибку загрузки"""
        wait = get_retry_delay() * attempt
        self.logger.warning(f"Attempt {attempt} failed for {relative_path}, retry in {wait}s: {error}")
        
        # ИСПРАВЛЕНО: используем атрибуты объекта
        if attempt < get_upload_retries() and upload_stats.is_running:
            return self._wait_for_retry(wait, relative_path)
        else:
            return False
    
    def _wait_for_retry(self, wait_time: int, relative_path: str) -> bool:
        """Ожидание перед повторной попыткой"""
        for _ in range(wait_time):
            # ИСПРАВЛЕНО: используем атрибуты объекта
            if not upload_stats.is_running:
                self.logger.info(f"Upload cancelled during retry: {relative_path}")
                return False
            time.sleep(1)
        return True
    
    def _cleanup_upload(self, relative_path: str):
        """Очистка информации о загрузке"""
        # ИСПРАВЛЕНО: используем атрибуты объекта
        if relative_path in upload_stats.file_start_times:
            del upload_stats.file_start_times[relative_path]
    
    def _handle_upload_failure(self, relative_path: str, file_size: int):
        """Обработка неудачной загрузки"""
        self.logger.error(f"✗ Upload FAILED after {get_upload_retries()} attempts: {relative_path}")
        # ИСПРАВЛЕНО: используем атрибуты объекта
        upload_stats.failed += 1
        self._cleanup_upload(relative_path)

# Глобальный экземпляр для обратной совместимости
s3_client = S3Client()

# Функции для обратной совместимости
def test_connection():
    return s3_client.test_connection()

def get_existing_s3_files():
    return s3_client.get_existing_s3_files()

def upload_file_to_s3(full_path, relative_path, tag, file_size, file_stats):
    return s3_client.upload_file_to_s3(full_path, relative_path, tag, file_size, file_stats)