"""
Модуль конфигурации (слой обратной совместимости)

Этот модуль предоставляет обратную совместимость со старым API конфигурации.
Внутри используется новый ConfigManager для управления конфигурацией.
"""

from typing import Dict, Any
from app.models.stats import UploadStats

# Глобальная статистика загрузки
upload_stats = UploadStats()

# Импортируем функции из нового менеджера конфигурации
from app.utils.config_manager import (
    get_config,
    update_config,
    validate_environment,
    get_nfs_path,
    get_s3_endpoint,
    get_s3_bucket,
    get_aws_access_key_id,
    get_aws_secret_access_key,
    get_max_threads,
    get_backup_days,
    get_ext_tag_map,
    get_storage_class,
    get_enable_tape_storage,
    get_upload_retries,
    get_retry_delay,
    get_file_categories
)

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