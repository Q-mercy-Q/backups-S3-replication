FROM python:3.9-slim

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    nfs-common \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Создание директории приложения
WORKDIR /app

# Копирование requirements и установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода
COPY . .

# Создание директорий для данных и логов
RUN mkdir -p data logs

# Открытие порта
EXPOSE 5000

# Переменные окружения
ENV PYTHONPATH=/app
ENV FLASK_APP=app/web/app.py
ENV FLASK_ENV=production

# Запуск приложения
CMD ["python", "run.py"]