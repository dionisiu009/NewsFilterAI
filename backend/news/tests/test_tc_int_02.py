# ==============================================================================
# TC-INT-02: Симуляція розриву з'єднання
# ==============================================================================
# Перевіряє стабільність роботи та спрацювання механізму повторних спроб (Retry)
# при зверненні до зовнішніх API Groq та Google Gemini.
#
# Покриті сценарії:
#   1. Groq: 2 розриви з'єднання → 1 успіх (retry відпрацьовує)
#   2. Groq: всі спроби вичерпані → повернення рядка з [ERROR]
#   3. Gemini worker: 3 помилки → 1 успіх
#   4. Gemini Judge (Stage 5): 1 помилка → 1 успіх
#   5. _gemini_runner.py subprocess: краш процесу → error-відповідь без виключень

import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from news.council_pipeline import (
    _call_groq_worker,
    _call_gemini_worker,
    stage_5_judge_synthesis,
)


_GROQ_KEY   = "dummy_groq_api_key"
_GEMINI_KEY = "dummy_gemini_api_key"
_SYS        = "You are a fact-checker."
_USER       = "Check this news article."


@pytest.mark.asyncio
async def test_groq_retry_recovers_after_connection_errors():
    """
    TC-INT-02 / Groq / Retry-Success:
    Перші 2 виклики до Groq API імітують розрив з'єднання.
    3-й виклик повертає успішну відповідь.
    Очікуємо: результат == "SUCCESS", кількість викликів == 3, sleep == 2.
    """
    with patch("groq.AsyncGroq") as MockGroq:
        mock_completions = MagicMock()
        mock_completions.create = AsyncMock(side_effect=[
            ConnectionError("Connection lost"),
            TimeoutError("Request timed out"),
            MagicMock(choices=[MagicMock(message=MagicMock(content="SUCCESS"))]),
        ])

        mock_client = MagicMock()
        mock_client.chat.completions = mock_completions
        MockGroq.return_value = mock_client

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await _call_groq_worker(_GROQ_KEY, _SYS, _USER)

    assert result == "SUCCESS", f"Очікували 'SUCCESS', отримали: {result!r}"
    assert mock_completions.create.call_count == 3, "Має бути рівно 3 виклики до API"
    assert mock_sleep.call_count == 2, "Має бути 2 паузи між спробами"


@pytest.mark.asyncio
async def test_groq_all_retries_exhausted_returns_error_string():
    """
    TC-INT-02 / Groq / All-Retries-Exhausted:
    Всі MAX_RETRIES (5) викликів завершуються помилкою.
    Очікуємо: функція НЕ кидає виключення, а повертає рядок з "[ERROR]".
    """
    with patch("groq.AsyncGroq") as MockGroq:
        mock_completions = MagicMock()
        # Завжди помилка
        mock_completions.create = AsyncMock(
            side_effect=ConnectionError("Persistent network failure")
        )

        mock_client = MagicMock()
        mock_client.chat.completions = mock_completions
        MockGroq.return_value = mock_client

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await _call_groq_worker(_GROQ_KEY, _SYS, _USER)

    assert "[ERROR]" in result, f"Очікували рядок з [ERROR], отримали: {result!r}"
    assert mock_completions.create.call_count == 5, "Має бути рівно 5 спроб (MAX_RETRIES)"


@pytest.mark.asyncio
async def test_gemini_worker_retry_recovers_after_api_errors():
    """
    TC-INT-02 / Gemini / Worker-Retry:
    Перші 3 виклики до Google Gemini API повертають помилки (503, reset, timeout).
    4-й виклик повертає успішну відповідь.
    Очікуємо: результат == "GEMINI_SUCCESS", 4 виклики, 3 паузи.
    """
    with patch("news.council_pipeline.genai.Client") as MockClient:
        mock_models = MagicMock()
        mock_models.generate_content.side_effect = [
            Exception("503 Service Unavailable"),
            Exception("Connection reset by peer"),
            Exception("DeadlineExceeded: timeout"),
            MagicMock(text="GEMINI_SUCCESS"),
        ]

        mock_client_instance = MagicMock()
        mock_client_instance.models = mock_models
        MockClient.return_value = mock_client_instance

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await _call_gemini_worker(_GEMINI_KEY, _SYS, _USER)

    assert result == "GEMINI_SUCCESS"
    assert mock_models.generate_content.call_count == 4
    assert mock_sleep.call_count == 3


@pytest.mark.asyncio
async def test_gemini_judge_retry_on_connection_error():
    """
    TC-INT-02 / Gemini / Judge-Stage5-Retry:
    Перший виклик до Gemini Judge (Stage 5) повертає 503.
    Другий виклик повертає валідний JSON-вердикт.
    Очікуємо: вердикт == "fact", 2 виклики, 1 пауза.
    """
    valid_response = json.dumps({
        "final_verdict": "fact",
        "overall_summary": "Тестовий підсумок",
        "intents_analysis": [],
    })

    with patch("news.council_pipeline.genai.Client") as MockClient:
        mock_models = MagicMock()
        mock_models.generate_content.side_effect = [
            Exception("503 Service Unavailable"),
            MagicMock(text=valid_response),
        ]

        mock_client_instance = MagicMock()
        mock_client_instance.models = mock_models
        MockClient.return_value = mock_client_instance

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await stage_5_judge_synthesis(
                news_title="Test Title",
                news_content="Test content",
                intents=[],
                top_articles=[],
                workers_data={},
                judge_api_key=_GEMINI_KEY,
            )

    assert result["final_verdict"] == "fact"
    assert mock_models.generate_content.call_count == 2
    assert mock_sleep.call_count == 1


def test_gemini_runner_subprocess_crash_returns_error_verdict():
    """
    TC-INT-02 / GeminiAIService / Subprocess-Crash:
    _gemini_runner.py запускається через subprocess.run.
    Симулюємо краш (returncode=3, stderr=b'Connection reset by peer').
    Очікуємо: сервіс НЕ кидає виключення, verdict == 'error',
    а в summary міститься повідомлення про помилку.
    """
    mock_settings = MagicMock()
    mock_settings.GEMINI_API_KEY = "dummy_key"
    mock_settings.GEMINI_MODEL_NAME = "gemini-2.5-flash"

    with patch("news.ai_service.settings", mock_settings):
        from news.ai_service import GeminiAIService
        service = GeminiAIService()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=3,
                stdout=b"",
                stderr=b"Connection reset by peer",
            )
            with patch("news.ai_service.get_current_time_from_internet") as mock_time:
                from datetime import datetime, timezone
                mock_time.return_value = datetime(2026, 5, 7, 12, 0, 0, tzinfo=timezone.utc)

                result = service.verify_news(
                    title="Test Title",
                    content="Test news content",
                    url="http://example.com/test",
                )

    assert result["verdict"] == "error", f"Очікували 'error', отримали: {result['verdict']!r}"
    assert result.get("error") is True, "Поле 'error' має бути True"
    assert "Connection reset by peer" in result.get("summary", ""), (
        "summary повинен містити повідомлення про помилку з'єднання"
    )
