import logging
from datetime import datetime

class WebLogHandler(logging.Handler):
    """Обработчик логов для отправки в веб-интерфейс через SocketIO"""
    
    def __init__(self, socketio):
        super().__init__()
        self.socketio = socketio
        self.last_messages = set()
    
    def emit(self, record):
        try:
            # Фильтруем ненужные логи и дубликаты
            message = self.format(record)
            
            # Пропускаем статические файлы и дубликаты
            if any(x in message for x in ['GET /static/', 'GET /favicon.ico', 'POST /socket.io/']):
                return
                
            # Отправляем только важные логи в веб-интерфейс
            if record.levelno >= logging.INFO:
                # Убираем временные метки для веб-интерфейса
                clean_message = message
                if ']' in clean_message:
                    clean_message = clean_message.split(']', 1)[1].strip()
                
                self.socketio.emit('log_message', {
                    'message': clean_message,
                    'level': record.levelname.lower(),
                    'timestamp': datetime.now().strftime('%H:%M:%S')
                })
        except Exception as e:
            print(f"Error sending log to web: {e}")