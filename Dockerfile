# Dockerfile для деплоя на Timeweb
FROM python:3.10-slim

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Создаем рабочую директорию
WORKDIR /app

# Копируем requirements.txt и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код приложения
COPY . .

# Создаем папки для отчетов
RUN mkdir -p reports/charts

# Открываем порт
EXPOSE 8000

# Запускаем приложение
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
