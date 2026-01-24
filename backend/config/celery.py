# ==============================================================================
# NEWSFILTERAI - CELERY CONFIGURATION
# ==============================================================================

import os
from celery import Celery
from django.conf import settings

# Встановлюємо налаштування Django для Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Створюємо екземпляр Celery
app = Celery('newsfilter')

# Завантажуємо налаштування з Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Автоматично знаходимо задачі в усіх зареєстрованих Django apps
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Тестова задача для перевірки роботи Celery."""
    print(f'Request: {self.request!r}')

