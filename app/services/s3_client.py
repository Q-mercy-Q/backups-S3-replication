"""
S3 Client for MinIO storage
"""

import logging
from typing import Optional, Set
import os
from minio import Minio
from minio.error import S3Error

try:
    import boto3
    from botocore.exceptions import ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

from app.utils.config import (
    get_s3_endpoint, get_s3_bucket, 
    get_aws_access_key_id, get_aws_secret_access_key,
    get_storage_class, get_enable_tape_storage
)

logger = logging.getLogger(__name__)

# Словарь клиентов MinIO по user_id для поддержки нескольких пользователей
_minio_clients: dict = {}
# Словарь boto3 клиентов для поддержки storage_class
_boto3_clients: dict = {}

def clear_minio_client_cache(user_id: Optional[int] = None):
    """Очистка кэша MinIO и boto3 клиентов для пользователя
    
    Args:
        user_id: ID пользователя (если None, очищается весь кэш)
    """
    global _minio_clients, _boto3_clients
    if user_id is not None:
        cache_key = user_id
        if cache_key in _minio_clients:
            del _minio_clients[cache_key]
            logger.info(f"MinIO client cache cleared for user_id={user_id}")
        if cache_key in _boto3_clients:
            del _boto3_clients[cache_key]
            logger.info(f"boto3 client cache cleared for user_id={user_id}")
    else:
        _minio_clients.clear()
        _boto3_clients.clear()
        logger.info("MinIO and boto3 client cache cleared for all users")

def get_minio_client(user_id: Optional[int] = None):
    """Получение или создание MinIO клиента для пользователя
    
    Args:
        user_id: ID пользователя (для использования его конфигурации)
    """
    global _minio_clients
    
    # Если user_id не указан, используем ключ None (дефолтная конфигурация)
    cache_key = user_id if user_id is not None else None
    
    if cache_key not in _minio_clients:
        try:
            # Получаем endpoint и определяем secure ДО удаления протокола
            endpoint_raw = get_s3_endpoint(user_id=user_id)
            
            # Проверяем, что endpoint не пустой и не None
            if not endpoint_raw or not isinstance(endpoint_raw, str):
                raise ValueError(f"Invalid S3 endpoint: {endpoint_raw}. Endpoint must be a non-empty string.")
            
            # Определяем secure по протоколу
            is_secure = endpoint_raw.startswith('https://') or ':443' in endpoint_raw
            
            # Убираем протокол из endpoint для MinIO клиента
            endpoint = endpoint_raw.replace('https://', '').replace('http://', '').strip()
            
            # Проверяем, что endpoint не стал пустым после обработки
            if not endpoint:
                raise ValueError(f"Invalid S3 endpoint after processing: '{endpoint_raw}'. Endpoint cannot be empty.")
            
            # Получаем credentials
            access_key = get_aws_access_key_id(user_id=user_id)
            secret_key = get_aws_secret_access_key(user_id=user_id)
            
            # Проверяем, что credentials не пустые
            if not access_key or not isinstance(access_key, str):
                raise ValueError(f"Invalid S3 access key for user_id={user_id}. Access key must be a non-empty string.")
            if not secret_key or not isinstance(secret_key, str):
                raise ValueError(f"Invalid S3 secret key for user_id={user_id}. Secret key must be a non-empty string.")
            
            _minio_clients[cache_key] = Minio(
                endpoint=endpoint,
                access_key=access_key,
                secret_key=secret_key,
                secure=is_secure
            )
            logger.info(f"MinIO client initialized for user_id={user_id} (endpoint: {endpoint}, secure: {is_secure})")
        except Exception as e:
            logger.error(f"Failed to initialize MinIO client for user_id={user_id}: {e}", exc_info=True)
            # Очищаем кэш при ошибке инициализации
            if cache_key in _minio_clients:
                del _minio_clients[cache_key]
            raise
    return _minio_clients[cache_key]

def get_boto3_client(user_id: Optional[int] = None):
    """Получение или создание boto3 S3 клиента для пользователя (для поддержки storage_class)
    
    Args:
        user_id: ID пользователя (для использования его конфигурации)
    """
    global _boto3_clients
    
    if not BOTO3_AVAILABLE:
        raise ImportError("boto3 is not installed. Install it with: pip install boto3")
    
    cache_key = user_id if user_id is not None else None
    
    if cache_key not in _boto3_clients:
        try:
            endpoint_url = get_s3_endpoint(user_id=user_id)
            
            # Проверяем, что endpoint не пустой и не None
            if not endpoint_url or not isinstance(endpoint_url, str):
                raise ValueError(f"Invalid S3 endpoint: {endpoint_url}. Endpoint must be a non-empty string.")
            
            # Получаем credentials
            access_key = get_aws_access_key_id(user_id=user_id)
            secret_key = get_aws_secret_access_key(user_id=user_id)
            
            # Проверяем, что credentials не пустые
            if not access_key or not isinstance(access_key, str):
                raise ValueError(f"Invalid S3 access key for user_id={user_id}. Access key must be a non-empty string.")
            if not secret_key or not isinstance(secret_key, str):
                raise ValueError(f"Invalid S3 secret key for user_id={user_id}. Secret key must be a non-empty string.")
            
            _boto3_clients[cache_key] = boto3.client(
                's3',
                endpoint_url=endpoint_url,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                use_ssl=endpoint_url.startswith('https://') or ':443' in endpoint_url
            )
            logger.info(f"boto3 S3 client initialized for user_id={user_id} (endpoint: {endpoint_url})")
        except Exception as e:
            logger.error(f"Failed to initialize boto3 client for user_id={user_id}: {e}", exc_info=True)
            if cache_key in _boto3_clients:
                del _boto3_clients[cache_key]
            raise
    return _boto3_clients[cache_key]

def upload_file_to_s3(file_path: str, s3_key: str, storage_class: Optional[str] = None, user_id: Optional[int] = None) -> bool:
    """
    Загрузка файла в MinIO хранилище с указанным классом хранения
    
    Args:
        file_path: Локальный путь к файлу
        s3_key: Ключ в S3 bucket
        storage_class: Класс хранения (если None, используется из конфигурации пользователя)
        user_id: ID пользователя (для использования его конфигурации)
    
    Returns:
        True если успешно, False в случае ошибки
    """
    try:
        minio_client = get_minio_client(user_id=user_id)
        
        # Определяем класс хранения
        if storage_class is None:
            storage_class = get_storage_class(user_id=user_id)
        
        target_storage_class = storage_class or 'STANDARD'
        
        logger.info(
            "Uploading %s to %s/%s with storage class: %s (user_id: %s)",
            os.path.basename(file_path),
            get_s3_bucket(user_id=user_id),
            s3_key,
            target_storage_class,
            user_id
        )
        
        # Загружаем файл сначала стандартным способом
        # MinIO и многие S3-совместимые хранилища не поддерживают StorageClass при загрузке
        bucket_name = get_s3_bucket(user_id=user_id)
        minio_client.fput_object(
            bucket_name=bucket_name,
            object_name=s3_key,
            file_path=file_path
        )
        logger.info(f"Successfully uploaded {s3_key} to S3 bucket")
        
        # Если нужен нестандартный storage_class, изменяем его после загрузки через copy_object
        if target_storage_class and target_storage_class.upper() != 'STANDARD' and BOTO3_AVAILABLE:
            try:
                s3_client = get_boto3_client(user_id=user_id)
                
                # Используем copy_object для изменения storage class
                # Копируем объект сам на себя, но с другим storage class
                copy_source = {
                    'Bucket': bucket_name,
                    'Key': s3_key
                }
                
                # Получаем метаданные объекта перед копированием
                try:
                    head_response = s3_client.head_object(Bucket=bucket_name, Key=s3_key)
                    content_type = head_response.get('ContentType', 'application/octet-stream')
                    metadata = head_response.get('Metadata', {})
                    # Копируем все существующие метаданные
                    copy_metadata = metadata.copy()
                except Exception:
                    content_type = 'application/octet-stream'
                    copy_metadata = {}
                
                # Используем copy_object для изменения storage class
                # Формат CopySource: {'Bucket': bucket, 'Key': key}
                copy_params = {
                    'CopySource': copy_source,
                    'Bucket': bucket_name,
                    'Key': s3_key,
                    'StorageClass': target_storage_class.upper()
                }
                
                # Добавляем метаданные, если они есть
                if copy_metadata:
                    copy_params['Metadata'] = copy_metadata
                    copy_params['MetadataDirective'] = 'REPLACE'
                else:
                    copy_params['MetadataDirective'] = 'COPY'
                
                copy_params['ContentType'] = content_type
                
                s3_client.copy_object(**copy_params)
                logger.info(f"Successfully changed storage class to {target_storage_class} for {s3_key}")
                return True
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', '')
                if error_code == 'NotImplemented':
                    logger.warning(
                        f"S3 storage does not support StorageClass modification for {s3_key}. "
                        f"File uploaded but storage class remains STANDARD. "
                        f"Consider using lifecycle policies instead."
                    )
                else:
                    logger.warning(f"Failed to set storage class {target_storage_class} for {s3_key}: {e}")
                # Файл уже загружен, считаем операцию успешной
                return True
            except Exception as e:
                logger.warning(f"Error setting storage class {target_storage_class} for {s3_key}: {e}")
                # Файл уже загружен, считаем операцию успешной
                return True
        
        logger.info(f"Successfully uploaded {s3_key} with storage class {target_storage_class or 'STANDARD'}")
        return True
        
    except S3Error as e:
        logger.error(f"MinIO error uploading {file_path}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error uploading {file_path}: {e}")
        return False

def test_connection(user_id: Optional[int] = None) -> bool:
    """
    Тестирование подключения к MinIO хранилищу с конфигурацией пользователя
    
    Args:
        user_id: ID пользователя (для использования его конфигурации)
    
    Returns:
        True если подключение успешно, False в случае ошибки
    """
    try:
        minio_client = get_minio_client(user_id=user_id)
        
        # Пытаемся получить список buckets
        minio_client.list_buckets()
        
        logger.info(f"MinIO connection test successful (user_id: {user_id})")
        return True
        
    except S3Error as e:
        logger.error(f"MinIO connection test failed (user_id: {user_id}): {e}")
        # Очищаем кэш клиента при ошибке для возможности переподключения
        cache_key = user_id if user_id is not None else None
        if cache_key in _minio_clients:
            del _minio_clients[cache_key]
        return False
    except Exception as e:
        logger.error(f"MinIO connection test failed (user_id: {user_id}): {e}", exc_info=True)
        # Очищаем кэш клиента при ошибке для возможности переподключения
        cache_key = user_id if user_id is not None else None
        if cache_key in _minio_clients:
            del _minio_clients[cache_key]
        return False

def get_existing_s3_files(user_id: Optional[int] = None) -> Set[str]:
    """
    Получение списка существующих файлов в MinIO bucket с конфигурацией пользователя
    
    Args:
        user_id: ID пользователя (для использования его конфигурации)
    
    Returns:
        Множество S3 ключей
    """
    existing_files = set()
    try:
        minio_client = get_minio_client(user_id=user_id)
        
        objects = minio_client.list_objects(get_s3_bucket(user_id=user_id), recursive=True)
        for obj in objects:
            existing_files.add(obj.object_name)
        
        logger.info(f"Found {len(existing_files)} existing files in MinIO bucket (user_id: {user_id})")
        return existing_files
        
    except S3Error as e:
        logger.error(f"Error listing MinIO files (user_id: {user_id}): {e}")
        return existing_files
    except Exception as e:
        logger.error(f"Error listing MinIO files (user_id: {user_id}): {e}")
        return existing_files

def check_file_exists(s3_key: str, user_id: Optional[int] = None) -> bool:
    """
    Проверка существования файла в MinIO
    
    Args:
        s3_key: Ключ файла в MinIO
        user_id: ID пользователя (для использования его конфигурации)
    
    Returns:
        True если файл существует
    """
    try:
        minio_client = get_minio_client(user_id=user_id)
        minio_client.stat_object(get_s3_bucket(user_id=user_id), s3_key)
        return True
    except S3Error as e:
        if e.code == 'NoSuchKey':
            return False
        logger.error(f"Error checking file existence {s3_key} (user_id: {user_id}): {e}")
        return False
    except Exception as e:
        logger.error(f"Error checking file existence {s3_key} (user_id: {user_id}): {e}")
        return False

def get_file_size(s3_key: str, user_id: Optional[int] = None) -> Optional[int]:
    """
    Получение размера файла в MinIO
    
    Args:
        s3_key: Ключ файла в MinIO
        user_id: ID пользователя (для использования его конфигурации)
    
    Returns:
        Размер файла в байтах или None если файл не существует
    """
    try:
        minio_client = get_minio_client(user_id=user_id)
        stats = minio_client.stat_object(get_s3_bucket(user_id=user_id), s3_key)
        return stats.size
    except S3Error as e:
        if e.code == 'NoSuchKey':
            return None
        logger.error(f"Error getting file size {s3_key} (user_id: {user_id}): {e}")
        return None
    except Exception as e:
        logger.error(f"Error getting file size {s3_key} (user_id: {user_id}): {e}")
        return None