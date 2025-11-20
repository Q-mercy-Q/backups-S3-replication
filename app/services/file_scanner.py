import os
import logging
import humanize
from datetime import datetime
from typing import List, Set, Tuple

from app.utils.config import get_nfs_path, get_ext_tag_map, get_backup_days, upload_stats
from app.utils.file_utils import get_file_modification_time, is_file_in_time_range, normalize_s3_key

class FileScanner:
    """Сервис для сканирования файлов бэкапов"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def scan_backup_files(self, existing_s3_files: Set[str] = None) -> List[Tuple]:
        """Сканирует файлы бэкапов с фильтрацией"""
        if existing_s3_files is None:
            existing_s3_files = set()
        
        nfs_path = get_nfs_path()
        ext_tag_map = get_ext_tag_map()
        backup_days = get_backup_days()
        
        if not os.path.exists(nfs_path):
            self.logger.error(f"NFS path does not exist: {nfs_path}")
            return []
        
        self.logger.info(f"Scanning NFS directory: {nfs_path}")
        self.logger.info(f"Filter: last {backup_days} days")
        
        return self._scan_directory(nfs_path, ext_tag_map, backup_days, existing_s3_files)
    
    def _scan_directory(self, nfs_path: str, ext_tag_map: dict, backup_days: int, existing_s3_files: Set[str]) -> List[Tuple]:
        """Рекурсивное сканирование директории"""
        backup_files = []
        total_size = 0
        skipped_time = 0
        skipped_existing = 0
        
        try:
            for root, dirs, files in os.walk(nfs_path):
                # Проверка флага остановки - ИСПРАВЛЕНО: используем атрибуты объекта
                if not upload_stats.is_running:
                    self.logger.info("Scanning interrupted by user")
                    break
                
                # Игнорируем скрытые директории
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                
                for filename in files:
                    # Проверка флага остановки - ИСПРАВЛЕНО: используем атрибуты объекта
                    if not upload_stats.is_running:
                        self.logger.info("Scanning interrupted by user")
                        break
                    
                    # Игнорируем скрытые файлы
                    if filename.startswith('.'):
                        continue
                    
                    file_result = self._process_file(
                        root, filename, ext_tag_map, backup_days, 
                        existing_s3_files, nfs_path
                    )
                    
                    if file_result:
                        if file_result == 'skipped_time':
                            skipped_time += 1
                        elif file_result == 'skipped_existing':
                            skipped_existing += 1
                        else:
                            backup_files.append(file_result)
                            total_size += file_result[3]  # size is at index 3
            
            # Обновляем статистику - ИСПРАВЛЕНО: используем атрибуты объекта
            self._update_stats(len(backup_files), total_size, skipped_existing, skipped_time)
            
            # Логируем результаты
            self._log_scan_results(backup_files, skipped_time, skipped_existing, total_size)
            
            return backup_files
            
        except Exception as e:
            self.logger.error(f"Error scanning NFS directory: {e}")
            return []
    
    def _process_file(self, root: str, filename: str, ext_tag_map: dict, 
                     backup_days: int, existing_s3_files: Set[str], nfs_path: str):
        """Обработка отдельного файла"""
        try:
            full_path = os.path.join(root, filename)
            
            # Определяем тег по расширению
            ext = os.path.splitext(filename)[1].lower()
            tag = ext_tag_map.get(ext)
            if not tag:
                return None
            
            # Проверяем временной диапазон
            if not is_file_in_time_range(full_path, backup_days):
                return 'skipped_time'
            
            # Получаем относительный путь
            rel_path = os.path.relpath(full_path, nfs_path)
            
            # Проверяем, существует ли файл уже в S3
            if rel_path in existing_s3_files:
                return 'skipped_existing'
            
            # Получаем размер файла
            file_size = os.path.getsize(full_path)
            
            return (full_path, rel_path, tag, file_size)
            
        except Exception as e:
            self.logger.warning(f"Could not process file {filename}: {e}")
            return None
    
    def _update_stats(self, files_count: int, total_size: int, skipped_existing: int, skipped_time: int):
        """Обновление статистики сканирования - ИСПРАВЛЕНО: используем атрибуты объекта"""
        upload_stats.total_files = files_count
        upload_stats.total_bytes = total_size
        upload_stats.skipped_existing = skipped_existing
        upload_stats.skipped_time = skipped_time
    
    def _log_scan_results(self, backup_files: List[Tuple], skipped_time: int, 
                         skipped_existing: int, total_size: int):
        """Логирование результатов сканирования"""
        self.logger.info(f"Found {len(backup_files)} files for upload")
        self.logger.info(f"Skipped {skipped_time} files (outside time range)")
        self.logger.info(f"Skipped {skipped_existing} files (already in S3)")
        self.logger.info(f"Total size to upload: {humanize.naturalsize(total_size)}")
        
        if backup_files:
            large_files = sorted(backup_files, key=lambda x: x[3], reverse=True)[:5]
            self.logger.info("Top 5 largest files to upload:")
            for full, rel, tag, size in large_files:
                file_time = get_file_modification_time(full)
                self.logger.info(f"  {humanize.naturalsize(size):>10} - {file_time.strftime('%Y-%m-%d %H:%M')} - {rel}")

# Глобальный экземпляр для обратной совместимости
file_scanner = FileScanner()

# Функции для обратной совместимости
def scan_backup_files(existing_s3_files=None):
    return file_scanner.scan_backup_files(existing_s3_files)

def get_file_modification_time(file_path):
    from app.utils.file_utils import get_file_modification_time as get_mtime
    return get_mtime(file_path)

def normalize_s3_key(tag: str, rel_path: str) -> str:
    from app.utils.file_utils import normalize_s3_key as normalize_key
    return normalize_key(tag, rel_path)

def is_file_in_time_range(file_path, days_back):
    from app.utils.file_utils import is_file_in_time_range as in_time_range
    return in_time_range(file_path, days_back)