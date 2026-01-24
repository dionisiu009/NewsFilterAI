from django.core.cache import cache

from news.services import news_cache_service


def test_cache_set_skips_error_results():
    # Перевірка, що результати з помилкою не кешуються
    url = "https://example.com/error"
    result = {"url": url, "verdict": "error", "_is_error": True}

    cached = news_cache_service.set(url, result)

    assert cached is False
    assert news_cache_service.get(url) is None


def test_cache_round_trip_successful_result():
    # Перевірка збереження та отримання валідного результату з кешу
    url = "https://example.com/news"
    result = {"url": url, "verdict": "true", "title": "Hello"}

    cache_key = news_cache_service._get_cache_key(url)
    cache.delete(cache_key)

    saved = news_cache_service.set(url, result, ttl=60)
    retrieved = news_cache_service.get(url)

    assert saved is True
    assert retrieved is not None
    assert retrieved["verdict"] == "true"
    assert retrieved["cached"] is True
