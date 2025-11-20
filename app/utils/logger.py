"""
Logging configuration for S3 Backup Manager
"""

import logging
import os
from datetime import datetime

def setup_logging():
    """Настройка централизованного логирования"""
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    # Форматтер для логов
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Обработчик для файла
    file_handler = logging.FileHandler(
        f"{log_dir}/app_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
    )
    file_handler.setFormatter(formatter)
    
    # Обработчик для консоли
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # Настраиваем корневой логгер
    logging.basicConfig(
        level=logging.INFO,
        handlers=[file_handler, console_handler],
        force=True
    )
    
    # Отключаем лишние логи Flask и SocketIO
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('engineio').setLevel(logging.WARNING)
    logging.getLogger('socketio').setLevel(logging.WARNING)