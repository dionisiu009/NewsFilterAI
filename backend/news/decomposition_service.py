# ==============================================================================
# NEWSFILTERAI - TEXT DECOMPOSITION SERVICE
# ==============================================================================
# Сервіс рекурсивної декомпозиції тексту для статей,
# що перевищують ліміт токенів (>25000 символів).
# Розбиває текст на частини, стискає кожну через Gemini AI (~30%),
# зберігаючи перше та останнє речення без змін.

import logging
import re
import os
import concurrent.futures
from typing import List, Optional, Callable

logger = logging.getLogger(__name__)

# ==============================================================================
# КОНСТАНТИ
# ==============================================================================

# Поріг, після якого текст вважається "занадто великим"
DECOMPOSITION_THRESHOLD = 25000

# Цільовий розмір після стиснення (символів)
TARGET_SIZE = 20000

# Мінімальна кількість частин для розбивки
MIN_CHUNKS = 5

# Відсоток стиснення для кожного фрагмента (30%)
COMPRESSION_RATIO = 0.30

# Модель Gemini для стиснення
DECOMPOSITION_MODEL = "gemini-3.1-flash-lite-preview"

# Знаки завершення речення
SENTENCE_TERMINATORS = re.compile(r'(?<=[.!?…])\s+')

# Промпт для стиснення фрагмента тексту
COMPRESSION_PROMPT = """\
Ти — професійний редактор. Твоє завдання — скоротити наведений нижче текст приблизно на 30%, \
зберігаючи при цьому весь ключовий зміст, факти, цифри та логіку викладу.

**ПРАВИЛА:**
1. Перше речення тексту ОБОВ'ЯЗКОВО залиш без змін (слово в слово).
2. Останнє речення тексту ОБОВ'ЯЗКОВО залиш без змін (слово в слово).
3. Скорочуй лише середню частину: видаляй повтори, зайві пояснення, воду, але НЕ змінюй факти.
4. Поверни ТІЛЬКИ скорочений текст. Без коментарів, без пояснень, без маркерів.

**ТЕКСТ ДЛЯ СКОРОЧЕННЯ:**
{text}
"""


# ==============================================================================
# РОЗБИВКА ТЕКСТУ НА РЕЧЕННЯ
# ==============================================================================

def split_into_sentences(text: str) -> List[str]:
    """
    Розбиває текст на речення по знаках завершення речення:
    крапка (.), знак оклику (!), знак питання (?), трикрапка (… або ...)

    Args:
        text: Текст для розбивки

    Returns:
        Список речень
    """
    # Замінюємо три крапки на символ трикрапки для уніфікації
    normalized = text.replace('...', '…')

    # Розбиваємо по знаках завершення речення, зберігаючи знак
    # Використовуємо lookbehind для збереження розділювача
    parts = re.split(r'(?<=[.!?…])\s+', normalized)

    # Фільтруємо порожні рядки та зайві пробіли
    sentences = [s.strip() for s in parts if s.strip()]

    return sentences


# ==============================================================================
# РОЗБИВКА НА ЧАСТИНИ (CHUNKS)
# ==============================================================================

def split_text_into_chunks(text: str, min_chunks: int = MIN_CHUNKS) -> List[str]:
    """
    Розбиває текст на мінімум min_chunks частин по межах речень.

    Кожна частина закінчується на знаку завершення речення.
    Перше речення першої частини та останнє речення останньої частини
    будуть збережені AI без змін.

    Args:
        text: Текст для розбивки
        min_chunks: Мінімальна кількість частин

    Returns:
        Список текстових фрагментів
    """
    sentences = split_into_sentences(text)

    if len(sentences) <= min_chunks:
        # Якщо речень менше ніж потрібно частин — кожне речення окремий чанк
        logger.warning(
            f"Кількість речень ({len(sentences)}) <= min_chunks ({min_chunks}). "
            f"Кожне речення стає окремим чанком."
        )
        return sentences

    # Розраховуємо кількість речень на кожну частину
    sentences_per_chunk = len(sentences) // min_chunks
    remainder = len(sentences) % min_chunks

    chunks = []
    idx = 0
    for i in range(min_chunks):
        # Розподіляємо залишок рівномірно
        chunk_size = sentences_per_chunk + (1 if i < remainder else 0)
        chunk_sentences = sentences[idx:idx + chunk_size]
        chunks.append(' '.join(chunk_sentences))
        idx += chunk_size

    return chunks


# ==============================================================================
# ПЕРЕВІРКА НЕОБХІДНОСТІ ДЕКОМПОЗИЦІЇ
# ==============================================================================

def needs_decomposition(text: str) -> bool:
    """
    Перевіряє, чи потрібна декомпозиція тексту.

    Args:
        text: Текст для перевірки

    Returns:
        True якщо текст перевищує поріг DECOMPOSITION_THRESHOLD
    """
    return len(text) > DECOMPOSITION_THRESHOLD


# ==============================================================================
# СТИСНЕННЯ ОДНОГО ФРАГМЕНТА ЧЕРЕЗ AI
# ==============================================================================

def compress_chunk_via_ai(
    chunk: str,
    ai_call: Callable[[str], str],
) -> str:
    """
    Стискає один фрагмент тексту через AI.

    Args:
        chunk: Текстовий фрагмент для стиснення
        ai_call: Функція виклику AI, яка приймає промпт і повертає текст

    Returns:
        Стиснений текст фрагмента
    """
    prompt = COMPRESSION_PROMPT.format(text=chunk)

    try:
        compressed = ai_call(prompt)
        if compressed and len(compressed.strip()) > 0:
            return compressed.strip()
        else:
            logger.warning("AI повернув порожню відповідь, використовуємо оригінальний чанк")
            return chunk
    except Exception as e:
        logger.error(f"Помилка стиснення чанка через AI: {e}")
        return chunk


# ==============================================================================
# ОСНОВНИЙ СЕРВІС ДЕКОМПОЗИЦІЇ
# ==============================================================================

def decompose_text(
    text: str,
    ai_call: Callable[[str], str],
    min_chunks: int = MIN_CHUNKS,
) -> str:
    """
    Головна функція декомпозиції тексту.

    1. Перевіряє чи текст перевищує поріг (25000 символів).
    2. Розбиває текст на min_chunks частин по межах речень.
    3. Відправляє кожну частину в Gemini AI для стиснення на ~30%.
    4. Збирає результат назад в один текст.

    Args:
        text: Повний текст статті
        ai_call: Функція виклику AI (prompt -> response_text)
        min_chunks: Мінімальна кількість частин

    Returns:
        Стиснений текст або оригінал (якщо декомпозиція не потрібна)
    """
    if not needs_decomposition(text):
        logger.info(
            f"Текст не потребує декомпозиції "
            f"({len(text)} символів < {DECOMPOSITION_THRESHOLD})"
        )
        return text

    logger.info(
        f"Запуск декомпозиції: {len(text)} символів, "
        f"поріг: {DECOMPOSITION_THRESHOLD}, мін. частин: {min_chunks}"
    )

    # 1. Розбиваємо текст на частини
    chunks = split_text_into_chunks(text, min_chunks=min_chunks)
    logger.info(f"Текст розбито на {len(chunks)} частин")

    for i, chunk in enumerate(chunks):
        logger.debug(f"Чанк {i+1}: {len(chunk)} символів, {len(split_into_sentences(chunk))} речень")

    # 2. Стискаємо кожну частину паралельно
    compressed_chunks = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(chunks)) as executor:
        future_to_idx = {
            executor.submit(compress_chunk_via_ai, chunk, ai_call): i
            for i, chunk in enumerate(chunks)
        }

        # Збираємо результати у правильному порядку
        results = [None] * len(chunks)
        for future in concurrent.futures.as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                results[idx] = future.result()
            except Exception as e:
                logger.error(f"Помилка обробки чанка {idx}: {e}")
                results[idx] = chunks[idx]  # Fallback: оригінальний чанк

        compressed_chunks = results

    # 3. Збираємо назад в один текст
    result = '\n\n'.join(compressed_chunks)

    original_len = len(text)
    compressed_len = len(result)
    reduction = ((original_len - compressed_len) / original_len) * 100

    logger.info(
        f"Декомпозиція завершена: {original_len} -> {compressed_len} символів "
        f"(скорочення {reduction:.1f}%)"
    )

    return result
