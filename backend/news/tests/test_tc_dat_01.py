# ==============================================================================
# TC-DAT-01: Валідація структури витягнутих інтентів (Stage 1)
# ==============================================================================
# Цей тест гарантує, що Gemini завжди повертає валідний масив інтентів,
# і їх кількість знаходиться в межах від 2 до 6, як вказано в документації.

import pytest
import json
from unittest.mock import patch, MagicMock
from news.council_pipeline import stage_1_extract_intents

# Тестові дані
NEWS_TITLE = "Тестова новина про янтарь в Антарктиді"
NEWS_CONTENT = "Короткий зміст новини для тестування Stage 1."
API_KEY = "dummy_key"

def mock_gemini_response(payload):
    """Допоміжна функція для створення моку відповіді Gemini"""
    mock_resp = MagicMock()
    mock_resp.text = json.dumps(payload)
    return mock_resp

def test_stage_1_valid_extraction():
    """
    TC-DAT-01 / Valid: Перевірка успішного витягування 3 інтентів.
    """
    valid_payload = {
        "intents": [
            {"intent_id": "i1", "intent": "Claim 1", "search_guidance": "G1"},
            {"intent_id": "i2", "intent": "Claim 2", "search_guidance": "G2"},
            {"intent_id": "i3", "intent": "Claim 3", "search_guidance": "G3"}
        ]
    }
    
    with patch("news.council_pipeline.genai.Client") as MockClient:
        instance = MockClient.return_value
        instance.models.generate_content.return_value = mock_gemini_response(valid_payload)
        
        intents = stage_1_extract_intents(NEWS_TITLE, NEWS_CONTENT, API_KEY)
        
        assert isinstance(intents, list)
        assert 2 <= len(intents) <= 6
        assert len(intents) == 3
        assert intents[0]["intent"] == "Claim 1"

def test_stage_1_enforces_max_limit():
    """
    TC-DAT-01 / Max-Limit: Якщо Gemini поверне 10 інтентів, 
    система має обрізати їх до 6.
    """
    overlimit_payload = {
        "intents": [{"intent_id": f"i{i}", "intent": f"Claim {i}"} for i in range(1, 11)]
    }
    
    with patch("news.council_pipeline.genai.Client") as MockClient:
        instance = MockClient.return_value
        instance.models.generate_content.return_value = mock_gemini_response(overlimit_payload)
        
        intents = stage_1_extract_intents(NEWS_TITLE, NEWS_CONTENT, API_KEY)
        
        # Перевіряємо ліміт у 6 інтентів
        assert len(intents) == 6
        assert intents[-1]["intent_id"] == "i6"

def test_stage_1_raises_error_on_too_few_intents():
    """
    TC-DAT-01 / Min-Limit: Якщо Gemini поверне лише 1 інтент,
    має виникнути RuntimeError (пайплайн зупиняється).
    """
    underlimit_payload = {
        "intents": [{"intent_id": "i1", "intent": "Only one claim"}]
    }
    
    with patch("news.council_pipeline.genai.Client") as MockClient:
        instance = MockClient.return_value
        instance.models.generate_content.return_value = mock_gemini_response(underlimit_payload)
        
        with pytest.raises(RuntimeError) as excinfo:
            stage_1_extract_intents(NEWS_TITLE, NEWS_CONTENT, API_KEY)
        
        assert "expected 2-6 intents, got 1" in str(excinfo.value)

def test_stage_1_handles_malformed_json():
    """
    TC-DAT-01 / Malformed: Перевірка поведінки при отриманні 
    невалідного JSON або пустого списку.
    """
    malformed_responses = [
        "Not a JSON at all",
        {"not_intents": []},
        {"intents": "not a list"}
    ]
    
    with patch("news.council_pipeline.genai.Client") as MockClient:
        instance = MockClient.return_value
        
        for resp_text in malformed_responses:
            mock_resp = MagicMock()
            mock_resp.text = json.dumps(resp_text) if isinstance(resp_text, dict) else resp_text
            instance.models.generate_content.return_value = mock_resp
            
            with pytest.raises(RuntimeError):
                stage_1_extract_intents(NEWS_TITLE, NEWS_CONTENT, API_KEY)

def test_stage_1_normalizes_missing_fields():
    """
    TC-DAT-01 / Normalization: Перевірка, що відсутні поля 
    (наприклад, intent_id або guidance) заповнюються дефолтними значеннями.
    """
    messy_payload = {
        "intents": [
            {"intent": "Claim without ID"},
            {"intent_id": "i2", "intent": "Claim without guidance"}
        ]
    }
    
    with patch("news.council_pipeline.genai.Client") as MockClient:
        instance = MockClient.return_value
        instance.models.generate_content.return_value = mock_gemini_response(messy_payload)
        
        intents = stage_1_extract_intents(NEWS_TITLE, NEWS_CONTENT, API_KEY)
        
        assert len(intents) == 2
        # Автоматична генерація ID
        assert "intent_id" in intents[0]
        # Дефолтний guidance (перевіряємо логіку в коді)
        assert "search_guidance" in intents[1]
        assert len(intents[1]["search_guidance"]) > 0
