#!/usr/bin/env python
"""
Тест отримання часу з інтернету
"""
import sys
import os
import django

# Налаштовуємо Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from news.ai_service import get_current_time_from_internet
from datetime import datetime, timezone

print("=" * 70)
print("Тест отримання часу з інтернету")
print("=" * 70)

# Системний час
system_time = datetime.now(timezone.utc)
print(f"\n🖥️  Системний час (UTC): {system_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")

# Час з інтернету
internet_time = get_current_time_from_internet()
print(f"🌐 Час з інтернету (UTC): {internet_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")

# Різниця
diff = abs((internet_time - system_time).total_seconds())
print(f"\n⏱️  Різниця: {diff:.1f} секунд")

if diff > 60:
    print("⚠️  УВАГА: Системний час відрізняється від інтернет-часу більше ніж на 1 хвилину!")
else:
    print("✅ Системний час налаштований правильно")

# Форматування для AI
months_uk = [
    'січня', 'лютого', 'березня', 'квітня', 'травня', 'червня',
    'липня', 'серпня', 'вересня', 'жовтня', 'листопада', 'грудня'
]
ai_date_str = f"{internet_time.day} {months_uk[internet_time.month - 1]} {internet_time.year} року, {internet_time.strftime('%H:%M')} UTC"

print("\n" + "=" * 70)
print("Дата, яка буде передана AI:")
print("=" * 70)
print(ai_date_str)
print("=" * 70)
