import os
import json
import logging
from typing import Dict, Any, Tuple, List
from app.models.schedule import Schedule
from app.models.sync_history import SyncHistory

class ScheduleStorage:
    """Утилита для работы с хранилищем расписаний"""
    
    def __init__(self, schedule_file: str = 'data/schedules.json'):
        self.schedule_file = schedule_file
        self.logger = logging.getLogger(__name__)
        self._ensure_directory_exists()
    
    def _ensure_directory_exists(self):
        """Создание директории для файла расписаний если не существует"""
        directory = os.path.dirname(self.schedule_file)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            self.logger.info(f"Created directory: {directory}")
    
    def load_schedules(self) -> Tuple[Dict[str, Schedule], List[SyncHistory]]:
        """Загрузка расписаний и истории из файла"""
        schedules = {}
        history = []
        
        try:
            if os.path.exists(self.schedule_file):
                with open(self.schedule_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # Загружаем расписания
                    for schedule_id, schedule_data in data.get('schedules', {}).items():
                        try:
                            schedule = Schedule.from_dict(schedule_data)
                            schedules[schedule_id] = schedule
                        except Exception as e:
                            self.logger.error(f"Error loading schedule {schedule_id}: {e}")
                            continue
                    
                    # Загружаем историю
                    for history_data in data.get('history', []):
                        try:
                            history_entry = SyncHistory.from_dict(history_data)
                            history.append(history_entry)
                        except Exception as e:
                            self.logger.error(f"Error loading history entry: {e}")
                            continue
                    
                    self.logger.info(f"Loaded {len(schedules)} schedules and {len(history)} history entries")
                    
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in schedule file: {e}")
            # Создаем backup поврежденного файла
            self._backup_corrupted_file()
        except Exception as e:
            self.logger.error(f"Error loading schedules: {e}")
        
        return schedules, history
    
    def _backup_corrupted_file(self):
        """Создание backup поврежденного файла"""
        try:
            if os.path.exists(self.schedule_file):
                backup_file = f"{self.schedule_file}.corrupted.{int(os.path.getmtime(self.schedule_file))}"
                os.rename(self.schedule_file, backup_file)
                self.logger.warning(f"Backed up corrupted schedule file to: {backup_file}")
        except Exception as e:
            self.logger.error(f"Failed to backup corrupted file: {e}")
    
    def save_schedules(self, schedules: Dict[str, Schedule], history: List[SyncHistory], max_history_entries: int = 100) -> bool:
        """Сохранение расписаний и истории в файл"""
        try:
            # Конвертируем в словари
            schedules_dict = {}
            for schedule_id, schedule in schedules.items():
                try:
                    schedules_dict[schedule_id] = schedule.to_dict()
                except Exception as e:
                    self.logger.error(f"Error converting schedule {schedule_id} to dict: {e}")
                    continue
            
            history_dict = []
            for history_entry in history[-max_history_entries:]:
                try:
                    history_dict.append(history_entry.to_dict())
                except Exception as e:
                    self.logger.error(f"Error converting history entry to dict: {e}")
                    continue
            
            data = {
                'schedules': schedules_dict,
                'history': history_dict
            }
            
            # Создаем временный файл для атомарной записи
            temp_file = f"{self.schedule_file}.tmp"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Заменяем старый файл новым
            if os.path.exists(self.schedule_file):
                os.replace(temp_file, self.schedule_file)
            else:
                os.rename(temp_file, self.schedule_file)
            
            self.logger.debug("Schedules saved to file")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving schedules: {e}")
            # Пытаемся удалить временный файл если он существует
            try:
                temp_file = f"{self.schedule_file}.tmp"
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except:
                pass
            return False
    
    def get_storage_info(self) -> Dict[str, Any]:
        """Получение информации о хранилище"""
        info = {
            'schedule_file': self.schedule_file,
            'exists': os.path.exists(self.schedule_file),
            'directory': os.path.dirname(self.schedule_file),
        }
        
        if info['exists']:
            try:
                file_stats = os.stat(self.schedule_file)
                info.update({
                    'size': file_stats.st_size,
                    'modified': file_stats.st_mtime,
                    'size_human': self._format_size(file_stats.st_size)
                })
                
                # Информация о данных в файле
                schedules, history = self.load_schedules()
                info.update({
                    'schedules_count': len(schedules),
                    'history_count': len(history)
                })
                
            except Exception as e:
                info['error'] = str(e)
        
        return info
    
    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Форматирование размера файла"""
        if not size_bytes:
            return "0 B"
        
        units = ['B', 'KB', 'MB', 'GB']
        size = float(size_bytes)
        
        for unit in units:
            if size < 1024.0 or unit == units[-1]:
                if unit == 'B':
                    return f"{size:.0f} {unit}"
                else:
                    return f"{size:.2f} {unit}"
            size /= 1024.0
        
        return f"{size_bytes} B"