from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, Any, List

@dataclass
class UploadStats:
    """Модель статистики загрузки"""
    
    total_files: int = 0
    successful: int = 0
    failed: int = 0
    total_bytes: int = 0
    uploaded_bytes: int = 0
    start_time: float = 0.0
    file_start_times: Dict[str, float] = None
    is_running: bool = False
    skipped_existing: int = 0
    skipped_time: int = 0
    
    def __post_init__(self):
        if self.file_start_times is None:
            self.file_start_times = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертация в словарь"""
        return asdict(self)
    
    def reset(self):
        """Сброс статистики"""
        self.total_files = 0
        self.successful = 0
        self.failed = 0
        self.total_bytes = 0
        self.uploaded_bytes = 0
        self.start_time = 0.0
        self.file_start_times.clear()
        self.is_running = False
        self.skipped_existing = 0
        self.skipped_time = 0
    
    def get_progress_percent(self) -> float:
        """Получение процента выполнения"""
        if self.total_files == 0:
            return 0.0
        processed = self.successful + self.failed
        return (processed / self.total_files) * 100
    
    def get_elapsed_time(self) -> float:
        """Получение прошедшего времени в секундах"""
        if self.start_time == 0:
            return 0.0
        return datetime.now().timestamp() - self.start_time
    
    def get_upload_speed(self) -> float:
        """Получение скорости загрузки (байт/сек)"""
        elapsed = self.get_elapsed_time()
        if elapsed == 0:
            return 0.0
        return self.uploaded_bytes / elapsed
    
    def get_remaining_files(self) -> int:
        """Получение количества оставшихся файлов"""
        return self.total_files - (self.successful + self.failed)
    
    def get_success_rate(self) -> float:
        """Получение процента успешных загрузок"""
        processed = self.successful + self.failed
        if processed == 0:
            return 0.0
        return (self.successful / processed) * 100

@dataclass
class ScheduleStats:
    """Модель статистики расписания"""
    
    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    total_files_uploaded: int = 0
    total_data_uploaded_bytes: int = 0
    average_duration: float = 0.0
    last_run: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.last_run is None:
            self.last_run = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертация в словарь"""
        data = asdict(self)
        data['success_rate'] = self.get_success_rate()
        data['total_data_uploaded'] = self.get_total_data_formatted()
        return data
    
    def get_success_rate(self) -> float:
        """Получение процента успешных запусков"""
        if self.total_runs == 0:
            return 0.0
        return (self.successful_runs / self.total_runs) * 100
    
    def get_total_data_formatted(self) -> str:
        """Форматирование общего объема данных"""
        return self._format_size(self.total_data_uploaded_bytes)
    
    @staticmethod
    def _format_size(size_bytes: int) -> str:
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