import os
import pytest
from django.conf import settings
from django.core.cache import caches


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        from django.core.management import call_command
        call_command("migrate", "--run-syncdb")


@pytest.fixture(autouse=True)
def override_cache_settings(settings):
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "newsfilter-test-cache",
        }
    }
    caches["default"].clear()
    yield
    caches["default"].clear()


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient

    return APIClient()
