import os
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Dict, Any, Tuple

@dataclass
class BackupFile:
    """Модель файла бэкапа для загрузки в S3"""
    
    full_path: str
    relative_path: str
    tag: str
    size: int
    modification_time: Optional[datetime] = None
    name: Optional[str] = None
    
    def __post_init__(self):
        # Устанавливаем имя файла если не задано
        if not self.name:
            self.name = os.path.basename(self.full_path)
        
        # Устанавливаем время модификации если не задано
        if self.modification_time is None:
            self.modification_time = self._get_file_modification_time()
    
    def _get_file_modification_time(self) -> datetime:
        """Получение времени модификации файла"""
        try:
            return datetime.fromtimestamp(os.path.getmtime(self.full_path))
        except Exception:
            return datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертация в словарь"""
        data = asdict(self)
        
        # Конвертируем datetime в строку
        if self.modification_time:
            data['modification_time'] = self.modification_time.isoformat()
        
        # Добавляем вычисляемые поля
        data['size_formatted'] = self.get_size_formatted()
        data['modification_time_formatted'] = self.get_modification_time_formatted()
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BackupFile':
        """Создание из словаря"""
        # Конвертируем строку времени обратно в datetime
        if 'modification_time' in data and isinstance(data['modification_time'], str):
            data['modification_time'] = datetime.fromisoformat(data['modification_time'])
        
        return cls(**data)
    
    def to_tuple(self) -> Tuple:
        """Конвертация в кортеж для обратной совместимости"""
        return (self.full_path, self.relative_path, self.tag, self.size)
    
    @classmethod
    def from_tuple(cls, file_tuple: Tuple) -> 'BackupFile':
        """Создание из кортежа"""
        return cls(
            full_path=file_tuple[0],
            relative_path=file_tuple[1],
            tag=file_tuple[2],
            size=file_tuple[3]
        )
    
    def get_size_formatted(self) -> str:
        """Форматирование размера файла"""
        return self._format_size(self.size)
    
    def get_modification_time_formatted(self) -> str:
        """Форматирование времени модификации"""
        if self.modification_time:
            return self.modification_time.strftime('%Y-%m-%d %H:%M:%S')
        return "Unknown"
    
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
    
    def exists(self) -> bool:
        """Проверка существования файла"""
        return os.path.exists(self.full_path)
    
    def is_readable(self) -> bool:
        """Проверка доступности файла для чтения"""
        return os.access(self.full_path, os.R_OK)
    
    def get_file_stats(self) -> Dict[str, Any]:
        """Получение статистики файла"""
        return {
            'modification_time': self.modification_time,
            'size': self.size,
            'readable': self.is_readable(),
            'exists': self.exists()
        }
    
    def __str__(self) -> str:
        return f"BackupFile({self.name}, {self.get_size_formatted()}, {self.tag})"
    
    def __repr__(self) -> str:
        return f"BackupFile(full_path='{self.full_path}', relative_path='{self.relative_path}', tag='{self.tag}', size={self.size})"