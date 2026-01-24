#!/usr/bin/env python
"""Тест отримання часу з інтернету в Docker"""
import sys
import os
import django

sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from news.ai_service import get_current_time_from_internet

print('=' * 70)
print('🐳 Тест отримання часу з інтернету в Docker контейнері')
print('=' * 70)

dt = get_current_time_from_internet()
print(f'✅ Отримано: {dt}')

months_uk = [
    'січня', 'лютого', 'березня', 'квітня', 'травня', 'червня',
    'липня', 'серпня', 'вересня', 'жовтня', 'листопада', 'грудня'
]
formatted = f"{dt.day} {months_uk[dt.month - 1]} {dt.year} року, {dt.strftime('%H:%M')} UTC"
print(f'📅 Форматована дата для AI: {formatted}')
print('=' * 70)
