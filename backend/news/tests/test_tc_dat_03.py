# ==============================================================================
# TC-DAT-03: Контроль якості RAG-контексту та валідація Cohere Rerank (Stage 3)
# ==============================================================================
# Цей тест перевіряє логіку фільтрації та ранжування статей, включаючи механізм
# "fallback" (резервного копіювання), коли жодна стаття не проходить поріг релевантності.

import pytest
from news.council_pipeline import _filter_top_articles, _build_worker_user_prompt

# ── Тестові дані ──────────────────────────────────────────────────────────────
MOCK_INTENTS = [
    {"intent_id": "i1", "intent": "Test Claim 1", "search_guidance": "Guide 1"}
]

NEWS_CONTENT = "Президент України заявив про необхідність посилення санкцій проти Росії у енергетичному та фінансовому секторах."

def test_filter_valid_context():
    """
    TC-DAT-03 / Scenario 1: Наявність релевантного контенту.
    Перевірка, що статті з високим балом (>= 0.5) проходять фільтр.
    """
    scored_results = [
        {
            "intent_id": "i1",
            "intent": "Test Claim 1",
            "articles": [
                {"title": "Good Art", "url": "url1", "cohere_score": 0.8},
                {"title": "Mid Art", "url": "url2", "cohere_score": 0.4}
            ]
        }
    ]
    
    filtered = _filter_top_articles(scored_results, threshold=0.5, max_per_intent=3)
    
    assert len(filtered[0]["articles"]) == 1
    assert filtered[0]["articles"][0]["title"] == "Good Art"
    assert "low_relevance" not in filtered[0]["articles"][0]

def test_filter_low_relevance_fallback():
    """
    TC-DAT-03 / Scenario 2: Резервне копіювання (Fallback).
    Якщо всі статті < 0.5, система має взяти топ-5 і позначити їх як low_relevance.
    """
    scored_results = [
        {
            "intent_id": "i1",
            "intent": "Test Claim 1",
            "articles": [
                {"title": "Weak Art 1", "url": "u1", "cohere_score": 0.3},
                {"title": "Weak Art 2", "url": "u2", "cohere_score": 0.2},
                {"title": "Weak Art 3", "url": "u3", "cohere_score": 0.1}
            ]
        }
    ]
    
    filtered = _filter_top_articles(scored_results, threshold=0.5, max_per_intent=3, fallback_count=5)
    
    assert len(filtered[0]["articles"]) == 3
    assert filtered[0]["articles"][0]["low_relevance"] is True
    assert filtered[0]["articles"][0]["title"] == "Weak Art 1"

def test_filter_no_results():
    """
    TC-DAT-03 / Scenario 3: Обробка порожньої видачі.
    Якщо Tavily не знайшов нічого, список має бути порожнім.
    """
    scored_results = [
        {
            "intent_id": "i1",
            "intent": "Test Claim 1",
            "articles": []
        }
    ]
    
    filtered = _filter_top_articles(scored_results)
    assert len(filtered[0]["articles"]) == 0

def test_prompt_warning_injection():
    """
    TC-DAT-03 / Scenario 4: Валідація форматів та ін'єкція попереджень.
    Перевірка, що при low_relevance=True в промпт додається WARNING.
    """
    top_articles = [
        {
            "intent_id": "i1",
            "intent": "Test Claim 1",
            "articles": [
                {"title": "Bad Art", "url": "u1", "cohere_score": 0.1, "low_relevance": True}
            ]
        }
    ]
    
    prompt = _build_worker_user_prompt(NEWS_CONTENT, MOCK_INTENTS, top_articles)
    
    assert "WARNING" in prompt
    assert "VERY LOW RELEVANCE SCORES" in prompt
    assert "Cohere Rerank Score: 0.1000" in prompt

def test_type_integrity_in_prompt():
    """
    Додаткова перевірка цілісності типів даних у промпті.
    """
    top_articles = [
        {
            "intent_id": "i1",
            "intent": "Test Claim 1",
            "articles": [
                {"title": None, "url": "", "content": "Some text", "cohere_score": 0.6}
            ]
        }
    ]
    
    prompt = _build_worker_user_prompt(NEWS_CONTENT, MOCK_INTENTS, top_articles)
    
    assert "(no title)" in prompt
    assert "Some text" in prompt
    assert isinstance(prompt, str)
