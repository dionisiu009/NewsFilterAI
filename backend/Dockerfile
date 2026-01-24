# ==============================================================================
# NEWSFILTERAI - BACKEND DOCKERFILE (Universal)
# ==============================================================================
# Цей Dockerfile використовується для:
# - Django Backend (Gunicorn)
# - Celery Worker
# - Telegram Bot (Aiogram)
# ==============================================================================

FROM python:3.11-slim

# Встановлюємо змінні середовища
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Встановлюємо системні залежності
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Для psycopg2
    libpq-dev \
    gcc \
    # Для newspaper3k (парсинг статей)
    libxml2-dev \
    libxslt1-dev \
    libjpeg-dev \
    zlib1g-dev \
    libpng-dev \
    # Для lxml
    python3-dev \
    # Очищення кешу apt
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Створюємо робочу директорію
WORKDIR /app

# Копіюємо файл залежностей
COPY requirements.txt .

# Встановлюємо Python залежності
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Копіюємо весь код проєкту
COPY . .

# Створюємо директорію для статичних файлів та збираємо їх
RUN mkdir -p /app/staticfiles && \
    python manage.py collectstatic --noinput

# Створюємо непривілейованого користувача для безпеки
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app
USER appuser

# Порт для Gunicorn (Django)
EXPOSE 8000

# За замовчуванням запускаємо Gunicorn
# (перевизначається в docker-compose.yml для Celery та Telegram Bot)
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]

