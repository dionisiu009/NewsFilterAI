"""
Команда для автоматичного створення суперкористувача Django.
Використовує змінні середовища з .env файлу.
"""
import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = 'Створює суперкористувача з змінних середовища, якщо він ще не існує'

    def handle(self, *args, **options):
        User = get_user_model()

        username = os.environ.get('DJANGO_SUPERUSER_USERNAME')
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL')
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')

        if not all([username, email, password]):
            self.stdout.write(
                self.style.WARNING(
                    'Змінні середовища DJANGO_SUPERUSER_USERNAME, '
                    'DJANGO_SUPERUSER_EMAIL та DJANGO_SUPERUSER_PASSWORD не встановлені. '
                    'Суперкористувача не створено.'
                )
            )
            return

        if not User.objects.filter(username=username).exists():
            User.objects.create_superuser(
                username=username,
                email=email,
                password=password
            )
            self.stdout.write(
                self.style.SUCCESS(f'Суперкористувача успішно створено!')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'Суперкористувач "{username}" вже існує.')
            )

