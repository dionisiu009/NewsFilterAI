# ==============================================================================
# TC-MOD-03: Тестування локального мікросервісу рекурсивної декомпозиції
#             на текстах, що перевищують ліміт токенів.
# ==============================================================================

import pytest
from unittest.mock import MagicMock, patch, call

from news.decomposition_service import (
    split_into_sentences,
    split_text_into_chunks,
    needs_decomposition,
    compress_chunk_via_ai,
    decompose_text,
    DECOMPOSITION_THRESHOLD,
    TARGET_SIZE,
    MIN_CHUNKS,
    COMPRESSION_RATIO,
)


def make_long_text(char_count: int, sentence_len: int = 80) -> str:
    """
    Генерує текст потрібної довжини, що складається з повноцінних речень,
    кожне з яких закінчується крапкою.
    """
    base_sentence = "Це тестове речення для перевірки декомпозиції тексту номер"
    sentences = []
    current_len = 0
    i = 1
    while current_len < char_count:
        s = f"{base_sentence} {i}."
        sentences.append(s)
        current_len += len(s) + 1  # +1 за пробіл між реченнями
        i += 1
    return ' '.join(sentences)[:char_count]


def make_text_with_terminators() -> str:
    """Текст із різними знаками завершення речення."""
    return (
        "Перше речення закінчується крапкою. "
        "Друге речення із знаком оклику! "
        "Третє речення із знаком питання? "
        "Четверте речення із трикрапкою… "
        "П'яте речення із трьома крапками... "
        "Шосте речення. "
        "Сьоме речення! "
        "Восьме речення? "
        "Дев'яте речення. "
        "Десяте речення."
    )

class TestSplitIntoSentences:
    """Тести розбивки тексту на речення."""

    def test_split_by_period(self):
        """Розбивка по крапці."""
        text = "Перше речення. Друге речення. Третє речення."
        result = split_into_sentences(text)
        assert len(result) == 3
        assert result[0] == "Перше речення."
        assert result[1] == "Друге речення."
        assert result[2] == "Третє речення."

    def test_split_by_exclamation(self):
        """Розбивка по знаку оклику."""
        text = "Увага! Це важливо! Зрозуміло."
        result = split_into_sentences(text)
        assert len(result) == 3

    def test_split_by_question(self):
        """Розбивка по знаку питання."""
        text = "Що це? Як працює? Дуже просто."
        result = split_into_sentences(text)
        assert len(result) == 3

    def test_split_by_ellipsis(self):
        """Розбивка по трикрапці (…)."""
        text = "Він думав… Потім зрозумів. Все просто."
        result = split_into_sentences(text)
        assert len(result) == 3

    def test_split_by_three_dots(self):
        """Розбивка по трьох крапках (...)."""
        text = "Він думав... Потім зрозумів. Все просто."
        result = split_into_sentences(text)
        assert len(result) == 3

    def test_mixed_terminators(self):
        """Розбивка з різними знаками завершення."""
        text = make_text_with_terminators()
        result = split_into_sentences(text)
        assert len(result) == 10

    def test_empty_text(self):
        """Порожній текст."""
        result = split_into_sentences("")
        assert result == []

    def test_single_sentence(self):
        """Одне речення."""
        result = split_into_sentences("Одне речення.")
        assert len(result) == 1
        assert result[0] == "Одне речення."

    def test_preserves_sentence_content(self):
        """Зміст речень не змінюється (скорочення типу 'тис.' сприймаються як кінець речення)."""
        text = "Факт: 13,7 тис. міжз'єднань. Пропускна здатність — 5,3 ТБ/с."
        result = split_into_sentences(text)
        # "тис." та "міжз'єднань." та "ТБ/с." — три крапки завершення
        assert len(result) == 3
        assert "13,7" in result[0]
        assert "5,3 ТБ/с" in result[2]

class TestSplitTextIntoChunks:
    """Тести розбивки тексту на частини."""

    def test_minimum_chunks_count(self):
        """Кількість частин >= MIN_CHUNKS."""
        text = make_text_with_terminators()
        chunks = split_text_into_chunks(text, min_chunks=5)
        assert len(chunks) >= 5

    def test_chunks_cover_all_text(self):
        """Всі речення присутні в частинах."""
        text = make_text_with_terminators()
        sentences = split_into_sentences(text)
        chunks = split_text_into_chunks(text, min_chunks=3)

        # Перевіряємо, що кожне речення є хоча б в одному чанку
        all_chunks_text = ' '.join(chunks)
        for sentence in sentences:
            assert sentence in all_chunks_text, f"Речення '{sentence}' не знайдено в чанках"

    def test_each_chunk_ends_with_sentence_terminator(self):
        """Кожна частина закінчується знаком завершення речення."""
        text = make_text_with_terminators()
        chunks = split_text_into_chunks(text, min_chunks=5)

        terminators = {'.', '!', '?', '…'}
        for i, chunk in enumerate(chunks):
            last_char = chunk.strip()[-1]
            assert last_char in terminators, (
                f"Чанк {i} не закінчується знаком завершення: '{chunk[-20:]}'"
            )

    def test_few_sentences_fallback(self):
        """Якщо речень менше min_chunks — кожне речення стає окремим чанком."""
        text = "Перше. Друге. Третє."
        chunks = split_text_into_chunks(text, min_chunks=10)
        assert len(chunks) == 3  # Кожне речення — окремий чанк

    def test_exact_split(self):
        """Рівний розподіл речень по чанках."""
        text = "A. B. C. D. E. F. G. H. I. J."
        chunks = split_text_into_chunks(text, min_chunks=5)
        assert len(chunks) == 5
        # 10 речень / 5 чанків = 2 речення на чанк
        for chunk in chunks:
            sentences_in_chunk = split_into_sentences(chunk)
            assert len(sentences_in_chunk) == 2

class TestNeedsDecomposition:
    """Тести визначення необхідності декомпозиції."""

    def test_short_text_no_decomposition(self):
        """Короткий текст НЕ потребує декомпозиції."""
        text = "Короткий текст."
        assert needs_decomposition(text) is False

    def test_threshold_exact_no_decomposition(self):
        """Текст рівно на порозі НЕ потребує декомпозиції."""
        text = "A" * DECOMPOSITION_THRESHOLD
        assert needs_decomposition(text) is False

    def test_above_threshold_needs_decomposition(self):
        """Текст вище порогу ПОТРЕБУЄ декомпозиції."""
        text = "A" * (DECOMPOSITION_THRESHOLD + 1)
        assert needs_decomposition(text) is True

    def test_empty_text_no_decomposition(self):
        """Порожній текст НЕ потребує декомпозиції."""
        assert needs_decomposition("") is False

    def test_threshold_value(self):
        """Поріг декомпозиції = 25000 символів."""
        assert DECOMPOSITION_THRESHOLD == 25000

class TestCompressChunkViaAI:
    """Тести стиснення одного фрагмента через AI."""

    def test_successful_compression(self):
        """AI повертає стиснений текст."""
        chunk = "Це довгий фрагмент тексту для стиснення. Він має кілька речень."
        mock_ai = MagicMock(return_value="Це стиснений фрагмент.")

        result = compress_chunk_via_ai(chunk, mock_ai)

        assert result == "Це стиснений фрагмент."
        mock_ai.assert_called_once()

    def test_ai_returns_empty_fallback(self):
        """Якщо AI повертає порожню відповідь — використовуємо оригінал."""
        chunk = "Оригінальний текст."
        mock_ai = MagicMock(return_value="")

        result = compress_chunk_via_ai(chunk, mock_ai)

        assert result == chunk

    def test_ai_returns_none_fallback(self):
        """Якщо AI повертає None — використовуємо оригінал."""
        chunk = "Оригінальний текст."
        mock_ai = MagicMock(return_value=None)

        result = compress_chunk_via_ai(chunk, mock_ai)

        assert result == chunk

    def test_ai_raises_exception_fallback(self):
        """Якщо AI кидає помилку — використовуємо оригінал."""
        chunk = "Оригінальний текст."
        mock_ai = MagicMock(side_effect=RuntimeError("AI error"))

        result = compress_chunk_via_ai(chunk, mock_ai)

        assert result == chunk

    def test_prompt_contains_text(self):
        """Промпт містить оригінальний текст."""
        chunk = "Дуже специфічний текст XYZ123."
        mock_ai = MagicMock(return_value="Стиснений.")

        compress_chunk_via_ai(chunk, mock_ai)

        call_args = mock_ai.call_args[0][0]
        assert "XYZ123" in call_args

    def test_prompt_contains_instructions(self):
        """Промпт містить інструкції про збереження першого/останнього речення."""
        chunk = "Перше речення. Середина. Останнє речення."
        mock_ai = MagicMock(return_value="Стиснений.")

        compress_chunk_via_ai(chunk, mock_ai)

        call_args = mock_ai.call_args[0][0]
        assert "Перше речення" in call_args
        assert "30%" in call_args

class TestDecomposeText:
    """Інтеграційні тести повного процесу декомпозиції."""

    def test_short_text_returns_as_is(self):
        """Текст менше порогу повертається без змін."""
        text = "Короткий текст статті."
        mock_ai = MagicMock()

        result = decompose_text(text, mock_ai)

        assert result == text
        mock_ai.assert_not_called()

    def test_long_text_triggers_decomposition(self):
        """Текст вище порогу запускає декомпозицію."""
        text = make_long_text(30000)
        mock_ai = MagicMock(side_effect=lambda prompt: "Стиснений фрагмент.")

        result = decompose_text(text, mock_ai)

        assert mock_ai.call_count >= MIN_CHUNKS

    def test_long_text_calls_ai_for_each_chunk(self):
        """AI викликається для кожного чанка."""
        text = make_long_text(30000)

        call_count = 0
        def fake_ai(prompt):
            nonlocal call_count
            call_count += 1
            return f"Стиснений блок {call_count}."

        result = decompose_text(text, fake_ai, min_chunks=5)

        assert call_count == 5

    def test_result_is_shorter_than_original(self):
        """Результат коротший за оригінал (при нормальній роботі AI)."""
        text = make_long_text(30000)

        def fake_ai(prompt):
            # Імітуємо стиснення на ~30%
            # Витягуємо текст з промпту
            lines = prompt.split("**ТЕКСТ ДЛЯ СКОРОЧЕННЯ:**\n")
            if len(lines) > 1:
                original = lines[1]
                return original[:int(len(original) * 0.7)]
            return "Стиснений."

        result = decompose_text(text, fake_ai)

        assert len(result) < len(text)

    def test_ai_failure_preserves_original_chunks(self):
        """Якщо AI падає — оригінальні чанки зберігаються."""
        text = make_long_text(30000)
        mock_ai = MagicMock(side_effect=RuntimeError("Connection error"))

        result = decompose_text(text, mock_ai)

        # Результат не повинен бути порожнім — fallback на оригінальні чанки
        assert len(result) > 0

    def test_threshold_boundary(self):
        """Текст рівно на порозі НЕ декомпозується."""
        text = make_long_text(DECOMPOSITION_THRESHOLD)
        mock_ai = MagicMock()

        result = decompose_text(text, mock_ai)

        mock_ai.assert_not_called()

    def test_min_chunks_parameter(self):
        """Параметр min_chunks керує кількістю частин."""
        text = make_long_text(30000)

        call_count = 0
        def fake_ai(prompt):
            nonlocal call_count
            call_count += 1
            return f"Блок {call_count}."

        decompose_text(text, fake_ai, min_chunks=7)

        assert call_count == 7

    def test_result_contains_compressed_parts(self):
        """Результат складається з стиснених частин, з'єднаних разом."""
        text = make_long_text(30000)

        counter = 0
        def fake_ai(prompt):
            nonlocal counter
            counter += 1
            return f"ЧАСТИНА_{counter}_СТИСНЕНА."

        result = decompose_text(text, fake_ai, min_chunks=5)

        for i in range(1, 6):
            assert f"ЧАСТИНА_{i}_СТИСНЕНА" in result

    def test_constants_are_correct(self):
        """Перевірка значень констант."""
        assert DECOMPOSITION_THRESHOLD == 25000
        assert TARGET_SIZE == 20000
        assert MIN_CHUNKS == 5
        assert COMPRESSION_RATIO == 0.30
