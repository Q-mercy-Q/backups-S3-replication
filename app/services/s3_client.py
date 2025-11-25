import os
import time
import logging
import humanize 
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
        """Создает клиент MinIO - ВСЕГДА АКТУАЛЬНЫЕ КОНФИГИ"""
        endpoint = get_s3_endpoint()
        access_key = get_aws_access_key_id()
        secret_key = get_aws_secret_access_key()
        bucket = get_s3_bucket()
        
        # Логируем используемую конфигурацию (без секретного ключа)
        self.logger.info(f" S3Client config - Endpoint: {endpoint}, Bucket: {bucket}, AccessKey: {access_key[:8]}...")
        
        if not endpoint or not access_key or not secret_key or not bucket:
            self.logger.error(" Missing S3 configuration parameters!")
            raise Exception("S3 configuration is incomplete")
        
        return Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=False
        )
    
    def test_connection(self) -> bool:
        """Тестирование соединения с S3"""
        try:
            endpoint = get_s3_endpoint()
            bucket = get_s3_bucket()
            
            self.logger.info(f" Testing connection to S3 - Endpoint: {endpoint}, Bucket: {bucket}")
            
            minio_client = self.get_minio_client()
            
            if not minio_client.bucket_exists(bucket):
                self.logger.error(f" Bucket {bucket} does not exist")
                return False
            
            self.logger.info(" Bucket access confirmed")
            return True
            
        except Exception as e:
            self.logger.error(f" Connection test failed: {e}")
            return False
    
    def get_existing_s3_files(self) -> Set[str]:
        """Получает список файлов, уже существующих в S3 бакете"""
        existing_files = set()
        try:
            bucket = get_s3_bucket()
            self.logger.info(f" Scanning existing files in S3 bucket: {bucket}")
        
            minio_client = self.get_minio_client()
            objects = minio_client.list_objects(bucket, recursive=True)
            
            count = 0
            for obj in objects:
                # Извлекаем оригинальное имя файла из S3 ключа
                if '/' in obj.object_name:
                    original_path = '/'.join(obj.object_name.split('/')[1:])
                    existing_files.add(original_path)
                    count += 1
                    
                    if count % 100 == 0:  # Логируем каждые 100 файлов
                        self.logger.info(f" Scanned {count} existing files...")
            
            self.logger.info(f" Found {len(existing_files)} existing files in S3 bucket")
            return existing_files
            
        except Exception as e:
            self.logger.error(f" Error scanning S3 bucket: {e}")
            return set()
    
    def upload_file_to_s3(self, full_path: str, relative_path: str, tag: str, 
                         file_size: int, file_stats: dict) -> bool:
        """Загружает файл в S3"""
        if not upload_stats.is_running:
            self.logger.warning(f" Upload stopped, skipping: {os.path.basename(full_path)}")
            return False
            
        safe_key = normalize_s3_key(tag, relative_path)
        
        if not os.path.exists(full_path):
            self.logger.error(f" File not found: {full_path}")
            return False
        
        file_start_time = time.time()
        filename = os.path.basename(full_path)
        
        try:
            self.logger.info(f" Starting S3 upload: {filename} -> {safe_key}")
            
            minio_client = self.get_minio_client()
            bucket = get_s3_bucket()
            
            # Проверяем существование файла (дополнительная проверка)
            objects = list(minio_client.list_objects(bucket, prefix=safe_key))
            if objects:
                self.logger.warning(f" File already exists in S3: {safe_key}")
                return True
            
            # Загружаем файл
            minio_client.fput_object(
                bucket_name=bucket,
                object_name=safe_key,
                file_path=full_path,
                content_type='application/octet-stream'
            )
            
            upload_time = time.time() - file_start_time
            speed = file_size / upload_time if upload_time > 0 else 0
            
            # ИСПРАВЛЕНИЕ: используем импортированный humanize
            self.logger.info(f" S3 upload successful: {filename} ({humanize.naturalsize(file_size)} in {upload_time:.2f}s, {humanize.naturalsize(speed)}/s)")
            return True
            
        except S3Error as e:
            self.logger.error(f" S3 error uploading {filename}: {e}")
            return False
        except Exception as e:
            self.logger.error(f" Unexpected error uploading {filename}: {e}")
            return False

# Глобальный экземпляр для обратной совместимости
s3_client = S3Client()

# Функции для обратной совместимости
def test_connection():
    return s3_client.test_connection()

def get_existing_s3_files():
    return s3_client.get_existing_s3_files()

def upload_file_to_s3(full_path: str, relative_path: str, tag: str, file_size: int, file_stats: dict) -> bool:
    return s3_client.upload_file_to_s3(full_path, relative_path, tag, file_size, file_stats)