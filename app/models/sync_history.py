from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from uuid import uuid4

class SyncStatus(Enum):
    """Статусы синхронизации"""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class SyncHistory:
    """Модель записи истории синхронизации"""
    
    id: str
    schedule_id: str
    schedule_name: str
    start_time: str
    status: SyncStatus
    files_processed: int = 0
    files_uploaded: int = 0
    files_failed: int = 0
    total_size: int = 0
    uploaded_size: int = 0
    duration: float = 0.0
    error: Optional[str] = None
    end_time: Optional[str] = None
    
    def __post_init__(self):
        # Конвертируем строку в Enum если нужно
        if isinstance(self.status, str):
            self.status = SyncStatus(self.status)
        
        # Генерируем ID если не задан
        if not self.id:
            self.id = f"sync_{uuid4().hex[:8]}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертация в словарь для JSON сериализации"""
        data = asdict(self)
        data['status'] = self.status.value
        
        # Добавляем вычисляемые поля
        data['success_rate'] = self.get_success_rate()
        data['duration_formatted'] = self.get_duration_formatted()
        data['total_size_formatted'] = self.get_size_formatted(self.total_size)
        data['uploaded_size_formatted'] = self.get_size_formatted(self.uploaded_size)
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SyncHistory':
        """Создание из словаря"""
        # Конвертируем строковый статус в Enum
        if isinstance(data.get('status'), str):
            data['status'] = SyncStatus(data['status'])
        
        return cls(**data)
    
    def get_success_rate(self) -> float:
        """Вычисление процента успешных операций"""
        if self.files_processed == 0:
            return 0.0
        return (self.files_uploaded / self.files_processed) * 100
    
    def get_duration_formatted(self) -> str:
        """Форматирование длительности"""
        if self.duration < 60:
            return f"{self.duration:.1f}s"
        elif self.duration < 3600:
            minutes = int(self.duration // 60)
            seconds = int(self.duration % 60)
            return f"{minutes}m {seconds}s"
        else:
            hours = int(self.duration // 3600)
            minutes = int((self.duration % 3600) // 60)
            return f"{hours}h {minutes}m"
    
    @staticmethod
    def get_size_formatted(size_bytes: int) -> str:
        """Форматирование размера в читаемый вид"""
        if not size_bytes:
            return "0 B"
        
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        size = float(size_bytes)
        
        for unit in units:
            if size < 1024.0 or unit == units[-1]:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        
        return f"{size_bytes} B"
    
    def mark_completed(self, files_uploaded: int, files_failed: int, 
                      total_size: int, uploaded_size: int, duration: float):
        """Отметка завершения синхронизации"""
        self.status = SyncStatus.COMPLETED
        self.files_processed = files_uploaded + files_failed
        self.files_uploaded = files_uploaded
        self.files_failed = files_failed
        self.total_size = total_size
        self.uploaded_size = uploaded_size
        self.duration = duration
        self.end_time = datetime.now().isoformat()
    
    def mark_failed(self, error: str, duration: float):
        """Отметка неудачной синхронизации"""
        self.status = SyncStatus.FAILED
        self.error = error
        self.duration = duration
        self.end_time = datetime.now().isoformat()
    
    def is_successful(self) -> bool:
        """Проверка успешности синхронизации"""
        return self.status == SyncStatus.COMPLETED and self.files_failed == 0
    
    def get_summary(self) -> str:
        """Получение краткого описания синхронизации"""
        if self.status == SyncStatus.RUNNING:
            return f"Running - {self.files_processed} files processed"
        elif self.status == SyncStatus.COMPLETED:
            return f"Completed - {self.files_uploaded}/{self.files_processed} files uploaded"
        elif self.status == SyncStatus.FAILED:
            return f"Failed - {self.error}"
        else:
            return f"{self.status.value.capitalize()}"