"""
Структурированное логирование для S3 Backup Manager
"""

import logging
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path


class StructuredFormatter(logging.Formatter):
    """Форматтер для структурированного логирования"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Форматирование записи лога"""
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }
        
        # Добавляем дополнительные поля если они есть
        if hasattr(record, 'file_name'):
            log_data['file_name'] = record.file_name
        if hasattr(record, 'file_size'):
            log_data['file_size'] = record.file_size
        if hasattr(record, 'attempt'):
            log_data['attempt'] = record.attempt
        if hasattr(record, 'progress'):
            log_data['progress'] = record.progress
        if hasattr(record, 'upload_speed'):
            log_data['upload_speed'] = record.upload_speed
        if hasattr(record, 'elapsed_time'):
            log_data['elapsed_time'] = record.elapsed_time
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Форматируем как JSON для структурированных логов или как читаемый текст
        if os.getenv('STRUCTURED_LOGS', 'false').lower() == 'true':
            return json.dumps(log_data, ensure_ascii=False)
        else:
            # Читаемый формат
            parts = [f"[{log_data['timestamp']}]", f"[{log_data['level']}]"]
            if 'file_name' in log_data:
                parts.append(f"[{log_data['file_name']}]")
            if 'progress' in log_data:
                parts.append(f"[{log_data['progress']}%]")
            parts.append(log_data['message'])
            return ' '.join(parts)


class UploadLogger:
    """Специализированный логгер для процесса загрузки"""
    
    def __init__(self, logger_name: str = 'app.services.upload_manager'):
        self.logger = logging.getLogger(logger_name)
        self._upload_start_time: Optional[float] = None
        self._total_files: int = 0
        self._processed_files: int = 0
        self._successful_files: int = 0
        self._failed_files: int = 0
    
    def start_upload_session(self, total_files: int, total_size: int) -> None:
        """Начало сессии загрузки"""
        self._upload_start_time = datetime.now().timestamp()
        self._total_files = total_files
        self._processed_files = 0
        self._successful_files = 0
        self._failed_files = 0
        
        import humanize
        self.logger.info(
            f"🚀 Upload session started: {total_files} files, "
            f"total size: {humanize.naturalsize(total_size)}",
            extra={'total_files': total_files, 'total_size': total_size}
        )
    
    def log_file_start(self, filename: str, file_size: int, attempt: int = 1) -> None:
        """Логирование начала загрузки файла"""
        import humanize
        self.logger.info(
            f"📤 Starting upload: {filename} ({humanize.naturalsize(file_size)}) [attempt {attempt}]",
            extra={
                'file_name': filename,
                'file_size': file_size,
                'attempt': attempt
            }
        )
    
    def log_file_success(self, filename: str, file_size: int, upload_time: float, attempt: int) -> None:
        """Логирование успешной загрузки файла"""
        import humanize
        speed = file_size / upload_time if upload_time > 0 else 0
        self._processed_files += 1
        self._successful_files += 1
        
        progress = (self._processed_files / self._total_files * 100) if self._total_files > 0 else 0
        
        self.logger.info(
            f"✅ Upload successful: {filename} "
            f"({humanize.naturalsize(file_size)} in {upload_time:.2f}s, "
            f"{humanize.naturalsize(speed)}/s) [attempt {attempt}] "
            f"[Progress: {progress:.1f}%]",
            extra={
                'file_name': filename,
                'file_size': file_size,
                'upload_time': upload_time,
                'upload_speed': speed,
                'attempt': attempt,
                'progress': progress
            }
        )
    
    def log_file_failure(self, filename: str, attempt: int, error: Optional[str] = None) -> None:
        """Логирование неудачной загрузки файла"""
        self._processed_files += 1
        self._failed_files += 1
        
        progress = (self._processed_files / self._total_files * 100) if self._total_files > 0 else 0
        
        message = f"❌ Upload failed: {filename} [attempt {attempt}] [Progress: {progress:.1f}%]"
        if error:
            message += f" - {error}"
        
        self.logger.error(
            message,
            extra={
                'file_name': filename,
                'attempt': attempt,
                'progress': progress,
                'error': error
            }
        )
    
    def log_file_retry(self, filename: str, attempt: int, retry_delay: int) -> None:
        """Логирование повторной попытки"""
        self.logger.warning(
            f"🔄 Retrying upload: {filename} [attempt {attempt + 1}] after {retry_delay}s",
            extra={
                'file_name': filename,
                'attempt': attempt + 1,
                'retry_delay': retry_delay
            }
        )
    
    def log_file_stopped(self, filename: str, reason: str = "User requested stop") -> None:
        """Логирование остановки загрузки файла"""
        self.logger.warning(
            f"⏸ Upload stopped: {filename} - {reason}",
            extra={
                'file_name': filename,
                'reason': reason
            }
        )
    
    def log_progress(self, processed: int, successful: int, failed: int, 
                    uploaded_bytes: int, total_bytes: int) -> None:
        """Логирование промежуточного прогресса"""
        if self._upload_start_time:
            elapsed = datetime.now().timestamp() - self._upload_start_time
            speed = uploaded_bytes / elapsed if elapsed > 0 else 0
            progress = (processed / self._total_files * 100) if self._total_files > 0 else 0
            
            import humanize
            self.logger.info(
                f"📊 Progress: {processed}/{self._total_files} files "
                f"({progress:.1f}%) | "
                f"✅ {successful} successful | ❌ {failed} failed | "
                f"📦 {humanize.naturalsize(uploaded_bytes)}/{humanize.naturalsize(total_bytes)} "
                f"({humanize.naturalsize(speed)}/s)",
                extra={
                    'progress': progress,
                    'processed': processed,
                    'successful': successful,
                    'failed': failed,
                    'uploaded_bytes': uploaded_bytes,
                    'total_bytes': total_bytes,
                    'upload_speed': speed,
                    'elapsed_time': elapsed
                }
            )
    
    def end_upload_session(self, successful: int, failed: int, 
                          uploaded_bytes: int, total_bytes: int) -> None:
        """Завершение сессии загрузки"""
        if self._upload_start_time:
            elapsed = datetime.now().timestamp() - self._upload_start_time
            speed = uploaded_bytes / elapsed if elapsed > 0 else 0
            
            import humanize
            success_rate = (successful / (successful + failed) * 100) if (successful + failed) > 0 else 0
            
            self.logger.info(
                f"🏁 Upload session completed: "
                f"✅ {successful} successful | ❌ {failed} failed | "
                f"📦 {humanize.naturalsize(uploaded_bytes)}/{humanize.naturalsize(total_bytes)} | "
                f"⏱ {elapsed:.2f}s | "
                f"🚀 {humanize.naturalsize(speed)}/s | "
                f"📈 Success rate: {success_rate:.1f}%",
                extra={
                    'successful': successful,
                    'failed': failed,
                    'uploaded_bytes': uploaded_bytes,
                    'total_bytes': total_bytes,
                    'elapsed_time': elapsed,
                    'upload_speed': speed,
                    'success_rate': success_rate
                }
            )


def setup_upload_logging(log_dir: str = "logs") -> None:
    """Настройка логирования для процесса загрузки"""
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    
    # Создаем отдельный файл для логов загрузки
    upload_log_file = Path(log_dir) / f"upload_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
    
    # Создаем обработчик для файла загрузки
    file_handler = logging.FileHandler(upload_log_file, encoding='utf-8')
    file_handler.setFormatter(StructuredFormatter())
    file_handler.setLevel(logging.DEBUG)
    
    # Получаем логгер для загрузки
    upload_logger = logging.getLogger('app.services.upload_manager')
    upload_logger.addHandler(file_handler)
    upload_logger.setLevel(logging.DEBUG)
    
    # Не пропагируем в корневой логгер чтобы избежать дублирования
    upload_logger.propagate = False

