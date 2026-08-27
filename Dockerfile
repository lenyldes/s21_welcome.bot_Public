FROM python:3.12-slim

WORKDIR /app

# Установка зависимостей
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Копирование исходного кода и ресурсов
COPY src/ ./src/
COPY assets/ ./assets/

# Создание директорий для персистентных данных и логов
RUN mkdir -p /app/data /app/logs

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

CMD ["python3", "src/main.py"]
