"""
Сервис для просмотра и навигации по S3 бакету
"""

import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from urllib.parse import unquote

from minio.error import S3Error

from app.services.s3_client import get_minio_client
from app.utils.config import get_s3_bucket

logger = logging.getLogger(__name__)


def list_bucket_objects(prefix: str = "", recursive: bool = False, user_id: Optional[int] = None) -> List[Dict]:
    """
    Получение списка объектов в S3 бакете
    
    Args:
        prefix: Префикс пути (папка) для фильтрации объектов
        recursive: Если True, возвращает все объекты рекурсивно, иначе только текущий уровень
        user_id: ID пользователя (для использования его конфигурации)
    
    Returns:
        Список словарей с информацией об объектах
    """
    objects = []
    folders = set()
    
    try:
        minio_client = get_minio_client(user_id=user_id)
        bucket_name = get_s3_bucket(user_id=user_id)
        
        # Нормализуем prefix
        normalized_prefix = prefix.rstrip('/') + '/' if prefix else ''
        
        # Получаем объекты
        try:
            for obj in minio_client.list_objects(
                bucket_name,
                prefix=normalized_prefix if normalized_prefix else None,
                recursive=recursive
            ):
                # Пропускаем сам префикс, если это "файл"
                if obj.object_name == normalized_prefix or obj.object_name == prefix:
                    continue
                
                # Извлекаем относительный путь
                if normalized_prefix:
                    relative_path = obj.object_name[len(normalized_prefix):]
                else:
                    relative_path = obj.object_name
                
                # Если это папка (заканчивается на /)
                if obj.is_dir or relative_path.endswith('/'):
                    folder_name = relative_path.rstrip('/').split('/')[0]
                    if folder_name:
                        folder_path = normalized_prefix + folder_name
                        if folder_path not in folders:
                            folders.add(folder_path)
                            # Вычисляем статистику для директории (синхронно для надежности)
                            try:
                                dir_stats = _get_directory_stats_fast(folder_path + '/', minio_client, bucket_name)
                                # Убеждаемся, что все поля заполнены
                                objects.append({
                                    'name': folder_name,
                                    'path': folder_path,
                                    'type': 'directory',
                                    'size': dir_stats.get('total_size') or 0,
                                    'size_human': dir_stats.get('total_size_human') or '0 B',
                                    'file_count': dir_stats.get('file_count') or 0,
                                    'modified': dir_stats.get('last_modified'),
                                    'storage_class': dir_stats.get('storage_class')
                                })
                            except Exception as e:
                                logger.error(f"Failed to calculate stats for directory {folder_path}: {e}", exc_info=True)
                                # Добавляем директорию с пустой статистикой при ошибке
                                objects.append({
                                    'name': folder_name,
                                    'path': folder_path,
                                    'type': 'directory',
                                    'size': 0,
                                    'size_human': '0 B',
                                    'file_count': 0,
                                    'modified': None,
                                    'storage_class': None
                                })
                else:
                    # Это файл
                    file_name = relative_path.split('/')[-1] if '/' in relative_path else relative_path
                    objects.append({
                        'name': file_name,
                        'path': obj.object_name,
                        'type': 'file',
                        'size': obj.size,
                        'size_human': _format_size(obj.size),
                        'modified': obj.last_modified.isoformat() if obj.last_modified else None,
                        'storage_class': getattr(obj, 'storage_class', None) or 'STANDARD'
                    })
        
        except S3Error as e:
            logger.error(f"S3 error listing objects: {e}", exc_info=True)
            raise
    
    except Exception as e:
        logger.error(f"Error listing bucket objects: {e}", exc_info=True)
        raise
    
    # Сортируем: сначала папки, потом файлы, все по имени
    objects.sort(key=lambda x: (x['type'] != 'directory', x['name'].lower()))
    
    return objects


def get_bucket_stats(prefix: str = "", user_id: Optional[int] = None) -> Dict:
    """
    Получение статистики по объектам в S3 бакете
    
    Args:
        prefix: Префикс пути для фильтрации
        user_id: ID пользователя (для использования его конфигурации)
    
    Returns:
        Словарь со статистикой
    """
    total_size = 0
    total_files = 0
    total_folders = 0
    
    try:
        minio_client = get_minio_client(user_id=user_id)
        bucket_name = get_s3_bucket(user_id=user_id)
        
        normalized_prefix = prefix.rstrip('/') + '/' if prefix else ''
        
        for obj in minio_client.list_objects(
            bucket_name,
            prefix=normalized_prefix if normalized_prefix else None,
            recursive=True
        ):
            # Пропускаем сам префикс
            if obj.object_name == normalized_prefix or obj.object_name == prefix:
                continue
            
            if obj.is_dir or obj.object_name.endswith('/'):
                total_folders += 1
            else:
                total_files += 1
                total_size += obj.size
    
    except Exception as e:
        logger.error(f"Error getting bucket stats: {e}", exc_info=True)
        return {
            'total_size': 0,
            'total_size_human': '0 B',
            'total_files': 0,
            'total_folders': 0
        }
    
    return {
        'total_size': total_size,
        'total_size_human': _format_size(total_size),
        'total_files': total_files,
        'total_folders': total_folders
    }


def get_object_info(object_path: str, user_id: Optional[int] = None) -> Optional[Dict]:
    """
    Получение подробной информации об объекте
    
    Args:
        object_path: Путь к объекту
        user_id: ID пользователя (для использования его конфигурации)
    
    Returns:
        Словарь с информацией об объекте или None
    """
    try:
        minio_client = get_minio_client(user_id=user_id)
        bucket_name = get_s3_bucket(user_id=user_id)
        
        stat = minio_client.stat_object(bucket_name, object_path)
        
        return {
            'name': object_path.split('/')[-1],
            'path': object_path,
            'size': stat.size,
            'size_human': _format_size(stat.size),
            'modified': stat.last_modified.isoformat() if stat.last_modified else None,
            'content_type': stat.content_type or 'application/octet-stream',
            'etag': stat.etag,
            'storage_class': getattr(stat, 'storage_class', None) or 'STANDARD'
        }
    
    except S3Error as e:
        logger.error(f"S3 error getting object info: {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"Error getting object info: {e}", exc_info=True)
        return None


def delete_bucket_object(object_path: str, user_id: Optional[int] = None) -> bool:
    """
    Удаление объекта из S3 бакета
    
    Args:
        object_path: Путь к объекту в бакете
        user_id: ID пользователя (для использования его конфигурации)
    
    Returns:
        True если успешно, False в случае ошибки
    """
    try:
        minio_client = get_minio_client(user_id=user_id)
        bucket_name = get_s3_bucket(user_id=user_id)
        
        # Удаляем объект
        minio_client.remove_object(bucket_name, object_path)
        logger.info(f"Object deleted successfully: {object_path} (user_id: {user_id})")
        return True
        
    except S3Error as e:
        logger.error(f"Failed to delete object {object_path}: {e}", exc_info=True)
        return False
    except Exception as e:
        logger.error(f"Unexpected error deleting object {object_path}: {e}", exc_info=True)
        return False


def delete_bucket_directory(directory_path: str, user_id: Optional[int] = None) -> Tuple[int, int]:
    """
    Рекурсивное удаление директории (всех объектов с данным префиксом) из S3 бакета
    
    Args:
        directory_path: Путь к директории (префикс)
        user_id: ID пользователя (для использования его конфигурации)
    
    Returns:
        Кортеж (удалено_объектов, ошибок) 
    """
    deleted_count = 0
    error_count = 0
    
    try:
        minio_client = get_minio_client(user_id=user_id)
        bucket_name = get_s3_bucket(user_id=user_id)
        
        # Нормализуем путь директории - добавляем / в конце если нет
        normalized_prefix = directory_path.rstrip('/') + '/'
        
        # Получаем все объекты с данным префиксом рекурсивно
        objects_to_delete = []
        try:
            for obj in minio_client.list_objects(
                bucket_name,
                prefix=normalized_prefix,
                recursive=True
            ):
                objects_to_delete.append(obj.object_name)
        except S3Error as e:
            logger.error(f"Failed to list objects for directory {directory_path}: {e}", exc_info=True)
            return (0, 1)
        
        if not objects_to_delete:
            logger.warning(f"No objects found for directory {directory_path}")
            return (0, 0)
        
        # Удаляем все объекты
        from minio.deleteobjects import DeleteObject
        errors = minio_client.remove_objects(
            bucket_name,
            [DeleteObject(obj_name) for obj_name in objects_to_delete]
        )
        
        # Подсчитываем ошибки
        for error in errors:
            logger.error(f"Error deleting object {error.object_name}: {error.error}")
            error_count += 1
        
        deleted_count = len(objects_to_delete) - error_count
        
        if deleted_count > 0:
            logger.info(f"Directory deleted successfully: {directory_path} - {deleted_count} objects (user_id: {user_id})")
        if error_count > 0:
            logger.warning(f"Some errors occurred while deleting directory {directory_path}: {error_count} errors")
        
        return (deleted_count, error_count)
        
    except S3Error as e:
        logger.error(f"Failed to delete directory {directory_path}: {e}", exc_info=True)
        return (deleted_count, error_count + 1)
    except Exception as e:
        logger.error(f"Unexpected error deleting directory {directory_path}: {e}", exc_info=True)
        return (deleted_count, error_count + 1)


def _get_directory_stats_fast(directory_path: str, minio_client, bucket_name: str) -> Dict:
    """
    Быстрое получение статистики по директории (оптимизированная версия)
    Использует ограниченное количество объектов для быстрого ответа
    
    Args:
        directory_path: Путь к директории (должен заканчиваться на /)
        minio_client: MinIO клиент
        bucket_name: Имя бакета
    
    Returns:
        Словарь со статистикой (всегда возвращает валидные значения)
    """
    total_size = 0
    file_count = 0
    last_modified = None
    storage_classes = {}  # Счетчик классов хранения: {class: count}
    
    try:
        normalized_dir_path = directory_path.rstrip('/') + '/' if directory_path else ''
        
        logger.debug(f"Calculating stats for directory: {normalized_dir_path}")
        
        # Ограничиваем количество проверяемых объектов для быстрой работы
        max_objects = 10000  # Увеличиваем лимит для больших директорий
        objects_checked = 0
        has_more = False
        
        # Получаем все объекты рекурсивно
        for obj in minio_client.list_objects(
            bucket_name,
            prefix=normalized_dir_path,
            recursive=True
        ):
            objects_checked += 1
            if objects_checked > max_objects:
                has_more = True
                logger.warning(f"Directory {normalized_dir_path} has more than {max_objects} objects, stats may be incomplete")
                break
            
            obj_name = obj.object_name
            
            # Пропускаем саму директорию (если она отображается как объект)
            if obj_name == normalized_dir_path or obj_name.rstrip('/') == normalized_dir_path.rstrip('/'):
                continue
            
            # Учитываем только файлы (не директории)
            # В MinIO объект считается директорией если имя заканчивается на /
            is_directory_obj = obj_name.endswith('/')
            
            if not is_directory_obj:
                file_count += 1
                
                # Получаем размер объекта
                obj_size = getattr(obj, 'size', None)
                if obj_size is None:
                    # Если размер не в объекте, пытаемся получить через stat
                    try:
                        obj_stat = minio_client.stat_object(bucket_name, obj_name)
                        obj_size = getattr(obj_stat, 'size', 0) or 0
                    except Exception as stat_error:
                        logger.warning(f"Could not get size for {obj_name}: {stat_error}")
                        obj_size = 0
                else:
                    obj_size = int(obj_size) if obj_size else 0
                
                total_size += obj_size
                
                # Получаем дату модификации
                obj_last_modified = getattr(obj, 'last_modified', None)
                if obj_last_modified:
                    if last_modified is None or obj_last_modified > last_modified:
                        last_modified = obj_last_modified
                
                # Получаем класс хранения
                obj_storage_class = getattr(obj, 'storage_class', None)
                if not obj_storage_class:
                    # Если storage_class нет в объекте, пытаемся получить через stat
                    try:
                        obj_stat = minio_client.stat_object(bucket_name, obj_name)
                        obj_storage_class = getattr(obj_stat, 'storage_class', None)
                    except Exception:
                        pass
                
                # Используем STANDARD по умолчанию если класс не указан
                storage_class = obj_storage_class or 'STANDARD'
                storage_classes[storage_class] = storage_classes.get(storage_class, 0) + 1
        
        if has_more:
            logger.debug(f"Directory {normalized_dir_path} has more than {max_objects} objects, stats may be incomplete")
                        
    except Exception as e:
        logger.error(f"Error calculating directory stats for {directory_path}: {e}", exc_info=True)
        # Возвращаем пустую статистику при ошибке
        return {
            'total_size': 0,
            'total_size_human': 'Error',
            'file_count': 0,
            'last_modified': None,
            'storage_class': None
        }
    
    # Форматируем размер
    size_human = _format_size(total_size) if total_size > 0 else '0 B'
    
    # Определяем класс хранения для директории
    # Если все файлы имеют один класс - показываем его
    # Если несколько классов - показываем "Mixed" или самый распространенный
    directory_storage_class = None
    if storage_classes:
        unique_classes = list(storage_classes.keys())
        if len(unique_classes) == 1:
            directory_storage_class = unique_classes[0]
        else:
            # Находим самый распространенный класс
            most_common_class = max(storage_classes.items(), key=lambda x: x[1])[0]
            # Если файлы с разными классами, показываем Mixed
            if len(unique_classes) > 1 and storage_classes[most_common_class] < file_count:
                directory_storage_class = 'Mixed'
            else:
                directory_storage_class = most_common_class
    
    result = {
        'total_size': total_size,
        'total_size_human': size_human,
        'file_count': file_count,
        'last_modified': last_modified.isoformat() if last_modified else None,
        'storage_class': directory_storage_class
    }
    
    logger.debug(f"Directory stats for {normalized_dir_path}: size={total_size}, files={file_count}, modified={last_modified}")
    
    return result


def _get_directory_stats_safe(directory_path: str, minio_client, bucket_name: str) -> Dict:
    """
    Безопасное получение статистики по директории с обработкой всех ошибок
    
    Args:
        directory_path: Путь к директории (должен заканчиваться на /)
        minio_client: MinIO клиент
        bucket_name: Имя бакета
    
    Returns:
        Словарь со статистикой (всегда возвращает валидные значения)
    """
    try:
        stats = _get_directory_stats(directory_path, minio_client, bucket_name)
        logger.debug(f"Directory stats for {directory_path}: {stats}")
        return stats
    except Exception as e:
        logger.warning(f"Error getting directory stats for {directory_path}: {e}", exc_info=True)
        # Возвращаем пустую статистику при ошибке
        return {
            'total_size': 0,
            'total_size_human': 'Error',
            'file_count': 0,
            'last_modified': None
        }


def _get_directory_stats(directory_path: str, minio_client, bucket_name: str) -> Dict:
    """
    Получение статистики по директории (размер, количество файлов, последнее изменение)
    
    Args:
        directory_path: Путь к директории (должен заканчиваться на /)
        minio_client: MinIO клиент
        bucket_name: Имя бакета
    
    Returns:
        Словарь со статистикой: {total_size, total_size_human, file_count, last_modified}
    """
    total_size = 0
    file_count = 0
    last_modified = None
    
    try:
        # Получаем все объекты в директории рекурсивно
        # Ограничиваем количество итераций для больших директорий (чтобы не зависнуть)
        max_objects_to_check = 10000  # Максимум объектов для проверки
        objects_checked = 0
        
        # Убеждаемся, что путь нормализован (заканчивается на /)
        normalized_dir_path = directory_path.rstrip('/') + '/' if directory_path else ''
        
        logger.debug(f"Getting stats for directory: {normalized_dir_path}")
        
        for obj in minio_client.list_objects(
            bucket_name,
            prefix=normalized_dir_path,
            recursive=True
        ):
            objects_checked += 1
            if objects_checked > max_objects_to_check:
                logger.warning(f"Directory {normalized_dir_path} has more than {max_objects_to_check} objects, stats may be incomplete")
                break
            
            # Пропускаем саму директорию как объект
            if obj.object_name == normalized_dir_path or obj.object_name.rstrip('/') == normalized_dir_path.rstrip('/'):
                continue
            
            # Учитываем только файлы (не директории)
            if not (obj.is_dir or obj.object_name.endswith('/')):
                file_count += 1
                total_size += getattr(obj, 'size', 0) or 0
                
                # Обновляем последнее изменение (берем самое свежее)
                obj_last_modified = getattr(obj, 'last_modified', None)
                if obj_last_modified:
                    if last_modified is None or obj_last_modified > last_modified:
                        last_modified = obj_last_modified
                        
        logger.debug(f"Directory stats for {normalized_dir_path}: {file_count} files, {total_size} bytes")
        
    except S3Error as e:
        logger.error(f"S3 error getting stats for directory {directory_path}: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"Error getting stats for directory {directory_path}: {e}", exc_info=True)
        raise  # Пробрасываем исключение дальше, чтобы обработать на уровне выше
    
    return {
        'total_size': total_size,
        'total_size_human': _format_size(total_size) if total_size > 0 else '0 B',
        'file_count': file_count,
        'last_modified': last_modified.isoformat() if last_modified else None
    }


def _format_size(size_bytes: int) -> str:
    """Форматирование размера в читаемый вид"""
    try:
        import humanize
        return humanize.naturalsize(size_bytes, binary=True)
    except Exception:
        # Fallback если humanize недоступен
        size = float(size_bytes)
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB"
