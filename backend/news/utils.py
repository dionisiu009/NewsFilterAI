# ==============================================================================
# NEWSFILTERAI - UTILITY FUNCTIONS
# ==============================================================================
# Допоміжні функції для модуля news

import hashlib
import re
from urllib.parse import urlparse
from typing import Optional


def normalize_domain(domain: str) -> str:
    """
    Нормалізує домен: lowercase, без www.

    Args:
        domain: Домен для нормалізації (наприклад: 'WWW.Example.Com')

    Returns:
        Нормалізований домен ('example.com')
    """
    domain = domain.lower().strip()
    if domain.startswith('www.'):
        domain = domain[4:]
    return domain


def extract_domain(url: str) -> str:
    """
    Витягує та нормалізує домен з URL.

    Args:
        url: Повний URL (наприклад: 'https://www.example.com/page')

    Returns:
        Нормалізований домен ('example.com')
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    except Exception:
        return ''


def generate_url_hash(url: str) -> str:
    """
    Генерує SHA-256 hash для URL.

    Args:
        url: URL для хешування

    Returns:
        64-символьний hex hash
    """
    return hashlib.sha256(url.encode('utf-8')).hexdigest()


def clean_text(text: str) -> str:
    """
    Очищає текст від зайвих символів та нормалізує пробіли.

    Args:
        text: Текст для очищення

    Returns:
        Очищений текст
    """
    if not text:
        return ''

    # Видаляємо зайві пробіли та переноси рядків
    text = re.sub(r'\s+', ' ', text)

    # Видаляємо нульові символи
    text = text.replace('\x00', '')

    # Видаляємо керуючі символи (крім пробілу та нового рядка)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

    return text.strip()


def truncate_text(text: str, max_length: int, suffix: str = '...') -> str:
    """
    Обрізає текст до вказаної довжини.

    Args:
        text: Текст для обрізання
        max_length: Максимальна довжина
        suffix: Суфікс для обрізаного тексту

    Returns:
        Обрізаний текст
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def is_valid_url(url: str) -> bool:
    """
    Перевіряє чи URL валідний.

    Args:
        url: URL для перевірки

    Returns:
        True якщо URL валідний
    """
    try:
        parsed = urlparse(url)
        return bool(parsed.scheme and parsed.netloc)
    except Exception:
        return False


def clean_url(url: str) -> str:
    """
    Очищає URL від зайвих символів.

    Args:
        url: URL для очищення

    Returns:
        Очищений URL
    """
    url = url.strip()
    # Видаляємо можливі зайві символи в кінці
    url = url.rstrip('.,;:!?)')
    return url

