# ==============================================================================
# NEWSFILTERAI - NEWS URL ROUTES
# ==============================================================================

from django.urls import path
from .views import (
    HealthCheckView,
    CheckNewsView,
    TaskStatusView,
    NewsCheckDetailView,
    NewsCheckHistoryView,
    DomainCheckView,
    DomainListView,
    DebugCheckView,
    ClearCacheView,
)

app_name = 'news'

urlpatterns = [
    # Health check
    path('health/', HealthCheckView.as_view(), name='health-check'),

    # Основний endpoint для перевірки новин
    path('check/', CheckNewsView.as_view(), name='check-news'),

    # Статус Celery задачі
    path('task-status/<str:task_id>/', TaskStatusView.as_view(), name='task-status'),

    # Деталі конкретної перевірки
    path('check/<int:check_id>/', NewsCheckDetailView.as_view(), name='check-detail'),

    # Історія перевірок
    path('history/', NewsCheckHistoryView.as_view(), name='history'),

    # Перевірка репутації домену
    path('domain-check/', DomainCheckView.as_view(), name='domain-check'),

    # Списки доменів (білий/чорний)
    path('domains/', DomainListView.as_view(), name='domain-list'),

    # Debug endpoint для діагностики
    path('debug/check/', DebugCheckView.as_view(), name='debug-check'),

    # Очищення кешу
    path('cache/clear/', ClearCacheView.as_view(), name='cache-clear'),
]

