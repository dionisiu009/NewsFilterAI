import pytest
from unittest.mock import patch, MagicMock
from rest_framework.test import APIClient

from news.models import NewsCheck
from config.celery import app as celery_app
from news.tasks import check_news_task


@pytest.mark.django_db
class TestTCInt01:

    def test_celery_broker_is_redis(self):
        """
        Крок 1. Перевірка, що Celery дійсно налаштований на використання Redis як брокера повідомлень.
        """
        broker_url = celery_app.conf.broker_url
        assert broker_url.startswith('redis://'), "Celery broker має бути налаштований на Redis"

    def test_task_is_transmitted_to_celery_from_api(self):
        """
        Крок 2. Перевірка, що при виклику API для перевірки новини
        відбувається коректна передача задачі в брокер (виклик delay).
        """
        client = APIClient()
        url = "/api/check/"
        test_url = "https://example.com/test-redis-transmission"
        
        with patch('news.views.check_news_task.delay') as mock_delay:
            mock_task_result = MagicMock()
            mock_task_result.id = "fake-redis-task-id-123"
            mock_delay.return_value = mock_task_result

            with patch('news.views.news_cache_service.get', return_value=None):
                response = client.post(url, {"url": test_url}, format="json")

            assert response.status_code == 202

            news_check = NewsCheck.objects.filter(url=test_url).first()
            assert news_check is not None

            mock_delay.assert_called_once_with(test_url, news_check.id)

            assert news_check.task_id == "fake-redis-task-id-123"

    def test_task_execution_via_eager_mode(self, settings):
        """
        Крок 3. Перевірка повного циклу "передачі" та виконання задачі воркером.
        Використовуємо CELERY_TASK_ALWAYS_EAGER для синхронного виконання задачі
        без підняття реального окремого воркера в тестах.
        """
        settings.CELERY_TASK_ALWAYS_EAGER = True
        settings.CELERY_TASK_EAGER_PROPAGATES = True

        with patch('news.tasks.domain_list_service.check_url') as mock_check_url:
            mock_check_url.return_value = {
                'domain': 'example.com',
                'reputation': 'unknown',
                'in_whitelist': False,
                'in_blacklist': True
            }
            
            test_url = "https://example.com/fake-news-eager"
            news_check = NewsCheck.objects.create(
                url=test_url,
                url_hash=NewsCheck.generate_url_hash(test_url),
                verdict=NewsCheck.VerdictChoices.PENDING
            )

            result = check_news_task.delay(test_url, news_check.id)

            assert result.successful()

            news_check.refresh_from_db()
            assert news_check.verdict == NewsCheck.VerdictChoices.FALSE
            assert news_check.is_fake is True
