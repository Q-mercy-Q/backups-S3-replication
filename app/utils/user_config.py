"""
Модуль для работы с персональными конфигурациями пользователей
Поддерживает несколько конфигураций на пользователя
"""

import json
import logging
from typing import Dict, Any, Optional, List
from flask_login import current_user

from app.db import session_scope
from app.models.db_models import UserConfig
from app.utils.config_manager import AppConfig

logger = logging.getLogger(__name__)


def get_user_config(user_id: Optional[int] = None, config_id: Optional[int] = None, config_name: Optional[str] = None) -> Optional[AppConfig]:
    """
    Получить конфигурацию пользователя
    
    Args:
        user_id: ID пользователя (если None, используется current_user)
        config_id: ID конфигурации (если указан, загружается этот конфиг)
        config_name: Название конфигурации (если указано, загружается конфиг с этим именем)
        
    Returns:
        AppConfig объект или None если конфигурация не найдена
    """
    if user_id is None:
        if not current_user.is_authenticated:
            return None
        user_id = current_user.id
    
    with session_scope() as session:
        query = session.query(UserConfig).filter(UserConfig.user_id == user_id)
        
        # Если указан config_id или config_name, загружаем конкретный конфиг
        if config_id:
            user_config = query.filter(UserConfig.id == config_id).first()
        elif config_name:
            user_config = query.filter(UserConfig.name == config_name).first()
        else:
            # Иначе загружаем конфиг по умолчанию
            user_config = query.filter(UserConfig.is_default == True).first()
            # Если конфига по умолчанию нет, берем первый доступный
            if not user_config:
                user_config = query.first()
        
        if not user_config:
            return None
        
        # Преобразуем UserConfig в AppConfig
        config_data = {
            'NFS_PATH': user_config.nfs_path,
            'S3_ENDPOINT': user_config.s3_endpoint,
            'S3_BUCKET': user_config.s3_bucket,
            'S3_ACCESS_KEY': user_config.s3_access_key,
            'S3_SECRET_KEY': user_config.s3_secret_key,
            'FILE_AGE_HOURS': str(user_config.file_age_hours),
            'MAX_THREADS': str(user_config.max_threads),
            'BACKUP_DAYS': str(user_config.backup_days),
            'STORAGE_CLASS': user_config.storage_class,
            'ENABLE_TAPE_STORAGE': 'true' if user_config.enable_tape_storage else 'false',
            'UPLOAD_RETRIES': str(user_config.upload_retries),
            'RETRY_DELAY': str(user_config.retry_delay),
        }
        
        # Парсим JSON поля
        if user_config.file_categories:
            try:
                config_data['FILE_CATEGORIES'] = json.loads(user_config.file_categories)
            except (json.JSONDecodeError, TypeError):
                config_data['FILE_CATEGORIES'] = ['full', 'incremental', 'metadata', 'logs']
        else:
            config_data['FILE_CATEGORIES'] = ['full', 'incremental', 'metadata', 'logs']
        
        if user_config.ext_tag_map:
            try:
                config_data['EXT_TAG_MAP'] = json.loads(user_config.ext_tag_map)
            except (json.JSONDecodeError, TypeError):
                config_data['EXT_TAG_MAP'] = {
                    '.vbk': 'full',
                    '.vib': 'incremental',
                    '.vbm': 'metadata',
                    '.log': 'logs'
                }
        else:
            config_data['EXT_TAG_MAP'] = {
                '.vbk': 'full',
                '.vib': 'incremental',
                '.vbm': 'metadata',
                '.log': 'logs'
            }
        
        return AppConfig.from_dict(config_data)


def list_user_configs(user_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Получить список всех конфигураций пользователя
    
    Args:
        user_id: ID пользователя (если None, используется current_user)
        
    Returns:
        Список словарей с информацией о конфигурациях
    """
    if user_id is None:
        if not current_user.is_authenticated:
            return []
        user_id = current_user.id
    
    with session_scope() as session:
        configs = session.query(UserConfig).filter(
            UserConfig.user_id == user_id
        ).order_by(UserConfig.is_default.desc(), UserConfig.name).all()
        
        result = []
        for config in configs:
            result.append({
                'id': config.id,
                'name': config.name,
                'is_default': config.is_default,
                'created_at': config.created_at.isoformat() if config.created_at else None,
                'updated_at': config.updated_at.isoformat() if config.updated_at else None,
            })
        
        return result


def create_user_config(name: str, config: Dict[str, Any], user_id: Optional[int] = None, is_default: bool = False) -> UserConfig:
    """
    Создать новую конфигурацию пользователя
    
    Args:
        name: Название конфигурации
        config: Словарь с конфигурацией
        user_id: ID пользователя (если None, используется current_user)
        is_default: Сделать конфигурацию конфигурацией по умолчанию
        
    Returns:
        UserConfig объект
    """
    if user_id is None:
        if not current_user.is_authenticated:
            raise ValueError("User must be authenticated to create config")
        user_id = current_user.id
    
    with session_scope() as session:
        # Проверяем, существует ли конфиг с таким именем
        existing = session.query(UserConfig).filter(
            UserConfig.user_id == user_id,
            UserConfig.name == name
        ).first()
        
        if existing:
            raise ValueError(f"Configuration with name '{name}' already exists")
        
        # Если делаем конфиг по умолчанию, снимаем флаг с других конфигов
        if is_default:
            session.query(UserConfig).filter(
                UserConfig.user_id == user_id,
                UserConfig.is_default == True
            ).update({UserConfig.is_default: False})
        
        # Создаем новую конфигурацию
        user_config = UserConfig(
            user_id=user_id,
            name=name,
            is_default=is_default or (session.query(UserConfig).filter(UserConfig.user_id == user_id).count() == 0),
            nfs_path=config.get('NFS_PATH', '/mnt/backups'),
            s3_endpoint=config.get('S3_ENDPOINT', ''),
            s3_bucket=config.get('S3_BUCKET', ''),
            s3_access_key=config.get('S3_ACCESS_KEY', ''),
            s3_secret_key=config.get('S3_SECRET_KEY', ''),
            file_age_hours=int(config.get('FILE_AGE_HOURS', 24)),
            max_threads=int(config.get('MAX_THREADS', 5)),
            backup_days=int(config.get('BACKUP_DAYS', 7)),
            storage_class=config.get('STORAGE_CLASS', 'STANDARD'),
            enable_tape_storage=config.get('ENABLE_TAPE_STORAGE', 'false').lower() == 'true',
            upload_retries=int(config.get('UPLOAD_RETRIES', 3)),
            retry_delay=int(config.get('RETRY_DELAY', 5)),
        )
        
        # JSON поля
        file_categories = config.get('FILE_CATEGORIES', [])
        if isinstance(file_categories, list):
            user_config.file_categories = json.dumps(file_categories)
        else:
            user_config.file_categories = json.dumps(['full', 'incremental', 'metadata', 'logs'])
        
        ext_tag_map = config.get('EXT_TAG_MAP')
        if isinstance(ext_tag_map, dict):
            user_config.ext_tag_map = json.dumps(ext_tag_map)
        else:
            user_config.ext_tag_map = json.dumps({
                '.vbk': 'full',
                '.vib': 'incremental',
                '.vbm': 'metadata',
                '.log': 'logs'
            })
        
        session.add(user_config)
        session.flush()
        
        logger.info(f"Created user config '{name}' for user_id={user_id}")
        
        # Очищаем кэш MinIO клиента
        try:
            from app.services.s3_client import clear_minio_client_cache
            clear_minio_client_cache(user_id=user_id)
        except Exception as e:
            logger.warning(f"Failed to clear MinIO client cache: {e}")
        
        return user_config


def save_user_config(config: Dict[str, Any], user_id: Optional[int] = None, config_id: Optional[int] = None, config_name: Optional[str] = None) -> UserConfig:
    """
    Сохранить конфигурацию пользователя
    
    Args:
        config: Словарь с конфигурацией
        user_id: ID пользователя (если None, используется current_user)
        config_id: ID конфигурации для обновления (если None, обновляется конфиг по умолчанию)
        config_name: Название конфигурации для обновления (если указано, используется вместо config_id)
        
    Returns:
        UserConfig объект
    """
    if user_id is None:
        if not current_user.is_authenticated:
            raise ValueError("User must be authenticated to save config")
        user_id = current_user.id
    
    with session_scope() as session:
        query = session.query(UserConfig).filter(UserConfig.user_id == user_id)
        
        # Определяем какой конфиг обновлять
        if config_id:
            user_config = query.filter(UserConfig.id == config_id).first()
        elif config_name:
            user_config = query.filter(UserConfig.name == config_name).first()
        else:
            # Обновляем конфиг по умолчанию
            user_config = query.filter(UserConfig.is_default == True).first()
            if not user_config:
                # Если конфига по умолчанию нет, создаем новый
                user_config = UserConfig(user_id=user_id, name='Default', is_default=True)
                session.add(user_config)
        
        if not user_config:
            raise ValueError("Configuration not found")
        
        # Обновляем поля ТОЛЬКО если они переданы в config
        if 'NFS_PATH' in config:
            user_config.nfs_path = config.get('NFS_PATH', '/mnt/backups')
        if 'S3_ENDPOINT' in config:
            user_config.s3_endpoint = config.get('S3_ENDPOINT', '')
        if 'S3_BUCKET' in config:
            user_config.s3_bucket = config.get('S3_BUCKET', '')
        
        # S3 credentials: сохраняем только если ключи присутствуют в config
        if 'S3_ACCESS_KEY' in config:
            s3_access_key = config.get('S3_ACCESS_KEY', '')
            user_config.s3_access_key = s3_access_key if s3_access_key is not None else ''
        if 'S3_SECRET_KEY' in config:
            s3_secret_key = config.get('S3_SECRET_KEY', '')
            user_config.s3_secret_key = s3_secret_key if s3_secret_key is not None else ''
        
        # Обновляем остальные поля только если они переданы
        if 'FILE_AGE_HOURS' in config:
            user_config.file_age_hours = int(config.get('FILE_AGE_HOURS', 24))
        if 'MAX_THREADS' in config:
            user_config.max_threads = int(config.get('MAX_THREADS', 5))
        if 'BACKUP_DAYS' in config:
            user_config.backup_days = int(config.get('BACKUP_DAYS', 7))
        if 'STORAGE_CLASS' in config:
            user_config.storage_class = config.get('STORAGE_CLASS', 'STANDARD')
        if 'ENABLE_TAPE_STORAGE' in config:
            user_config.enable_tape_storage = config.get('ENABLE_TAPE_STORAGE', 'false').lower() == 'true'
        if 'UPLOAD_RETRIES' in config:
            user_config.upload_retries = int(config.get('UPLOAD_RETRIES', 3))
        if 'RETRY_DELAY' in config:
            user_config.retry_delay = int(config.get('RETRY_DELAY', 5))
        
        # Сохраняем JSON поля только если они переданы
        if 'FILE_CATEGORIES' in config:
            file_categories = config.get('FILE_CATEGORIES', [])
            if isinstance(file_categories, list):
                user_config.file_categories = json.dumps(file_categories)
            else:
                user_config.file_categories = json.dumps(['full', 'incremental', 'metadata', 'logs'])
        
        # Сохраняем маппинг расширений
        if 'EXT_TAG_MAP' in config:
            ext_tag_map = config.get('EXT_TAG_MAP')
            if ext_tag_map is not None and isinstance(ext_tag_map, dict):
                user_config.ext_tag_map = json.dumps(ext_tag_map)
            elif ext_tag_map is None:
                pass  # Не меняем существующее значение
            else:
                default_map = {
                    '.vbk': 'full',
                    '.vib': 'incremental',
                    '.vbm': 'metadata',
                    '.log': 'logs'
                }
                user_config.ext_tag_map = json.dumps(default_map)
        
        # Обновляем название конфига, если указано
        if 'CONFIG_NAME' in config:
            new_name = config.get('CONFIG_NAME', '').strip()
            if new_name and new_name != user_config.name:
                # Проверяем уникальность имени
                existing = session.query(UserConfig).filter(
                    UserConfig.user_id == user_id,
                    UserConfig.name == new_name,
                    UserConfig.id != user_config.id
                ).first()
                if existing:
                    raise ValueError(f"Configuration with name '{new_name}' already exists")
                user_config.name = new_name
        
        # Обновляем updated_at
        from datetime import datetime
        user_config.updated_at = datetime.utcnow()
        
        session.flush()
        logger.info(f"User config '{user_config.name}' (id={user_config.id}) saved for user_id={user_id}")
        
        # Очищаем кэш MinIO клиента
        try:
            from app.services.s3_client import clear_minio_client_cache
            clear_minio_client_cache(user_id=user_id)
        except Exception as e:
            logger.warning(f"Failed to clear MinIO client cache: {e}")
        
        return user_config


def delete_user_config(config_id: Optional[int] = None, config_name: Optional[str] = None, user_id: Optional[int] = None) -> bool:
    """
    Удалить конфигурацию пользователя
    
    Args:
        config_id: ID конфигурации для удаления
        config_name: Название конфигурации для удаления
        user_id: ID пользователя (если None, используется current_user)
        
    Returns:
        True если конфигурация была удалена, False если не найдена
    """
    if user_id is None:
        if not current_user.is_authenticated:
            return False
        user_id = current_user.id
    
    with session_scope() as session:
        query = session.query(UserConfig).filter(UserConfig.user_id == user_id)
        
        if config_id:
            user_config = query.filter(UserConfig.id == config_id).first()
        elif config_name:
            user_config = query.filter(UserConfig.name == config_name).first()
        else:
            # Нельзя удалить без указания конкретного конфига
            raise ValueError("Must specify config_id or config_name to delete")
        
        if user_config:
            # Нельзя удалить конфиг, если он единственный
            count = session.query(UserConfig).filter(UserConfig.user_id == user_id).count()
            if count <= 1:
                raise ValueError("Cannot delete the last remaining configuration")
            
            # Если удаляем конфиг по умолчанию, делаем дефолтным первый доступный
            if user_config.is_default:
                other_config = session.query(UserConfig).filter(
                    UserConfig.user_id == user_id,
                    UserConfig.id != user_config.id
                ).first()
                if other_config:
                    other_config.is_default = True
            
            session.delete(user_config)
            logger.info(f"Deleted user config '{user_config.name}' (id={user_config.id}) for user_id={user_id}")
            return True
        
        return False


def set_default_config(config_id: Optional[int] = None, config_name: Optional[str] = None, user_id: Optional[int] = None) -> bool:
    """
    Установить конфигурацию по умолчанию
    
    Args:
        config_id: ID конфигурации
        config_name: Название конфигурации
        user_id: ID пользователя (если None, используется current_user)
        
    Returns:
        True если операция успешна, False если конфигурация не найдена
    """
    if user_id is None:
        if not current_user.is_authenticated:
            return False
        user_id = current_user.id
    
    with session_scope() as session:
        query = session.query(UserConfig).filter(UserConfig.user_id == user_id)
        
        if config_id:
            user_config = query.filter(UserConfig.id == config_id).first()
        elif config_name:
            user_config = query.filter(UserConfig.name == config_name).first()
        else:
            return False
        
        if not user_config:
            return False
        
        # Снимаем флаг is_default со всех конфигов пользователя
        session.query(UserConfig).filter(
            UserConfig.user_id == user_id,
            UserConfig.is_default == True
        ).update({UserConfig.is_default: False})
        
        # Устанавливаем флаг для выбранного конфига
        user_config.is_default = True
        session.flush()
        
        logger.info(f"Set default config '{user_config.name}' (id={user_config.id}) for user_id={user_id}")
        return True


def get_user_id_from_config_id(config_id: int) -> Optional[int]:
    """
    Получить user_id по config_id
    
    Args:
        config_id: ID конфигурации
        
    Returns:
        user_id или None если конфигурация не найдена
    """
    with session_scope() as session:
        user_config = session.query(UserConfig).filter(
            UserConfig.id == config_id
        ).first()
        
        if user_config:
            return user_config.user_id
        
        return None
