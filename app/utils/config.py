import os
import json
import logging
from typing import Dict, Any
from app.models.stats import UploadStats

# Глобальная статистика загрузки
upload_stats = UploadStats()

# Файл для сохранения конфигурации
CONFIG_FILE = 'data/config.json'

# Логгер
logger = logging.getLogger(__name__)

def _ensure_config_dir():
    """Создает директорию для конфигурационного файла если не существует"""
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        logger.info(f"Ensured directory exists for: {CONFIG_FILE}")
    except Exception as e:
        logger.error(f"Error creating config directory: {e}")

def _load_config_from_file() -> Dict[str, Any]:
    """Загружает конфигурацию из файла - ВСЕГДА ЧИТАЕТ ИЗ ФАЙЛА"""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                logger.debug(f"Loaded config from file: {CONFIG_FILE}")
                return config
        else:
            logger.debug(f"Config file does not exist: {CONFIG_FILE}")
    except Exception as e:
        logger.error(f"Error loading config from file {CONFIG_FILE}: {e}")
    return {}

def _save_config_to_file(config: Dict[str, Any]):
    """Сохраняет конфигурацию в файл"""
    try:
        _ensure_config_dir()
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        logger.info(f"Configuration saved to file: {CONFIG_FILE}")
    except Exception as e:
        logger.error(f"Error saving config to file {CONFIG_FILE}: {e}")

def get_config() -> Dict[str, Any]:
    """Получение конфигурации - ВСЕГДА АКТУАЛЬНЫЕ ДАННЫЕ"""
    # Базовые значения по умолчанию
    default_config = {
        'NFS_PATH': '/mnt/backups',
        'S3_ENDPOINT': '',
        'S3_BUCKET': '',
        'S3_ACCESS_KEY': '',
        'S3_SECRET_KEY': '',
        'FILE_AGE_HOURS': '24',
        'MAX_THREADS': '5',
        'BACKUP_DAYS': '7',
        'STORAGE_CLASS': 'STANDARD',
        'ENABLE_TAPE_STORAGE': 'false',
        'UPLOAD_RETRIES': '3',
        'RETRY_DELAY': '5'
    }
    
    # Загружаем конфигурацию из файла (ВЫСШИЙ ПРИОРИТЕТ)
    file_config = _load_config_from_file()
    
    # Объединяем: файл > переменные окружения > значения по умолчанию
    config = default_config.copy()
    
    # Обновляем из переменных окружения (НИЗШИЙ ПРИОРИТЕТ)
    for key in default_config.keys():
        env_value = os.getenv(key)
        if env_value is not None:
            config[key] = env_value
    
    # Обновляем из файла (НАИВЫСШИЙ ПРИОРИТЕТ - перезаписывает env)
    config.update(file_config)
    
    logger.debug(f"Config loaded - file priority: {list(file_config.keys())}")
    return config

# Геттеры для конкретных настроек - ВСЕГДА ВЫЗЫВАЮТ get_config()
def get_nfs_path() -> str:
    return get_config()['NFS_PATH']

def get_s3_endpoint() -> str:
    return get_config()['S3_ENDPOINT']

def get_s3_bucket() -> str:
    return get_config()['S3_BUCKET']

def get_aws_access_key_id() -> str:
    return get_config()['S3_ACCESS_KEY']

def get_aws_secret_access_key() -> str:
    return get_config()['S3_SECRET_KEY']

def get_max_threads() -> int:
    return int(get_config()['MAX_THREADS'])

def get_backup_days() -> int:
    return int(get_config()['BACKUP_DAYS'])

def get_ext_tag_map() -> Dict[str, str]:
    return {
        '.vbk': 'full',
        '.vib': 'incremental',
        '.vbm': 'metadata',
        '.log': 'logs'
    }

def get_storage_class() -> str:
    return get_config()['STORAGE_CLASS']

def get_enable_tape_storage() -> bool:
    return get_config()['ENABLE_TAPE_STORAGE'].lower() == 'true'

def get_upload_retries() -> int:
    return int(get_config()['UPLOAD_RETRIES'])

def get_retry_delay() -> int:
    return int(get_config()['RETRY_DELAY'])

def validate_environment() -> bool:
    """Валидация переменных окружения"""
    config = get_config()
    required = ['NFS_PATH', 'S3_ENDPOINT', 'S3_BUCKET', 'S3_ACCESS_KEY', 'S3_SECRET_KEY']
    
    for key in required:
        if not config.get(key):
            raise Exception(f"Missing required configuration: {key}")
    
    if not os.path.exists(config['NFS_PATH']):
        raise Exception(f"NFS path does not exist: {config['NFS_PATH']}")
    
    return True

def update_config(new_config: Dict[str, Any]) -> None:
    """Обновление конфигурации (для веб-интерфейса)"""
    logger.info(f"Updating configuration with keys: {list(new_config.keys())}")
    
    # Загружаем текущую конфигурацию из файла
    current_config = _load_config_from_file()
    
    # Обновляем только переданные поля
    updated_keys = []
    for key, value in new_config.items():
        if value is not None and value != '':
            current_config[key] = str(value)
            updated_keys.append(key)
    
    logger.info(f"Updated config keys: {updated_keys}")
    
    # Сохраняем в файл
    _save_config_to_file(current_config)
    
    # НЕ обновляем переменные окружения - чтобы файл конфигурации имел приоритет
    logger.info("Configuration update completed - FILE configuration has priority")