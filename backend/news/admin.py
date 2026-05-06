# ==============================================================================
# NEWSFILTERAI - NEWS ADMIN
# ==============================================================================

from django.contrib import admin
from .models import NewsCheck, DomainReputation


@admin.register(NewsCheck)
class NewsCheckAdmin(admin.ModelAdmin):
    """Адмін-панель для перевірок новин."""

    list_display = (
        'id',
        'short_url',
        'source_domain',
        'verdict',
        'is_fake',
        'created_at'
    )
    list_filter = ('verdict', 'is_fake', 'source_domain', 'created_at')
    search_fields = ('url', 'title', 'source_domain', 'ai_response')
    readonly_fields = (
        'url_hash',
        'created_at',
        'updated_at',
        'task_id',
    )
    ordering = ('-created_at',)

    fieldsets = (
        ('Основна інформація', {
            'fields': ('url', 'url_hash', 'title', 'source_domain')
        }),
        ('Результат перевірки', {
            'fields': ('verdict', 'is_fake')
        }),
        ('Відповідь AI', {
            'fields': ('ai_verdict_json', 'ai_response'),
            'classes': ('collapse',)
        }),
        ('Службова інформація', {
            'fields': ('task_id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def short_url(self, obj):
        """Скорочений URL для відображення в списку."""
        return obj.url[:60] + '...' if len(obj.url) > 60 else obj.url
    short_url.short_description = 'URL'


@admin.register(DomainReputation)
class DomainReputationAdmin(admin.ModelAdmin):
    """Адмін-панель для репутації доменів."""

    list_display = ('domain', 'reputation_type', 'added_by', 'created_at')
    list_filter = ('reputation_type', 'created_at')
    search_fields = ('domain', 'description', 'added_by')
    readonly_fields = ('created_at',)
    ordering = ('reputation_type', 'domain')

    fieldsets = (
        ('Домен', {
            'fields': ('domain', 'reputation_type')
        }),
        ('Деталі', {
            'fields': ('description', 'added_by')
        }),
        ('Службова інформація', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    actions = ['make_whitelist', 'make_blacklist']

    @admin.action(description='Перемістити до білого списку')
    def make_whitelist(self, request, queryset):
        queryset.update(reputation_type=DomainReputation.ReputationType.WHITELIST)

    @admin.action(description='Перемістити до чорного списку')
    def make_blacklist(self, request, queryset):
        queryset.update(reputation_type=DomainReputation.ReputationType.BLACKLIST)


