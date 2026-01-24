# ==============================================================================
# NEWSFILTERAI - SERIALIZERS
# ==============================================================================
# Серіалізатори для API endpoints

from rest_framework import serializers
from .models import NewsCheck, DomainReputation


class NewsCheckInputSerializer(serializers.Serializer):
    """
    Серіалізатор для вхідних даних - приймає URL новини для перевірки.
    Використовується в POST /api/check-news/
    """
    url = serializers.URLField(
        max_length=2048,
        help_text='URL новини для перевірки на достовірність'
    )

    def validate_url(self, value):
        """Валідація та нормалізація URL"""
        # Видаляємо зайві пробіли
        value = value.strip()

        # Перевіряємо що URL починається з http:// або https://
        if not value.startswith(('http://', 'https://')):
            raise serializers.ValidationError(
                'URL повинен починатися з http:// або https://'
            )

        return value


class NewsCheckSerializer(serializers.ModelSerializer):
    """
    Серіалізатор для повної інформації про перевірку новини.
    Використовується для відповіді API.
    """
    verdict_display = serializers.CharField(
        source='get_verdict_display',
        read_only=True
    )

    class Meta:
        model = NewsCheck
        fields = [
            'id',
            'url',
            'url_hash',
            'title',
            'source_domain',
            'verdict',
            'verdict_display',
            'is_fake',
            'confidence_score',
            'ai_verdict_json',
            'ai_response',
            'task_id',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'url_hash',
            'verdict',
            'is_fake',
            'confidence_score',
            'ai_verdict_json',
            'ai_response',
            'task_id',
            'created_at',
            'updated_at',
        ]


class NewsCheckShortSerializer(serializers.ModelSerializer):
    """
    Короткий серіалізатор для списку перевірок.
    Без повної відповіді AI для оптимізації.
    """
    verdict_display = serializers.CharField(
        source='get_verdict_display',
        read_only=True
    )

    class Meta:
        model = NewsCheck
        fields = [
            'id',
            'url',
            'title',
            'source_domain',
            'verdict',
            'verdict_display',
            'is_fake',
            'confidence_score',
            'created_at',
        ]


class TaskStatusSerializer(serializers.Serializer):
    """
    Серіалізатор для статусу Celery задачі.
    Використовується в GET /api/task-status/<task_id>/
    """
    task_id = serializers.CharField(help_text='ID Celery задачі')
    status = serializers.CharField(help_text='Статус задачі: PENDING, STARTED, SUCCESS, FAILURE')
    result = NewsCheckSerializer(allow_null=True, required=False)
    error = serializers.CharField(allow_null=True, required=False)


class CacheResultSerializer(serializers.Serializer):
    """
    Серіалізатор для кешованого результату з Redis.
    """
    cached = serializers.BooleanField(
        default=True,
        help_text='Результат отримано з кешу'
    )
    url = serializers.URLField()
    title = serializers.CharField(allow_blank=True)
    source_domain = serializers.CharField()
    verdict = serializers.CharField()
    verdict_display = serializers.CharField()
    is_fake = serializers.BooleanField()
    confidence_score = serializers.FloatField()
    ai_verdict_json = serializers.JSONField()
    checked_at = serializers.DateTimeField()


class DomainReputationSerializer(serializers.ModelSerializer):
    """
    Серіалізатор для репутації домену.
    """
    reputation_type_display = serializers.CharField(
        source='get_reputation_type_display',
        read_only=True
    )

    class Meta:
        model = DomainReputation
        fields = [
            'id',
            'domain',
            'reputation_type',
            'reputation_type_display',
            'description',
            'added_by',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class DomainCheckSerializer(serializers.Serializer):
    """
    Серіалізатор для перевірки домену в білому/чорному списку.
    """
    domain = serializers.CharField(max_length=255)
    in_whitelist = serializers.BooleanField()
    in_blacklist = serializers.BooleanField()
    reputation = serializers.CharField(allow_null=True)

