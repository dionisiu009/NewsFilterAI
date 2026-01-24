import uuid
from types import SimpleNamespace

import pytest

from news import views
from news.models import NewsCheck


@pytest.mark.django_db
def test_check_news_invalid_payload_returns_400(api_client):
    # Перевірка, що невалідний запит повертає 400 з деталями помилки
    response = api_client.post("/api/check/", {}, format="json")

    assert response.status_code == 400
    assert "details" in response.data


@pytest.mark.django_db
def test_check_news_cache_hit_short_circuits(api_client, monkeypatch):
    # Перевірка, що при Cache HIT повертається результат без створення задачі
    url = "https://example.com/news/1"
    cached_result = {"url": url, "verdict": "true", "summary": "ok"}

    monkeypatch.setattr(views, "news_cache_service", SimpleNamespace(get=lambda _: cached_result))

    response = api_client.post("/api/check/", {"url": url}, format="json")

    assert response.status_code == 200
    assert response.data["cached"] is True
    assert response.data["result"]["verdict"] == "true"


@pytest.mark.django_db
def test_check_news_existing_pending_reuses_task(api_client, monkeypatch):
    # Перевірка, що для вже запущеної перевірки повертається існуючий task_id
    url = "https://example.com/news/2"
    news = NewsCheck.objects.create(
        url=url,
        url_hash=NewsCheck.generate_url_hash(url),
        verdict=NewsCheck.VerdictChoices.PENDING,
        task_id="task-existing",
    )

    monkeypatch.setattr(views, "news_cache_service", SimpleNamespace(get=lambda _: None))

    response = api_client.post("/api/check/", {"url": url}, format="json")

    assert response.status_code == 202
    assert response.data["task_id"] == news.task_id
    assert response.data["status"] == "already_processing"


@pytest.mark.django_db
def test_check_news_existing_success_is_returned(api_client, monkeypatch):
    # Перевірка, що існуючий успішний результат повертається та кешується
    url = "https://example.com/news/3"
    news = NewsCheck.objects.create(
        url=url,
        url_hash=NewsCheck.generate_url_hash(url),
        verdict=NewsCheck.VerdictChoices.TRUE,
        ai_verdict_json={"verdict": "true", "summary": "validated"},
        ai_response="validated",
        source_domain="example.com",
    )

    monkeypatch.setattr(views, "news_cache_service", SimpleNamespace(get=lambda _: None, set=lambda *_: True))

    response = api_client.post("/api/check/", {"url": url}, format="json")

    assert response.status_code == 200
    assert response.data["cached"] is True
    assert response.data["result"]["verdict"] == news.verdict


@pytest.mark.django_db
def test_check_news_error_result_triggers_retry(api_client, monkeypatch):
    # Перевірка, що попередня помилка призводить до нової Celery задачі
    url = "https://example.com/news/4"
    news = NewsCheck.objects.create(
        url=url,
        url_hash=NewsCheck.generate_url_hash(url),
        verdict=NewsCheck.VerdictChoices.ERROR,
        ai_verdict_json={"verdict": "error", "parse_error": True},
        ai_response="fail",
    )

    dummy_task = SimpleNamespace(id="celery-new")
    monkeypatch.setattr(views, "news_cache_service", SimpleNamespace(get=lambda _: None))
    monkeypatch.setattr(views.check_news_task, "delay", lambda *_: dummy_task)

    response = api_client.post("/api/check/", {"url": url}, format="json")

    news.refresh_from_db()

    assert response.status_code == 202
    assert response.data["task_id"] == dummy_task.id
    assert news.verdict == NewsCheck.VerdictChoices.PENDING


@pytest.mark.django_db
def test_check_news_celery_failure_returns_500(api_client, monkeypatch):
    # Перевірка, що виняток під час запуску Celery повертає 500 та позначає запис як помилку
    url = "https://example.com/news/5"

    def raise_error(*_):
        raise RuntimeError("celery boom")

    monkeypatch.setattr(views, "news_cache_service", SimpleNamespace(get=lambda _: None))
    monkeypatch.setattr(views.check_news_task, "delay", raise_error)

    response = api_client.post("/api/check/", {"url": url}, format="json")

    news = NewsCheck.objects.get(url=url)

    assert response.status_code == 500
    assert response.data["error_code"] == "CELERY_TASK_ERROR"
    assert news.verdict == NewsCheck.VerdictChoices.ERROR


@pytest.mark.django_db
def test_check_news_creates_new_task(api_client, monkeypatch):
    # Перевірка стандартного шляху створення запису та Celery задачі
    url = "https://example.com/news/6"
    dummy_task = SimpleNamespace(id="task-new")

    monkeypatch.setattr(views, "news_cache_service", SimpleNamespace(get=lambda _: None))
    monkeypatch.setattr(views.check_news_task, "delay", lambda *_: dummy_task)

    response = api_client.post("/api/check/", {"url": url}, format="json")
    news = NewsCheck.objects.get(url=url)

    assert response.status_code == 202
    assert response.data["task_id"] == dummy_task.id
    assert news.task_id == dummy_task.id


@pytest.mark.parametrize(
    "status_value,result_payload,expected_field",
    [
        ("PENDING", None, "message"),
        ("STARTED", None, "message"),
        ("SUCCESS", {"verdict": "true"}, "result"),
        ("FAILURE", "boom", "error"),
    ],
)
def test_task_status_view_handles_states(api_client, monkeypatch, status_value, result_payload, expected_field):
    # Перевірка мапінгу статусів Celery задачі у відповіді API
    task_id = str(uuid.uuid4())

    class DummyResult:
        def __init__(self, status, result):
            self.status = status
            self.result = result

    monkeypatch.setattr(views, "AsyncResult", lambda _: DummyResult(status_value, result_payload))

    response = api_client.get(f"/api/task-status/{task_id}/")

    assert response.status_code == 200
    assert expected_field in response.data
    assert response.data["status"] == status_value.lower()


@pytest.mark.django_db
def test_domain_check_view_validations(api_client, monkeypatch):
    # Перевірка валідації обов'язкових параметрів для domain-check
    response_get = api_client.get("/api/domain-check/")
    response_post = api_client.post("/api/domain-check/", {})

    assert response_get.status_code == 400
    assert response_post.status_code == 400


@pytest.mark.django_db
def test_domain_check_view_returns_reputation(api_client, monkeypatch):
    # Перевірка, що сервіс репутації доменів проксіюється через endpoint
    stub_service = SimpleNamespace(
        check_domain=lambda domain: {"domain": domain, "reputation": "trusted", "in_whitelist": True, "in_blacklist": False},
        check_url=lambda url: {"domain": "example.com", "reputation": "unknown", "in_whitelist": False, "in_blacklist": False},
    )
    monkeypatch.setattr(views, "domain_list_service", stub_service)

    response_get = api_client.get("/api/domain-check/", {"domain": "example.com"})
    response_post = api_client.post("/api/domain-check/", {"url": "https://example.com/a"})

    assert response_get.status_code == 200
    assert response_get.data["reputation"] == "trusted"
    assert response_post.status_code == 200
    assert response_post.data["domain"] == "example.com"
