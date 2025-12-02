"""
Сервис для расширенного управления S3 хранилищем
Включает управление бакетами, политиками, версионированием, lifecycle и т.д.
"""

import logging
import json
from typing import Dict, List, Optional, Any
from datetime import datetime

from minio import Minio
from minio.error import S3Error

try:
    import boto3
    from botocore.exceptions import ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

from app.services.s3_client import get_minio_client, get_boto3_client
from app.utils.config import get_s3_endpoint, get_aws_access_key_id, get_aws_secret_access_key

logger = logging.getLogger(__name__)


def list_all_buckets(user_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Получение списка всех бакетов
    
    Args:
        user_id: ID пользователя
        
    Returns:
        Список словарей с информацией о бакетах
    """
    try:
        minio_client = get_minio_client(user_id=user_id)
        buckets = minio_client.list_buckets()
        
        result = []
        for bucket in buckets:
            bucket_info = {
                'name': bucket.name,
                'creation_date': bucket.creation_date.isoformat() if bucket.creation_date else None,
                'size': 0,
                'object_count': 0
            }
            
            # Получаем статистику бакета
            try:
                objects = list(minio_client.list_objects(bucket.name, recursive=True))
                total_size = 0
                count = 0
                for obj in objects:
                    if hasattr(obj, 'size'):
                        total_size += int(obj.size) if obj.size else 0
                    count += 1
                bucket_info['size'] = total_size
                bucket_info['object_count'] = count
            except Exception as e:
                logger.warning(f"Could not get statistics for bucket {bucket.name}: {e}")
            
            result.append(bucket_info)
        
        return result
    except Exception as e:
        logger.error(f"Error listing buckets: {e}", exc_info=True)
        raise


def create_bucket(bucket_name: str, location: str = "us-east-1", user_id: Optional[int] = None) -> bool:
    """
    Создание нового бакета
    
    Args:
        bucket_name: Имя бакета
        location: Регион/локация (по умолчанию us-east-1)
        user_id: ID пользователя
        
    Returns:
        True если успешно создан
    """
    try:
        minio_client = get_minio_client(user_id=user_id)
        minio_client.make_bucket(bucket_name, location=location)
        logger.info(f"Bucket {bucket_name} created successfully")
        return True
    except S3Error as e:
        if e.code == 'BucketAlreadyExists':
            logger.warning(f"Bucket {bucket_name} already exists")
            return False
        logger.error(f"Error creating bucket {bucket_name}: {e}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"Error creating bucket {bucket_name}: {e}", exc_info=True)
        raise


def delete_bucket(bucket_name: str, force: bool = False, user_id: Optional[int] = None) -> bool:
    """
    Удаление бакета
    
    Args:
        bucket_name: Имя бакета
        force: Если True, удаляет все объекты перед удалением бакета
        user_id: ID пользователя
        
    Returns:
        True если успешно удален
    """
    try:
        minio_client = get_minio_client(user_id=user_id)
        
        if force:
            # Удаляем все объекты
            try:
                objects = list(minio_client.list_objects(bucket_name, recursive=True))
                for obj in objects:
                    minio_client.remove_object(bucket_name, obj.object_name)
                logger.info(f"All objects deleted from bucket {bucket_name}")
            except Exception as e:
                logger.warning(f"Error deleting objects from bucket {bucket_name}: {e}")
        
        minio_client.remove_bucket(bucket_name)
        logger.info(f"Bucket {bucket_name} deleted successfully")
        return True
    except S3Error as e:
        if e.code == 'NoSuchBucket':
            logger.warning(f"Bucket {bucket_name} does not exist")
            return False
        logger.error(f"Error deleting bucket {bucket_name}: {e}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"Error deleting bucket {bucket_name}: {e}", exc_info=True)
        raise


def get_bucket_info(bucket_name: str, user_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Получение подробной информации о бакете
    
    Args:
        bucket_name: Имя бакета
        user_id: ID пользователя
        
    Returns:
        Словарь с информацией о бакете
    """
    try:
        minio_client = get_minio_client(user_id=user_id)
        boto3_client = get_boto3_client(user_id=user_id) if BOTO3_AVAILABLE else None
        
        info = {
            'name': bucket_name,
            'exists': False,
            'versioning': None,
            'lifecycle': None,
            'cors': None,
            'policy': None,
            'tags': {},
            'replication': None
        }
        
        # Проверяем существование и получаем базовую информацию
        try:
            buckets = minio_client.list_buckets()
            for bucket in buckets:
                if bucket.name == bucket_name:
                    info['exists'] = True
                    info['creation_date'] = bucket.creation_date.isoformat() if bucket.creation_date else None
                    break
            
            if not info['exists']:
                return info
            
            # Получаем версионирование через boto3
            if boto3_client:
                try:
                    versioning = boto3_client.get_bucket_versioning(Bucket=bucket_name)
                    info['versioning'] = versioning.get('Status') or 'Disabled'
                    info['versioning_mfa_delete'] = versioning.get('MFADelete') or 'Disabled'
                except ClientError as e:
                    if e.response['Error']['Code'] != 'NoSuchBucket':
                        logger.warning(f"Could not get versioning for bucket {bucket_name}: {e}")
            
            # Получаем lifecycle policy через boto3
            if boto3_client:
                try:
                    lifecycle = boto3_client.get_bucket_lifecycle_configuration(Bucket=bucket_name)
                    info['lifecycle'] = lifecycle.get('Rules', [])
                except ClientError as e:
                    if e.response['Error']['Code'] == 'NoSuchLifecycleConfiguration':
                        info['lifecycle'] = []
                    else:
                        logger.warning(f"Could not get lifecycle for bucket {bucket_name}: {e}")
            
            # Получаем CORS через boto3
            if boto3_client:
                try:
                    cors = boto3_client.get_bucket_cors(Bucket=bucket_name)
                    info['cors'] = cors.get('CORSRules', [])
                except ClientError as e:
                    if e.response['Error']['Code'] == 'NoSuchCORSConfiguration':
                        info['cors'] = []
                    else:
                        logger.warning(f"Could not get CORS for bucket {bucket_name}: {e}")
            
            # Получаем bucket policy через boto3
            if boto3_client:
                try:
                    policy = boto3_client.get_bucket_policy(Bucket=bucket_name)
                    policy_doc = policy.get('Policy')
                    if policy_doc:
                        info['policy'] = json.loads(policy_doc)
                except ClientError as e:
                    if e.response['Error']['Code'] == 'NoSuchBucketPolicy':
                        info['policy'] = None
                    else:
                        logger.warning(f"Could not get policy for bucket {bucket_name}: {e}")
            
            # Получаем теги через boto3
            if boto3_client:
                try:
                    tags = boto3_client.get_bucket_tagging(Bucket=bucket_name)
                    tag_set = tags.get('TagSet', [])
                    info['tags'] = {tag['Key']: tag['Value'] for tag in tag_set}
                except ClientError as e:
                    if e.response['Error']['Code'] == 'NoSuchTagSet':
                        info['tags'] = {}
                    else:
                        logger.warning(f"Could not get tags for bucket {bucket_name}: {e}")
            
            # Получаем репликацию через boto3
            if boto3_client:
                try:
                    replication = boto3_client.get_bucket_replication(Bucket=bucket_name)
                    info['replication'] = replication.get('ReplicationConfiguration')
                except ClientError as e:
                    if e.response['Error']['Code'] == 'ReplicationConfigurationNotFoundError':
                        info['replication'] = None
                    else:
                        logger.warning(f"Could not get replication for bucket {bucket_name}: {e}")
        
        except Exception as e:
            logger.error(f"Error getting bucket info for {bucket_name}: {e}", exc_info=True)
            raise
        
        return info
    except Exception as e:
        logger.error(f"Error getting bucket info for {bucket_name}: {e}", exc_info=True)
        raise


def set_bucket_versioning(bucket_name: str, enabled: bool, mfa_delete: bool = False, user_id: Optional[int] = None) -> bool:
    """
    Включение/выключение версионирования для бакета
    
    Args:
        bucket_name: Имя бакета
        enabled: Включить версионирование
        mfa_delete: Требовать MFA для удаления версий
        user_id: ID пользователя
        
    Returns:
        True если успешно
    """
    if not BOTO3_AVAILABLE:
        raise ImportError("boto3 is required for versioning operations")
    
    try:
        boto3_client = get_boto3_client(user_id=user_id)
        
        config = {
            'Bucket': bucket_name,
            'VersioningConfiguration': {
                'Status': 'Enabled' if enabled else 'Suspended',
                'MFADelete': 'Enabled' if mfa_delete else 'Disabled'
            }
        }
        
        boto3_client.put_bucket_versioning(**config)
        logger.info(f"Versioning {'enabled' if enabled else 'disabled'} for bucket {bucket_name}")
        return True
    except Exception as e:
        logger.error(f"Error setting versioning for bucket {bucket_name}: {e}", exc_info=True)
        raise


def set_bucket_lifecycle(bucket_name: str, rules: List[Dict[str, Any]], user_id: Optional[int] = None) -> bool:
    """
    Установка lifecycle policy для бакета
    
    Args:
        bucket_name: Имя бакета
        rules: Список правил lifecycle
        user_id: ID пользователя
        
    Returns:
        True если успешно
    """
    if not BOTO3_AVAILABLE:
        raise ImportError("boto3 is required for lifecycle operations")
    
    try:
        boto3_client = get_boto3_client(user_id=user_id)
        
        config = {
            'Bucket': bucket_name,
            'LifecycleConfiguration': {
                'Rules': rules
            }
        }
        
        boto3_client.put_bucket_lifecycle_configuration(**config)
        logger.info(f"Lifecycle policy set for bucket {bucket_name}")
        return True
    except Exception as e:
        logger.error(f"Error setting lifecycle for bucket {bucket_name}: {e}", exc_info=True)
        raise


def set_bucket_cors(bucket_name: str, cors_rules: List[Dict[str, Any]], user_id: Optional[int] = None) -> bool:
    """
    Установка CORS правил для бакета
    
    Args:
        bucket_name: Имя бакета
        cors_rules: Список CORS правил
        user_id: ID пользователя
        
    Returns:
        True если успешно
    """
    if not BOTO3_AVAILABLE:
        raise ImportError("boto3 is required for CORS operations")
    
    try:
        boto3_client = get_boto3_client(user_id=user_id)
        
        config = {
            'Bucket': bucket_name,
            'CORSConfiguration': {
                'CORSRules': cors_rules
            }
        }
        
        boto3_client.put_bucket_cors(**config)
        logger.info(f"CORS rules set for bucket {bucket_name}")
        return True
    except Exception as e:
        logger.error(f"Error setting CORS for bucket {bucket_name}: {e}", exc_info=True)
        raise


def set_bucket_policy(bucket_name: str, policy: Dict[str, Any], user_id: Optional[int] = None) -> bool:
    """
    Установка bucket policy
    
    Args:
        bucket_name: Имя бакета
        policy: Политика в формате JSON
        user_id: ID пользователя
        
    Returns:
        True если успешно
    """
    if not BOTO3_AVAILABLE:
        raise ImportError("boto3 is required for policy operations")
    
    try:
        boto3_client = get_boto3_client(user_id=user_id)
        
        policy_json = json.dumps(policy) if isinstance(policy, dict) else policy
        
        boto3_client.put_bucket_policy(
            Bucket=bucket_name,
            Policy=policy_json
        )
        logger.info(f"Policy set for bucket {bucket_name}")
        return True
    except Exception as e:
        logger.error(f"Error setting policy for bucket {bucket_name}: {e}", exc_info=True)
        raise


def set_bucket_tags(bucket_name: str, tags: Dict[str, str], user_id: Optional[int] = None) -> bool:
    """
    Установка тегов для бакета
    
    Args:
        bucket_name: Имя бакета
        tags: Словарь тегов
        user_id: ID пользователя
        
    Returns:
        True если успешно
    """
    if not BOTO3_AVAILABLE:
        raise ImportError("boto3 is required for tagging operations")
    
    try:
        boto3_client = get_boto3_client(user_id=user_id)
        
        tag_set = [{'Key': k, 'Value': v} for k, v in tags.items()]
        
        boto3_client.put_bucket_tagging(
            Bucket=bucket_name,
            Tagging={
                'TagSet': tag_set
            }
        )
        logger.info(f"Tags set for bucket {bucket_name}")
        return True
    except Exception as e:
        logger.error(f"Error setting tags for bucket {bucket_name}: {e}", exc_info=True)
        raise


def get_bucket_statistics(bucket_name: str, user_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Получение статистики по бакету
    
    Args:
        bucket_name: Имя бакета
        user_id: ID пользователя
        
    Returns:
        Словарь со статистикой
    """
    try:
        minio_client = get_minio_client(user_id=user_id)
        
        total_size = 0
        object_count = 0
        storage_classes = {}
        
        for obj in minio_client.list_objects(bucket_name, recursive=True):
            object_count += 1
            if hasattr(obj, 'size'):
                size = int(obj.size) if obj.size else 0
                total_size += size
            
            # Получаем storage class
            storage_class = getattr(obj, 'storage_class', 'STANDARD') or 'STANDARD'
            storage_classes[storage_class] = storage_classes.get(storage_class, 0) + 1
        
        return {
            'bucket_name': bucket_name,
            'total_size': total_size,
            'object_count': object_count,
            'storage_classes': storage_classes
        }
    except Exception as e:
        logger.error(f"Error getting statistics for bucket {bucket_name}: {e}", exc_info=True)
        raise


def get_iam_endpoint(user_id: Optional[int] = None) -> Optional[str]:
    """
    Получение IAM endpoint для подключения
    
    Логика (по приоритету):
    1. Переменная окружения IAM_ENDPOINT / S3_IAM_ENDPOINT
    2. Явный IAM_ENDPOINT / S3_IAM_ENDPOINT в конфигурации пользователя
    3. Ограниченное автоматическое формирование из S3 endpoint:
       - Для MinIO: меняем порт 9000 на 9001
       - Для generic S3 endpoint с суффиксом /s3: заменяем '/s3' на '/iam' в URL
    
    Args:
        user_id: ID пользователя
        
    Returns:
        IAM endpoint URL или None
    """
    import os
    
    try:
        # 1. Проверяем переменную окружения (наивысший приоритет)
        env_iam_endpoint = os.getenv('IAM_ENDPOINT') or os.getenv('S3_IAM_ENDPOINT')
        if env_iam_endpoint and env_iam_endpoint.strip():
            endpoint = env_iam_endpoint.strip().rstrip('/')
            logger.info(f"Using IAM endpoint from environment variable: {endpoint}")
            return endpoint
        
        # 2. Проверяем явный IAM endpoint в конфигурации пользователя
        from app.utils.config import get_config
        config = get_config(user_id=user_id)
        explicit_iam_endpoint = config.get('IAM_ENDPOINT') or config.get('S3_IAM_ENDPOINT')
        
        if explicit_iam_endpoint and explicit_iam_endpoint.strip():
            endpoint = explicit_iam_endpoint.strip().rstrip('/')
            logger.info(f"Using explicit IAM endpoint from user config: {endpoint}")
            return endpoint
        
        # 3. Автоматически формируем из S3 endpoint (ограниченный набор кейсов)
        s3_endpoint = get_s3_endpoint(user_id=user_id)
        if not s3_endpoint:
            logger.warning("S3 endpoint is not configured, cannot determine IAM endpoint")
            return None
        
        # Очищаем S3 endpoint от лишних слешей
        s3_endpoint = s3_endpoint.rstrip('/')
        
        # Для MinIO меняем порт
        if ':9000' in s3_endpoint:
            iam_endpoint = s3_endpoint.replace(':9000', ':9001').rstrip('/')
            logger.info(f"Auto-generated IAM endpoint for MinIO: {iam_endpoint}")
            return iam_endpoint
        
        # Заменяем /s3 на /iam в URL (например: https://example.com/s3 → https://example.com/iam)
        iam_endpoint = s3_endpoint.replace('/s3', '/iam').rstrip('/')
        if iam_endpoint != s3_endpoint:
            logger.info(f"Auto-generated IAM endpoint by replacing /s3: {s3_endpoint} → {iam_endpoint}")
            return iam_endpoint
        
        # Если ничего не изменилось, возвращаем None (IAM не поддерживается)
        logger.warning(f"Could not auto-generate IAM endpoint from S3 endpoint: {s3_endpoint}")
        return None
        
    except Exception as e:
        logger.warning(f"Error getting IAM endpoint: {e}", exc_info=True)
        return None


def get_iam_client(user_id: Optional[int] = None):
    """
    Получение IAM клиента для управления пользователями
    
    Args:
        user_id: ID пользователя
        
    Returns:
        boto3 IAM client
    """
    if not BOTO3_AVAILABLE:
        raise ImportError("boto3 is required for IAM operations")
    
    try:
        endpoint_url = get_s3_endpoint(user_id=user_id)
        access_key = get_aws_access_key_id(user_id=user_id)
        secret_key = get_aws_secret_access_key(user_id=user_id)
        
        # Получаем IAM endpoint (сначала из конфигурации, потом автоматически)
        iam_endpoint = get_iam_endpoint(user_id=user_id)
        
        if not iam_endpoint:
            raise ValueError("IAM endpoint could not be determined. Please specify IAM_ENDPOINT in configuration or ensure S3 endpoint supports IAM auto-detection.")
        
        # Очищаем endpoint от лишних слешей в конце
        iam_endpoint = iam_endpoint.rstrip('/')
        
        # Определяем SSL настройки из IAM endpoint
        use_ssl = iam_endpoint.startswith('https://') or ':443' in iam_endpoint
        
        try:
            iam_client = boto3.client(
                'iam',
                endpoint_url=iam_endpoint,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                use_ssl=use_ssl,
                region_name='us-east-1',
                verify=False  # Для самоподписанных сертификатов
            )
            
            logger.info(f"IAM client initialized with endpoint: {iam_endpoint}")
            return iam_client
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to create IAM client with endpoint {iam_endpoint}: {error_msg}")
            
            # Проверяем, является ли это ошибкой DNS/подключения
            if 'Name or service not known' in error_msg or 'gaierror' in error_msg.lower():
                raise ValueError(
                    f"IAM endpoint '{iam_endpoint}' cannot be resolved via DNS. "
                    f"QuantumActiveScale may not support AWS IAM API through boto3, "
                    f"or the IAM endpoint may be different. "
                    f"Please check your storage documentation or disable IAM functionality."
                )
            elif 'Could not connect' in error_msg or 'Connection' in error_msg:
                raise ValueError(
                    f"Could not connect to IAM endpoint '{iam_endpoint}'. "
                    f"IAM API may not be supported by your S3 storage, or the endpoint is incorrect. "
                    f"Error: {error_msg}"
                )
            else:
                raise ValueError(f"Could not initialize IAM client: {error_msg}")
    except Exception as e:
        logger.warning(f"Could not create IAM client (may not be supported): {e}")
        raise


def list_iam_users(user_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Получение списка IAM пользователей
    
    Args:
        user_id: ID пользователя
        
    Returns:
        Список пользователей с информацией
    """
    try:
        iam_client = get_iam_client(user_id=user_id)
        response = iam_client.list_users()
        
        users = []
        for user in response.get('Users', []):
            user_info = {
                'UserName': user.get('UserName'),
                'CreateDate': user.get('CreateDate').isoformat() if user.get('CreateDate') else None,
                'UserId': user.get('UserId'),
                'Path': user.get('Path', '/')
            }
            
            # Получаем количество ключей доступа
            try:
                keys_response = iam_client.list_access_keys(UserName=user.get('UserName'))
                user_info['AccessKeysCount'] = len(keys_response.get('AccessKeyMetadata', []))
            except Exception as e:
                logger.warning(f"Could not get access keys count for user {user.get('UserName')}: {e}")
                user_info['AccessKeysCount'] = 0
            
            users.append(user_info)
        
        return users
    except ValueError as e:
        # Пробрасываем ValueError как есть (уже с понятным сообщением)
        logger.error(f"IAM not supported: {e}")
        raise
    except Exception as e:
        logger.error(f"Error listing IAM users: {e}", exc_info=True)
        error_msg = str(e)
        
        # Проверяем специфичные ошибки подключения
        if 'Name or service not known' in error_msg or 'gaierror' in error_msg.lower():
            raise ValueError(
                f"IAM endpoint cannot be resolved via DNS. "
                f"QuantumActiveScale may not support AWS IAM API through boto3. "
                f"Please check your storage documentation or specify a valid IAM_ENDPOINT if available."
            )
        elif 'Could not connect' in error_msg or 'Connection' in error_msg:
            raise ValueError(
                f"Could not connect to IAM endpoint. "
                f"IAM API may not be supported by your S3 storage. "
                f"Original error: {error_msg}"
            )
        # Если IAM не поддерживается, возвращаем пустой список с информацией
        if "not supported" in error_msg.lower() or "cannot" in error_msg.lower():
            return []
        raise


def create_iam_user(user_name: str, create_access_key: bool = False, user_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Создание нового IAM пользователя
    
    Args:
        user_name: Имя пользователя
        create_access_key: Создать ключ доступа сразу
        user_id: ID пользователя
        
    Returns:
        Информация о созданном пользователе и ключе доступа (если создан)
    """
    try:
        iam_client = get_iam_client(user_id=user_id)
        
        # Создаем пользователя
        iam_client.create_user(UserName=user_name)
        
        result = {
            'UserName': user_name,
            'AccessKey': None
        }
        
        # Создаем ключ доступа, если требуется
        if create_access_key:
            key_response = iam_client.create_access_key(UserName=user_name)
            result['AccessKey'] = {
                'AccessKeyId': key_response['AccessKey']['AccessKeyId'],
                'SecretAccessKey': key_response['AccessKey']['SecretAccessKey'],
                'Status': key_response['AccessKey']['Status']
            }
        
        logger.info(f"IAM user {user_name} created successfully")
        return result
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'EntityAlreadyExists':
            raise ValueError(f"User {user_name} already exists")
        raise
    except Exception as e:
        logger.error(f"Error creating IAM user {user_name}: {e}", exc_info=True)
        raise


def delete_iam_user(user_name: str, user_id: Optional[int] = None) -> bool:
    """
    Удаление IAM пользователя
    
    Args:
        user_name: Имя пользователя
        user_id: ID пользователя
        
    Returns:
        True если успешно
    """
    try:
        iam_client = get_iam_client(user_id=user_id)
        
        # Удаляем все ключи доступа
        try:
            keys_response = iam_client.list_access_keys(UserName=user_name)
            for key in keys_response.get('AccessKeyMetadata', []):
                iam_client.delete_access_key(
                    UserName=user_name,
                    AccessKeyId=key['AccessKeyId']
                )
        except Exception as e:
            logger.warning(f"Could not delete access keys for user {user_name}: {e}")
        
        # Удаляем пользователя
        iam_client.delete_user(UserName=user_name)
        
        logger.info(f"IAM user {user_name} deleted successfully")
        return True
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'NoSuchEntity':
            raise ValueError(f"User {user_name} does not exist")
        raise
    except Exception as e:
        logger.error(f"Error deleting IAM user {user_name}: {e}", exc_info=True)
        raise


def list_user_access_keys(user_name: str, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Получение списка ключей доступа пользователя
    
    Args:
        user_name: Имя пользователя
        user_id: ID пользователя
        
    Returns:
        Список ключей доступа
    """
    try:
        iam_client = get_iam_client(user_id=user_id)
        response = iam_client.list_access_keys(UserName=user_name)
        
        keys = []
        for key in response.get('AccessKeyMetadata', []):
            keys.append({
                'AccessKeyId': key.get('AccessKeyId'),
                'Status': key.get('Status'),
                'CreateDate': key.get('CreateDate').isoformat() if key.get('CreateDate') else None
            })
        
        return keys
    except Exception as e:
        logger.error(f"Error listing access keys for user {user_name}: {e}", exc_info=True)
        raise


def create_access_key(user_name: str, user_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Создание нового ключа доступа для пользователя
    
    Args:
        user_name: Имя пользователя
        user_id: ID пользователя
        
    Returns:
        Информация о созданном ключе
    """
    try:
        iam_client = get_iam_client(user_id=user_id)
        response = iam_client.create_access_key(UserName=user_name)
        
        return {
            'AccessKeyId': response['AccessKey']['AccessKeyId'],
            'SecretAccessKey': response['AccessKey']['SecretAccessKey'],
            'Status': response['AccessKey']['Status']
        }
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'LimitExceeded':
            raise ValueError(f"User {user_name} has reached the maximum number of access keys (2)")
        raise
    except Exception as e:
        logger.error(f"Error creating access key for user {user_name}: {e}", exc_info=True)
        raise


def delete_access_key(user_name: str, access_key_id: str, user_id: Optional[int] = None) -> bool:
    """
    Удаление ключа доступа
    
    Args:
        user_name: Имя пользователя
        access_key_id: ID ключа доступа
        user_id: ID пользователя
        
    Returns:
        True если успешно
    """
    try:
        iam_client = get_iam_client(user_id=user_id)
        iam_client.delete_access_key(UserName=user_name, AccessKeyId=access_key_id)
        
        logger.info(f"Access key {access_key_id} deleted successfully")
        return True
    except Exception as e:
        logger.error(f"Error deleting access key {access_key_id}: {e}", exc_info=True)
        raise


