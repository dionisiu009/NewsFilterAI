import os
import pytest
from django.conf import settings
from django.core.cache import caches


@pytest.fixture(scope="session")
def django_db_setup():
    settings.DATABASES["default"] = {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.path.join(settings.BASE_DIR, "test_db.sqlite3"),
    }


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
