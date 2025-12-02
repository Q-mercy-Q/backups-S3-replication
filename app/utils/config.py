"""
Модуль конфигурации (слой обратной совместимости)

Этот модуль предоставляет обратную совместимость со старым API конфигурации.
Теперь использует персональные конфигурации пользователей.
"""

from typing import Dict, Any, Optional
from flask_login import current_user

from app.models.stats import UploadStats
from app.utils.user_config import get_user_config, save_user_config
from app.utils.config_manager import AppConfig

# Глобальная статистика загрузки
upload_stats = UploadStats()


def get_config(user_id: Optional[int] = None, config_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Получить конфигурацию пользователя в виде словаря
    
    Args:
        user_id: ID пользователя (если None и есть контекст Flask, используется current_user)
        config_id: ID конкретной конфигурации (если None, используется конфиг по умолчанию)
    
    Returns:
        Словарь с конфигурацией
    """
    # Пытаемся получить конфигурацию пользователя
    user_config = None
    
    if user_id is not None:
        user_config = get_user_config(user_id=user_id, config_id=config_id)
    elif hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
        user_config = get_user_config(user_id=current_user.id, config_id=config_id)
    
    if user_config:
        return user_config.to_dict()
    
    # Если конфигурации нет, возвращаем дефолтную
    default_config = AppConfig()
    return default_config.to_dict()


def update_config(new_config: Dict[str, Any], user_id: Optional[int] = None) -> None:
    """
    Обновить конфигурацию пользователя
    
    Args:
        new_config: Словарь с новой конфигурацией
        user_id: ID пользователя (если None и есть контекст Flask, используется current_user)
    """
    target_user_id = user_id
    if target_user_id is None and hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
        target_user_id = current_user.id
    
    if target_user_id is None:
        raise ValueError("User ID is required to update config")
    
    save_user_config(new_config, user_id=target_user_id)


# Геттеры для обратной совместимости
def get_nfs_path(user_id: Optional[int] = None) -> str:
    config = get_config(user_id=user_id)
    return config.get('NFS_PATH', '/mnt/backups')


def get_s3_endpoint(user_id: Optional[int] = None) -> str:
    config = get_config(user_id=user_id)
    return config.get('S3_ENDPOINT', '')


def get_s3_bucket(user_id: Optional[int] = None) -> str:
    config = get_config(user_id=user_id)
    return config.get('S3_BUCKET', '')


def get_aws_access_key_id(user_id: Optional[int] = None) -> str:
    config = get_config(user_id=user_id)
    return config.get('S3_ACCESS_KEY', '')


def get_aws_secret_access_key(user_id: Optional[int] = None) -> str:
    config = get_config(user_id=user_id)
    return config.get('S3_SECRET_KEY', '')


def get_max_threads(user_id: Optional[int] = None) -> int:
    config = get_config(user_id=user_id)
    return int(config.get('MAX_THREADS', 5))


def get_backup_days(user_id: Optional[int] = None) -> int:
    config = get_config(user_id=user_id)
    return int(config.get('BACKUP_DAYS', 7))


def get_ext_tag_map(user_id: Optional[int] = None) -> Dict[str, str]:
    config = get_config(user_id=user_id)
    ext_map = config.get('EXT_TAG_MAP', {})
    if not ext_map:
        # Дефолтный маппинг
        return {
            '.vbk': 'full',
            '.vib': 'incremental',
            '.vbm': 'metadata',
            '.log': 'logs'
        }
    return ext_map


def get_storage_class(user_id: Optional[int] = None) -> str:
    config = get_config(user_id=user_id)
    return config.get('STORAGE_CLASS', 'STANDARD')


def get_enable_tape_storage(user_id: Optional[int] = None) -> bool:
    config = get_config(user_id=user_id)
    return config.get('ENABLE_TAPE_STORAGE', 'false').lower() == 'true'


def get_upload_retries(user_id: Optional[int] = None) -> int:
    config = get_config(user_id=user_id)
    return int(config.get('UPLOAD_RETRIES', 3))


def get_retry_delay(user_id: Optional[int] = None) -> int:
    config = get_config(user_id=user_id)
    return int(config.get('RETRY_DELAY', 5))


def get_file_categories(user_id: Optional[int] = None, config_id: Optional[int] = None) -> list:
    config = get_config(user_id=user_id, config_id=config_id)
    categories = config.get('FILE_CATEGORIES', [])
    if isinstance(categories, list):
        return categories
    return ['full', 'incremental', 'metadata', 'logs']


def validate_environment(user_id: Optional[int] = None) -> bool:
    """Валидация конфигурации"""
    try:
        config = get_config(user_id=user_id)
        app_config = AppConfig.from_dict(config)
        app_config.validate()
        return True
    except Exception:
        return False


# Экспортируем все для обратной совместимости
__all__ = [
    'upload_stats',
    'get_config',
    'update_config',
    'validate_environment',
    'get_nfs_path',
    'get_s3_endpoint',
    'get_s3_bucket',
    'get_aws_access_key_id',
    'get_aws_secret_access_key',
    'get_max_threads',
    'get_backup_days',
    'get_ext_tag_map',
    'get_storage_class',
    'get_enable_tape_storage',
    'get_upload_retries',
    'get_retry_delay',
    'get_file_categories'
]