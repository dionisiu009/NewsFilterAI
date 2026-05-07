# ==============================================================================
# TC-DAT-02: Валідація фінального вердикту (Stage 5)
# ==============================================================================
# Перевіряє поле final_verdict на строгу відповідність семи дозволеним 
# категоріям класифікації та роботу механізму Retry при помилках.

import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock
from news.council_pipeline import stage_5_judge_synthesis

# Валідні категорії
VALID_VERDICTS = ["fact", "partial", "false-fake", "clickbait", "opinion", "satire", "unverifiable"]

@pytest.mark.asyncio
async def test_stage_5_valid_verdicts():
    """
    TC-DAT-02 / Valid-Verdicts: Перевірка, що система приймає 
    кожен з дозволених вердиктів.
    """
    for expected_verdict in VALID_VERDICTS:
        payload = {
            "final_verdict": expected_verdict,
            "overall_summary": "Тестовий підсумок",
            "intents_analysis": []
        }
        
        with patch("news.council_pipeline.genai.Client") as MockClient:
            instance = MockClient.return_value
            mock_resp = MagicMock()
            mock_resp.text = json.dumps(payload)
            instance.models.generate_content.return_value = mock_resp
            
            result = await stage_5_judge_synthesis("T", "C", [], [], {}, "key")
            
            assert result["final_verdict"] == expected_verdict

@pytest.mark.asyncio
async def test_stage_5_retries_on_invalid_verdict():
    """
    TC-DAT-02 / Retry-Invalid: Якщо нейронка поверне "fake" (невалідний), 
    система має зробити повторний запит і прийняти "false-fake" (валідний).
    """
    invalid_payload = {"final_verdict": "fake", "overall_summary": "..."}
    valid_payload = {"final_verdict": "false-fake", "overall_summary": "..."}
    
    with patch("news.council_pipeline.genai.Client") as MockClient:
        instance = MockClient.return_value
        
        mock_resp_invalid = MagicMock()
        mock_resp_invalid.text = json.dumps(invalid_payload)
        
        mock_resp_valid = MagicMock()
        mock_resp_valid.text = json.dumps(valid_payload)
        
        instance.models.generate_content.side_effect = [mock_resp_invalid, mock_resp_valid]
        
        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await stage_5_judge_synthesis("T", "C", [], [], {}, "key")
            
            assert instance.models.generate_content.call_count == 2
            assert result["final_verdict"] == "false-fake"

@pytest.mark.asyncio
async def test_stage_5_exhausts_retries_on_persistent_invalid_verdict():
    """
    TC-DAT-02 / Exhausted: Якщо нейронка 5 разів повертає невалідний вердикт,
    система має повернути "unverifiable" як безпечний фолбек.
    """
    persistent_invalid = {"final_verdict": "unknown_status", "overall_summary": "..."}
    
    with patch("news.council_pipeline.genai.Client") as MockClient:
        instance = MockClient.return_value
        mock_resp = MagicMock()
        mock_resp.text = json.dumps(persistent_invalid)
        instance.models.generate_content.return_value = mock_resp
        
        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await stage_5_judge_synthesis("T", "C", [], [], {}, "key")
            
            assert instance.models.generate_content.call_count == 5
            assert result["final_verdict"] == "unverifiable"
            assert "error" in result

@pytest.mark.asyncio
async def test_stage_5_retries_when_final_verdict_missing():
    """
    TC-DAT-02 / Missing-Key: Перевірка поведінки, коли JSON валідний, 
    але поле 'final_verdict' відсутнє.
    """
    payload_no_key = {"summary": "Only summary here"}
    valid_payload = {"final_verdict": "fact", "overall_summary": "..."}
    
    with patch("news.council_pipeline.genai.Client") as MockClient:
        instance = MockClient.return_value
        
        mock_resp_no_key = MagicMock()
        mock_resp_no_key.text = json.dumps(payload_no_key)
        
        mock_resp_valid = MagicMock()
        mock_resp_valid.text = json.dumps(valid_payload)
        
        instance.models.generate_content.side_effect = [mock_resp_no_key, mock_resp_valid]
        
        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await stage_5_judge_synthesis("T", "C", [], [], {}, "key")
            
            assert instance.models.generate_content.call_count == 2
            assert result["final_verdict"] == "fact"
