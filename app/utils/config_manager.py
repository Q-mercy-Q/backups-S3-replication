"""
Менеджер конфигурации приложения
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field
from pathlib import Path


logger = logging.getLogger(__name__)


@dataclass
class AppConfig:
    """Класс конфигурации приложения"""
    
    # Пути и подключения
    nfs_path: str = '/mnt/backups'
    s3_endpoint: str = ''
    s3_bucket: str = ''
    s3_access_key: str = ''
    s3_secret_key: str = ''
    
    # Настройки загрузки
    file_age_hours: int = 24
    max_threads: int = 5
    backup_days: int = 7
    storage_class: str = 'STANDARD'
    enable_tape_storage: bool = False
    upload_retries: int = 3
    retry_delay: int = 5
    file_categories: List[str] = field(default_factory=lambda: ['full', 'incremental', 'metadata', 'logs'])
    
    # Маппинг расширений файлов
    ext_tag_map: Dict[str, str] = field(default_factory=lambda: {
        '.vbk': 'full',
        '.vib': 'incremental',
        '.vbm': 'metadata',
        '.log': 'logs'
    })
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AppConfig':
        """Создание конфигурации из словаря"""
        # Конвертируем строковые значения в нужные типы
        config_data = {}
        
        # Пути и подключения
        config_data['nfs_path'] = data.get('NFS_PATH', cls.__dataclass_fields__['nfs_path'].default)
        config_data['s3_endpoint'] = data.get('S3_ENDPOINT', cls.__dataclass_fields__['s3_endpoint'].default)
        config_data['s3_bucket'] = data.get('S3_BUCKET', cls.__dataclass_fields__['s3_bucket'].default)
        config_data['s3_access_key'] = data.get('S3_ACCESS_KEY', cls.__dataclass_fields__['s3_access_key'].default)
        config_data['s3_secret_key'] = data.get('S3_SECRET_KEY', cls.__dataclass_fields__['s3_secret_key'].default)
        
        # Настройки загрузки
        config_data['file_age_hours'] = int(data.get('FILE_AGE_HOURS', cls.__dataclass_fields__['file_age_hours'].default))
        config_data['max_threads'] = int(data.get('MAX_THREADS', cls.__dataclass_fields__['max_threads'].default))
        config_data['backup_days'] = int(data.get('BACKUP_DAYS', cls.__dataclass_fields__['backup_days'].default))
        config_data['storage_class'] = data.get('STORAGE_CLASS', cls.__dataclass_fields__['storage_class'].default)
        config_data['enable_tape_storage'] = data.get('ENABLE_TAPE_STORAGE', 'false').lower() == 'true'
        config_data['upload_retries'] = int(data.get('UPLOAD_RETRIES', cls.__dataclass_fields__['upload_retries'].default))
        config_data['retry_delay'] = int(data.get('RETRY_DELAY', cls.__dataclass_fields__['retry_delay'].default))
        
        file_categories = data.get('FILE_CATEGORIES')
        if isinstance(file_categories, str):
            file_categories = [item.strip() for item in file_categories.split(',') if item.strip()]
        elif not isinstance(file_categories, list):
            file_categories = cls.__dataclass_fields__['file_categories'].default_factory()

        config_data['file_categories'] = file_categories

        return cls(**config_data)
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертация в словарь"""
        return {
            'NFS_PATH': self.nfs_path,
            'S3_ENDPOINT': self.s3_endpoint,
            'S3_BUCKET': self.s3_bucket,
            'S3_ACCESS_KEY': self.s3_access_key,
            'S3_SECRET_KEY': self.s3_secret_key,
            'FILE_AGE_HOURS': str(self.file_age_hours),
            'MAX_THREADS': str(self.max_threads),
            'BACKUP_DAYS': str(self.backup_days),
            'STORAGE_CLASS': self.storage_class,
            'ENABLE_TAPE_STORAGE': 'true' if self.enable_tape_storage else 'false',
            'UPLOAD_RETRIES': str(self.upload_retries),
            'RETRY_DELAY': str(self.retry_delay),
            'FILE_CATEGORIES': self.file_categories
        }
    
    def validate(self) -> None:
        """Валидация конфигурации"""
        required_fields = {
            'NFS_PATH': self.nfs_path,
            'S3_ENDPOINT': self.s3_endpoint,
            'S3_BUCKET': self.s3_bucket,
            'S3_ACCESS_KEY': self.s3_access_key,
            'S3_SECRET_KEY': self.s3_secret_key
        }
        
        missing = [key for key, value in required_fields.items() if not value]
        if missing:
            raise ValueError(f"Missing required configuration fields: {', '.join(missing)}")
        
        if not os.path.exists(self.nfs_path):
            raise ValueError(f"NFS path does not exist: {self.nfs_path}")


class ConfigManager:
    """
    Менеджер конфигурации с поддержкой файлов и переменных окружения
    
    ⚠️ УСТАРЕВШИЙ КОД: Этот класс больше не используется для пользовательских конфигураций.
    Все пользовательские конфигурации теперь хранятся в БД через app.utils.user_config.
    Этот класс оставлен только для обратной совместимости и может быть удален в будущем.
    """
    
    def __init__(self, config_file: str = 'data/config.json'):
        self.config_file = Path(config_file)
        self._config: Optional[AppConfig] = None
    
    def _ensure_config_dir(self) -> None:
        """Создает директорию для конфигурационного файла если не существует"""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Ensured directory exists for: {self.config_file}")
        except Exception as e:
            logger.error(f"Error creating config directory: {e}")
    
    def _load_from_file(self) -> Dict[str, Any]:
        """Загружает конфигурацию из файла"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    logger.debug(f"Loaded config from file: {self.config_file}")
                    return config
            else:
                logger.debug(f"Config file does not exist: {self.config_file}")
        except Exception as e:
            logger.error(f"Error loading config from file {self.config_file}: {e}")
        return {}
    
    def _save_to_file(self, config: Dict[str, Any]) -> None:
        """Сохраняет конфигурацию в файл"""
        try:
            self._ensure_config_dir()
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            logger.info(f"Configuration saved to file: {self.config_file}")
        except Exception as e:
            logger.error(f"Error saving config to file {self.config_file}: {e}")
    
    def _load_from_env(self) -> Dict[str, Any]:
        """Загружает конфигурацию из переменных окружения"""
        env_config = {}
        env_keys = [
            'NFS_PATH', 'S3_ENDPOINT', 'S3_BUCKET', 'S3_ACCESS_KEY', 'S3_SECRET_KEY',
            'FILE_AGE_HOURS', 'MAX_THREADS', 'BACKUP_DAYS', 'STORAGE_CLASS',
            'ENABLE_TAPE_STORAGE', 'UPLOAD_RETRIES', 'RETRY_DELAY'
        ]
        
        for key in env_keys:
            value = os.getenv(key)
            if value is not None:
                env_config[key] = value
        
        return env_config
    
    def get_config(self) -> AppConfig:
        """
        Получение конфигурации с приоритетом: файл > переменные окружения > значения по умолчанию
        
        Returns:
            Объект конфигурации AppConfig
        """
        # Загружаем из файла (наивысший приоритет)
        file_config = self._load_from_file()
        
        # Загружаем из переменных окружения
        env_config = self._load_from_env()
        
        # Создаем конфигурацию по умолчанию
        default_config = AppConfig()
        default_dict = default_config.to_dict()
        
        # Объединяем: env > default
        merged_config = {**default_dict, **env_config}
        
        # Объединяем: file > env > default (файл имеет наивысший приоритет)
        merged_config.update(file_config)
        
        self._config = AppConfig.from_dict(merged_config)
        return self._config
    
    def update_config(self, new_config: Dict[str, Any]) -> None:
        """
        Обновление конфигурации
        
        Args:
            new_config: Словарь с новыми значениями конфигурации
        """
        logger.info(f"Updating configuration with keys: {list(new_config.keys())}")
        
        # Загружаем текущую конфигурацию из файла
        current_config = self._load_from_file()
        
        # Обновляем только переданные поля
        updated_keys = []
        for key, value in new_config.items():
            if value is None or value == '':
                continue

            if key == 'FILE_CATEGORIES':
                normalized = self._normalize_categories(value)
                current_config[key] = normalized
                updated_keys.append(key)
                continue

            current_config[key] = str(value)
            updated_keys.append(key)
        
        logger.info(f"Updated config keys: {updated_keys}")
        
        # Сохраняем в файл
        self._save_to_file(current_config)
        
        # Сбрасываем кэш конфигурации
        self._config = None
        
        logger.info("Configuration update completed - FILE configuration has priority")

    def _normalize_categories(self, value: Union[str, List[str]]) -> List[str]:
        """Normalize category input to list of strings."""
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            return [item.strip() for item in value.split(',') if item.strip()]
        return AppConfig.__dataclass_fields__['file_categories'].default_factory()
    
    def validate(self) -> bool:
        """Валидация текущей конфигурации"""
        try:
            config = self.get_config()
            config.validate()
            return True
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            raise


# Глобальный экземпляр менеджера конфигурации
# ⚠️ УСТАРЕВШИЙ КОД: Не используется для пользовательских конфигураций.
# Все конфигурации пользователей хранятся в БД через app.utils.user_config
_config_manager = ConfigManager()


def get_config() -> Dict[str, Any]:
    """Получение конфигурации в виде словаря (для обратной совместимости)"""
    return _config_manager.get_config().to_dict()


def get_config_object() -> AppConfig:
    """Получение объекта конфигурации"""
    return _config_manager.get_config()


def update_config(new_config: Dict[str, Any]) -> None:
    """
    Обновление конфигурации (для обратной совместимости)
    
    ⚠️ УСТАРЕВШАЯ ФУНКЦИЯ: Эта функция пишет в файл и больше не должна использоваться!
    Для пользовательских конфигураций используйте app.utils.config.update_config()
    или app.utils.user_config.save_user_config() для работы с БД.
    """
    logger.warning("⚠️ DEPRECATED: config_manager.update_config() writes to file. Use app.utils.config.update_config() for database storage.")
    _config_manager.update_config(new_config)


def validate_environment() -> bool:
    """Валидация окружения (для обратной совместимости)"""
    return _config_manager.validate()


# Геттеры для обратной совместимости
def get_nfs_path() -> str:
    return _config_manager.get_config().nfs_path


def get_s3_endpoint() -> str:
    return _config_manager.get_config().s3_endpoint


def get_s3_bucket() -> str:
    return _config_manager.get_config().s3_bucket


def get_aws_access_key_id() -> str:
    return _config_manager.get_config().s3_access_key


def get_aws_secret_access_key() -> str:
    return _config_manager.get_config().s3_secret_key


def get_max_threads() -> int:
    return _config_manager.get_config().max_threads


def get_backup_days() -> int:
    return _config_manager.get_config().backup_days


def get_ext_tag_map() -> Dict[str, str]:
    return _config_manager.get_config().ext_tag_map


def get_storage_class() -> str:
    return _config_manager.get_config().storage_class


def get_enable_tape_storage() -> bool:
    return _config_manager.get_config().enable_tape_storage


def get_upload_retries() -> int:
    return _config_manager.get_config().upload_retries


def get_retry_delay() -> int:
    return _config_manager.get_config().retry_delay


def get_file_categories() -> List[str]:
    return _config_manager.get_config().file_categories

