import pytest
from unittest.mock import patch
from rest_framework.test import APIClient
from news.models import NewsCheck, ParserDebugInfo
from django.urls import reverse

@pytest.mark.django_db
class TestEndToEndRegression:
    """
    Regression tests to ensure the core flow (API -> Task -> Parser -> Model) 
    remains functional.
    """

    def setup_method(self):
        self.client = APIClient()
        self.check_url = reverse('news:check-news')
        self.history_url = reverse('news:history')

    @patch('news.tasks.execute_pipeline')
    @patch('news.tasks.article_parser.parse_url')
    @patch('news.tasks.domain_list_service.check_url')
    def test_full_check_flow_regression(self, mock_domain_check, mock_parser, mock_pipeline, settings):
        """
        Verify that a full news check request flows correctly through the system.
        Covers: API Reception -> DB Record Creation -> Celery Task -> Parser -> Pipeline -> Result Saving.
        """
        # 1. Setup mocks
        settings.CELERY_TASK_ALWAYS_EAGER = True
        
        test_url = "https://regression-test.com/article-1"
        mock_domain_check.return_value = {
            'domain': 'regression-test.com',
            'reputation': 'unknown',
            'in_whitelist': False,
            'in_blacklist': False,
            'in_blacklist_manual': False,
            'in_whitelist_manual': False
        }
        
        mock_parser.return_value = {
            'success': True,
            'title': 'Regression Test Title',
            'text': 'Full article content for regression testing...',
            'authors': ['Test Author'],
            'publish_date': '2026-05-07',
            'domain': 'regression-test.com',
            'word_count': 100,
            'parsers_debug': []
        }
        
        mock_pipeline.return_value = {
            'final_verdict': 'fact',
            'overall_summary': 'This is a verified fact.',
            'intents_analysis': [],
            'recommendation': 'Trust but verify.',
            'artifacts': {'stage1.md': 'content'}
        }

        # 2. Trigger API
        response = self.client.post(self.check_url, {"url": test_url}, format='json')
        assert response.status_code == 202
        check_id = response.data['check_id']

        # 3. Verify Database Integrity
        news_check = NewsCheck.objects.get(id=check_id)
        assert news_check.url == test_url
        assert news_check.verdict == NewsCheck.VerdictChoices.FACT
        assert news_check.is_fake is False
        
        # 4. Verify Parser Debug Info
        debug_info = ParserDebugInfo.objects.get(news_check=news_check)
        assert debug_info.parsed_title == 'Regression Test Title'

        # 5. Verify History Visibility
        history_response = self.client.get(self.history_url)
        assert history_response.status_code == 200
        # Check if the check_id is in the results
        assert any(item['id'] == check_id for item in history_response.data['results'])

    def test_api_health_regression(self):
        """Ensure core API endpoints are alive."""
        health_url = reverse('news:health-check')
        response = self.client.get(health_url)
        assert response.status_code == 200
        assert response.data['status'] == 'healthy'
