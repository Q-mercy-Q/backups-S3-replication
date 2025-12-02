import os
import logging
import humanize
from datetime import datetime, timedelta
from typing import List, Set, Tuple, Optional, Dict, Any

from app.utils.config import get_nfs_path, get_ext_tag_map, get_backup_days, get_file_categories, upload_stats
from app.utils.file_utils import get_file_modification_time, is_file_in_time_range, normalize_s3_key

class FileScanner:
    """Сервис для сканирования файлов бэкапов с расширенной фильтрацией"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def scan_backup_files(
        self, 
        existing_s3_files: Set[str] = None, 
        categories: Optional[List[str]] = None,
        user_id: Optional[int] = None,
        config_id: Optional[int] = None,
        file_extensions: Optional[List[str]] = None,
        min_size: Optional[int] = None,
        max_size: Optional[int] = None,
        skip_time_filter: bool = False,
        backup_days: Optional[int] = None,
        source_directory: Optional[str] = None  # Относительный путь к поддиректории
    ) -> List[Tuple]:
        """
        Сканирует файлы бэкапов с расширенной фильтрацией
        
        Args:
            existing_s3_files: Множество уже существующих файлов в S3
            categories: Список категорий для фильтрации (если None, используется конфигурация)
            user_id: ID пользователя для получения конфигурации
            file_extensions: Список расширений файлов для включения (например, ['.vbk', '.vib', '.txt'])
            min_size: Минимальный размер файла в байтах
            max_size: Максимальный размер файла в байтах
            skip_time_filter: Пропустить фильтрацию по времени
            backup_days: Количество дней для фильтрации по времени (если None, используется конфигурация)
        """
        if existing_s3_files is None:
            existing_s3_files = set()
        
        # Получаем конфигурацию с поддержкой config_id
        from app.utils.config import get_nfs_path, get_ext_tag_map, get_backup_days, get_file_categories, get_config
        import os
        config = get_config(user_id=user_id, config_id=config_id)
        nfs_path = config.get('NFS_PATH', '/mnt/backups')
        ext_tag_map = config.get('EXT_TAG_MAP', {})
        if not ext_tag_map:
            ext_tag_map = {
                '.vbk': 'full',
                '.vib': 'incremental',
                '.vbm': 'metadata',
                '.log': 'logs'
            }
        
        if backup_days is None:
            backup_days = int(config.get('BACKUP_DAYS', 7))
        
        # Если указана поддиректория, добавляем её к базовому пути
        if source_directory:
            source_directory = source_directory.strip().strip('/')
            if source_directory:
                scan_path = os.path.join(nfs_path, source_directory)
                self.logger.info(f"📁 Using source directory: {source_directory} (full path: {scan_path})")
            else:
                scan_path = nfs_path
        else:
            scan_path = nfs_path
        
        # Логируем используемую конфигурацию
        self.logger.info(f"🔧 FileScanner config - NFS_PATH: {nfs_path}, BACKUP_DAYS: {backup_days}, config_id: {config_id}")
        if source_directory:
            self.logger.info(f"📁 Source directory: {source_directory}")
        
        if not os.path.exists(scan_path):
            self.logger.error(f"❌ Scan path does not exist: {scan_path}")
            return []
        
        self.logger.info(f"📂 Scanning directory: {scan_path}")
        
        # Если указаны конкретные расширения, используем их вместо категорий
        if file_extensions:
            self.logger.info(f"📋 Filtering by extensions: {file_extensions}")
            # Создаем расширенный ext_tag_map для указанных расширений
            extended_ext_tag_map = {}
            for ext in file_extensions:
                ext = ext.lower()
                if not ext.startswith('.'):
                    ext = '.' + ext
                # Используем существующий тег или создаем "custom"
                tag = ext_tag_map.get(ext, 'custom')
                extended_ext_tag_map[ext] = tag
            ext_tag_map = extended_ext_tag_map
        else:
            if skip_time_filter:
                self.logger.info("⏱️ Time filter disabled")
            else:
                self.logger.info(f"⏱️ Filter: last {backup_days} days")
        
        selected_categories = categories or get_file_categories(user_id=user_id, config_id=config_id)
        
        # Передаем scan_path (который может быть поддиректорией) в _scan_directory
        # но base_path остается nfs_path для правильного формирования относительных путей
        return self._scan_directory(
            scan_path,  # Сканируем эту директорию
            nfs_path,   # Базовая директория для формирования относительных путей
            ext_tag_map, 
            backup_days, 
            existing_s3_files, 
            selected_categories,
            file_extensions=file_extensions,
            min_size=min_size,
            max_size=max_size,
            skip_time_filter=skip_time_filter
        )
    
    def scan_specific_files(
        self,
        file_paths: List[str],
        existing_s3_files: Set[str] = None,
        user_id: Optional[int] = None
    ) -> List[Tuple]:
        """
        Сканирует и обрабатывает конкретные файлы по их путям
        
        Args:
            file_paths: Список относительных путей к файлам (относительно NFS_PATH)
            existing_s3_files: Множество уже существующих файлов в S3
            user_id: ID пользователя для получения конфигурации
        
        Returns:
            Список кортежей (full_path, rel_path, tag, file_size)
        """
        if existing_s3_files is None:
            existing_s3_files = set()
        
        from app.utils.config import get_nfs_path, get_ext_tag_map
        nfs_path = get_nfs_path(user_id=user_id)
        ext_tag_map = get_ext_tag_map(user_id=user_id)
        
        if not os.path.exists(nfs_path):
            self.logger.error(f"❌ NFS path does not exist: {nfs_path}")
            return []
        
        backup_files = []
        total_size = 0
        
        for rel_path in file_paths:
            full_path = os.path.join(nfs_path, rel_path)
            
            if not os.path.exists(full_path):
                self.logger.warning(f"⚠️ File not found: {full_path}")
                continue
            
            if not os.path.isfile(full_path):
                self.logger.warning(f"⚠️ Not a file: {full_path}")
                continue
            
            # Проверяем, существует ли файл уже в S3
            if rel_path in existing_s3_files:
                self.logger.debug(f"⏭️ Skipping existing file: {rel_path}")
                continue
            
            # Определяем тег по расширению
            ext = os.path.splitext(os.path.basename(rel_path))[1].lower()
            tag = ext_tag_map.get(ext, 'custom')
            
            try:
                file_size = os.path.getsize(full_path)
                backup_files.append((full_path, rel_path, tag, file_size))
                total_size += file_size
            except Exception as e:
                self.logger.warning(f"⚠️ Could not process file {rel_path}: {e}")
        
        # Обновляем статистику
        upload_stats.total_files = len(backup_files)
        upload_stats.total_bytes = total_size
        
        self.logger.info(f"✅ Scanned {len(backup_files)} specific files, total size: {humanize.naturalsize(total_size)}")
        
        return backup_files
    
    def _scan_directory(
        self, 
        scan_path: str,  # Директория для сканирования (может быть поддиректорией)
        base_path: str,  # Базовая директория для формирования относительных путей
        ext_tag_map: dict, 
        backup_days: int, 
        existing_s3_files: Set[str], 
        categories: List[str],
        file_extensions: Optional[List[str]] = None,
        min_size: Optional[int] = None,
        max_size: Optional[int] = None,
        skip_time_filter: bool = False
    ) -> List[Tuple]:
        """Рекурсивное сканирование директории с расширенными фильтрами"""
        backup_files = []
        total_size = 0
        skipped_time = 0
        skipped_existing = 0
        skipped_size = 0
        
        try:
            for root, dirs, files in os.walk(scan_path):
                # Проверка флага остановки
                if not upload_stats.is_running:
                    self.logger.info("⏹️ Scanning interrupted by user")
                    break
                
                # Игнорируем скрытые директории
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                
                for filename in files:
                    # Проверка флага остановки
                    if not upload_stats.is_running:
                        self.logger.info("⏹️ Scanning interrupted by user")
                        break
                    
                    # Игнорируем скрытые файлы
                    if filename.startswith('.'):
                        continue
                    
                    file_result = self._process_file(
                        root, filename, ext_tag_map, backup_days, 
                        existing_s3_files, base_path, categories,
                        file_extensions=file_extensions,
                        min_size=min_size,
                        max_size=max_size,
                        skip_time_filter=skip_time_filter
                    )
                    
                    if file_result:
                        if file_result == 'skipped_time':
                            skipped_time += 1
                        elif file_result == 'skipped_existing':
                            skipped_existing += 1
                        elif file_result == 'skipped_size':
                            skipped_size += 1
                        else:
                            backup_files.append(file_result)
                            total_size += file_result[3]  # size is at index 3
            
            # Обновляем статистику
            self._update_stats(len(backup_files), total_size, skipped_existing, skipped_time)
            
            # Логируем результаты
            self._log_scan_results(backup_files, skipped_time, skipped_existing, skipped_size, total_size)
            
            return backup_files
            
        except Exception as e:
            self.logger.error(f"❌ Error scanning NFS directory: {e}")
            return []
    
    def _process_file(
        self, 
        root: str, 
        filename: str, 
        ext_tag_map: dict, 
        backup_days: int, 
        existing_s3_files: Set[str], 
        nfs_path: str,
        categories: List[str],
        file_extensions: Optional[List[str]] = None,
        min_size: Optional[int] = None,
        max_size: Optional[int] = None,
        skip_time_filter: bool = False
    ):
        """Обработка отдельного файла с расширенными фильтрами"""
        try:
            full_path = os.path.join(root, filename)
            
            # Определяем расширение
            ext = os.path.splitext(filename)[1].lower()
            
            # Если указаны конкретные расширения, фильтруем по ним
            if file_extensions:
                # Нормализуем расширения (добавляем точку если нет)
                normalized_exts = [e if e.startswith('.') else '.' + e.lower() for e in file_extensions]
                if ext not in normalized_exts:
                    return None
                tag = ext_tag_map.get(ext, 'custom')
            else:
                # Используем стандартную логику
                tag = ext_tag_map.get(ext)
                if not tag:
                    return None
            
            # Фильтр по категориям (если указаны)
            if categories and tag not in categories:
                return None
            
            # Проверяем временной диапазон (если не отключен)
            if not skip_time_filter:
                if not is_file_in_time_range(full_path, backup_days):
                    return 'skipped_time'
            
            # Получаем относительный путь
            rel_path = os.path.relpath(full_path, nfs_path)
            
            # Проверяем, существует ли файл уже в S3
            if rel_path in existing_s3_files:
                return 'skipped_existing'
            
            # Получаем размер файла
            file_size = os.path.getsize(full_path)
            
            # Фильтр по размеру
            if min_size is not None and file_size < min_size:
                return 'skipped_size'
            if max_size is not None and file_size > max_size:
                return 'skipped_size'
            
            return (full_path, rel_path, tag, file_size)
            
        except Exception as e:
            self.logger.warning(f"⚠️ Could not process file {filename}: {e}")
            return None
    
    def _update_stats(self, files_count: int, total_size: int, skipped_existing: int, skipped_time: int):
        """Обновление статистики сканирования"""
        upload_stats.total_files = files_count
        upload_stats.total_bytes = total_size
        upload_stats.skipped_existing = skipped_existing
        upload_stats.skipped_time = skipped_time
    
    def _log_scan_results(
        self, 
        backup_files: List[Tuple], 
        skipped_time: int, 
        skipped_existing: int,
        skipped_size: int,
        total_size: int
    ):
        """Логирование результатов сканирования"""
        self.logger.info(f"📊 Scan results: {len(backup_files)} files to upload")
        if skipped_time > 0:
            self.logger.info(f"⏭️ Skipped {skipped_time} files (outside time range)")
        if skipped_existing > 0:
            self.logger.info(f"⏭️ Skipped {skipped_existing} files (already in S3)")
        if skipped_size > 0:
            self.logger.info(f"⏭️ Skipped {skipped_size} files (size filter)")
        self.logger.info(f"📦 Total size to upload: {humanize.naturalsize(total_size)}")
        
        if backup_files:
            large_files = sorted(backup_files, key=lambda x: x[3], reverse=True)[:5]
            self.logger.info("📋 Top 5 largest files to upload:")
            for full, rel, tag, size in large_files:
                file_time = get_file_modification_time(full)
                self.logger.info(f"  {humanize.naturalsize(size):>10} - {file_time.strftime('%Y-%m-%d %H:%M')} - {rel}")

# Глобальный экземпляр для обратной совместимости
file_scanner = FileScanner()

# Функции для обратной совместимости
def scan_backup_files(
    existing_s3_files=None, 
    categories: Optional[List[str]] = None,
    user_id: Optional[int] = None,
    config_id: Optional[int] = None,
    file_extensions: Optional[List[str]] = None,
    min_size: Optional[int] = None,
    max_size: Optional[int] = None,
    skip_time_filter: bool = False,
    backup_days: Optional[int] = None,
    source_directory: Optional[str] = None
):
    return file_scanner.scan_backup_files(
        existing_s3_files, 
        categories, 
        user_id,
        config_id,
        file_extensions,
        min_size,
        max_size,
        skip_time_filter,
        backup_days,
        source_directory
    )

def scan_specific_files(
    file_paths: List[str],
    existing_s3_files: Optional[Set[str]] = None,
    user_id: Optional[int] = None
):
    """Сканирование конкретных файлов"""
    return file_scanner.scan_specific_files(file_paths, existing_s3_files, user_id)

def get_file_modification_time(file_path):
    from app.utils.file_utils import get_file_modification_time as get_mtime
    return get_mtime(file_path)

def normalize_s3_key(tag: str, rel_path: str) -> str:
    from app.utils.file_utils import normalize_s3_key as normalize_key
    return normalize_key(tag, rel_path)

def is_file_in_time_range(file_path, days_back):
    from app.utils.file_utils import is_file_in_time_range as in_time_range
    return in_time_range(file_path, days_back)
