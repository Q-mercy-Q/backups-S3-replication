from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from uuid import uuid4

class ScheduleType(Enum):
    """Типы расписаний"""
    INTERVAL = "interval"
    CRON = "cron"

@dataclass
class Schedule:
    """Модель расписания выполнения задач"""
    
    id: str
    name: str
    schedule_type: ScheduleType
    interval: str  # минуты для interval, cron выражение для cron
    enabled: bool = True
    created_at: Optional[str] = None
    last_run: Optional[str] = None
    next_run: Optional[str] = None
    description: Optional[str] = None
    categories: Optional[List[str]] = None
    
    def __post_init__(self):
        # Конвертируем строку в Enum если нужно
        if isinstance(self.schedule_type, str):
            self.schedule_type = ScheduleType(self.schedule_type)
        
        # Устанавливаем время создания если не задано
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        
        # Генерируем ID если не задан
        if not self.id:
            self.id = f"schedule_{uuid4().hex[:8]}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертация в словарь для JSON сериализации"""
        data = asdict(self)
        data['schedule_type'] = self.schedule_type.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Schedule':
        """Создание из словаря"""
        # Конвертируем строковый тип в Enum
        if isinstance(data.get('schedule_type'), str):
            data['schedule_type'] = ScheduleType(data['schedule_type'])
        if 'categories' in data and data['categories'] is None:
            data['categories'] = None
        
        return cls(**data)
    
    def validate(self) -> bool:
        """Валидация данных расписания"""
        if not self.name or not self.name.strip():
            raise ValueError("Schedule name is required")
        
        if not self.interval:
            raise ValueError("Schedule interval is required")
        
        if self.schedule_type == ScheduleType.INTERVAL:
            try:
                interval_minutes = int(self.interval)
                if interval_minutes <= 0:
                    raise ValueError("Interval must be positive")
            except (ValueError, TypeError):
                raise ValueError("Interval must be a positive integer")

        if self.categories:
            self.categories = [str(category).strip() for category in self.categories if str(category).strip()]
        
        return True
    
    def get_interval_display(self) -> str:
        """Получение читаемого представления интервала"""
        if self.schedule_type == ScheduleType.CRON:
            return f"Cron: {self.interval}"
        
        # Для interval расписаний конвертируем минуты в читаемый формат
        minutes = int(self.interval)
        
        if minutes % (7 * 24 * 60) == 0:
            weeks = minutes // (7 * 24 * 60)
            return f"Every {weeks} week{'s' if weeks > 1 else ''}"
        elif minutes % (24 * 60) == 0:
            days = minutes // (24 * 60)
            return f"Every {days} day{'s' if days > 1 else ''}"
        elif minutes % 60 == 0:
            hours = minutes // 60
            return f"Every {hours} hour{'s' if hours > 1 else ''}"
        else:
            return f"Every {minutes} minute{'s' if minutes > 1 else ''}"