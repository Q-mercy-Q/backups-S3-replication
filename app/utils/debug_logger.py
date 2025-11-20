import logging
import os
from datetime import datetime
from typing import List, Dict, Any

class DebugLogger:
    """Утилита для управления отладочными логами"""
    
    def __init__(self, log_file: str = 'logs/scheduler_debug.log', max_logs: int = 1000):
        self.log_file = log_file
        self.max_logs = max_logs
        self.logs: List[Dict[str, Any]] = []
        self.setup_logging()
    
    def setup_logging(self):
        """Настройка логирования"""
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        
        self.logger = logging.getLogger('scheduler_debug')
        self.logger.setLevel(logging.DEBUG)
        
        # Обработчик для файла
        file_handler = logging.FileHandler(self.log_file)
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s"
        ))
        self.logger.addHandler(file_handler)
        self.logger.propagate = False
        
        # Обработчик для памяти
        self.setup_memory_handler()
    
    def setup_memory_handler(self):
        """Настройка обработчика для хранения логов в памяти"""
        class MemoryHandler(logging.Handler):
            def __init__(self, debug_logger):
                super().__init__()
                self.debug_logger = debug_logger
            
            def emit(self, record):
                log_entry = {
                    'timestamp': datetime.now().strftime('%H:%M:%S'),
                    'level': record.levelname,
                    'message': self.format(record)
                }
                self.debug_logger.add_log(log_entry)
        
        memory_handler = MemoryHandler(self)
        memory_handler.setLevel(logging.DEBUG)
        self.logger.addHandler(memory_handler)
    
    def add_log(self, log_entry: Dict[str, Any]):
        """Добавление лога"""
        self.logs.append(log_entry)
        if len(self.logs) > self.max_logs:
            self.logs = self.logs[-self.max_logs:]
    
    def get_logs(self, level: str = 'INFO', limit: int = 100) -> List[Dict[str, Any]]:
        """Получение логов с фильтрацией по уровню"""
        level_priority = {'DEBUG': 10, 'INFO': 20, 'WARNING': 30, 'ERROR': 40}
        min_priority = level_priority.get(level, 20)
        
        filtered_logs = [
            log for log in self.logs 
            if level_priority.get(log['level'], 20) >= min_priority
        ]
        
        return filtered_logs[-limit:]
    
    def clear_logs(self) -> bool:
        """Очистка логов"""
        self.logs = []
        return True
    
    def info(self, message: str):
        """Логирование информационного сообщения"""
        self.logger.info(message)
    
    def error(self, message: str):
        """Логирование ошибки"""
        self.logger.error(message)
    
    def debug(self, message: str):
        """Логирование отладочного сообщения"""
        self.logger.debug(message)