"""
File system utilities for S3 Backup Manager
"""

import os
import re
import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple

def normalize_s3_key(tag: str, rel_path: str) -> str:
    """Нормализация имени файла для S3"""
    safe_path = re.sub(r'[^a-zA-Z0-9/._-]', '_', rel_path)
    safe_path = re.sub(r'_+', '_', safe_path)
    segments = safe_path.split('/')
    safe_segments = [seg.strip('_').strip('.')[:200] for seg in segments]
    return f"{tag}/" + '/'.join(safe_segments)

def get_file_modification_time(file_path: str) -> datetime:
    """Получает время последнего изменения файла"""
    try:
        return datetime.fromtimestamp(os.path.getmtime(file_path))
    except Exception as e:
        logging.warning(f"Could not get modification time for {file_path}: {e}")
        return datetime.now()

def is_file_in_time_range(file_path: str, days_back: int) -> bool:
    """Проверяет, попадает ли файл в указанный временной диапазон"""
    if days_back <= 0:  # 0 или отрицательное значение - загружать все файлы
        return True
    
    file_time = get_file_modification_time(file_path)
    cutoff_time = datetime.now() - timedelta(days=days_back)
    
    return file_time >= cutoff_time

def get_file_info(file_path: str, base_path: str) -> Optional[Tuple]:
    """Получение информации о файле для загрузки"""
    try:
        if not os.path.exists(file_path):
            return None
            
        file_size = os.path.getsize(file_path)
        relative_path = os.path.relpath(file_path, base_path)
        modification_time = get_file_modification_time(file_path)
        
        return (file_path, relative_path, file_size, modification_time)
        
    except Exception as e:
        logging.warning(f"Could not get file info for {file_path}: {e}")
        return None

def format_size(size_bytes: int) -> str:
    """Форматирование размера в читаемый вид"""
    if not size_bytes:
        return "0 B"
    
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    size = float(size_bytes)
    
    for unit in units:
        if size < 1024.0 or unit == units[-1]:
            if unit == 'B':
                return f"{size:.0f} {unit}"
            else:
                return f"{size:.2f} {unit}"
        size /= 1024.0
    
    return f"{size_bytes} B"