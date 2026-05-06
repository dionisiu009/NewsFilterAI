# ==============================================================================
# NEWSFILTERAI - NEWS MODELS
# ==============================================================================
# Моделі для зберігання історії перевірок новин

from django.db import models

from .utils import generate_url_hash, extract_domain


class NewsCheck(models.Model):
    """
    Модель для зберігання історії перевірок новин.
    Зберігає URL, результат AI аналізу та метадані.
    """

    class VerdictChoices(models.TextChoices):
        PENDING = 'pending', 'В обробці'
        TRUE = 'true', 'Достовірна'
        FACT = 'fact', 'Факт'
        FALSE = 'false', 'Фейк'
        FALSE_FAKE = 'false-fake', 'Фейк'
        PARTIALLY_TRUE = 'partial', 'Частково правда'
        CLICKBAIT = 'clickbait', 'Клікбейт'
        OPINION = 'opinion', 'Думка'
        SATIRE = 'satire', 'Сатира'
        UNVERIFIABLE = 'unverifiable', 'Неможливо перевірити'
        ERROR = 'error', 'Помилка обробки'

    # Основні поля
    url = models.URLField(
        max_length=2048,
        verbose_name='URL новини',
        db_index=True
    )
    url_hash = models.CharField(
        max_length=64,
        unique=True,
        verbose_name='Hash URL',
        help_text='SHA-256 hash для швидкого пошуку'
    )

    # Контент
    title = models.CharField(
        max_length=500,
        blank=True,
        verbose_name='Заголовок статті'
    )
    source_domain = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Домен джерела'
    )

    # Результати AI аналізу
    verdict = models.CharField(
        max_length=20,
        choices=VerdictChoices.choices,
        default=VerdictChoices.PENDING,
        verbose_name='Вердикт'
    )
    is_fake = models.BooleanField(
        default=False,
        verbose_name='Є фейком',
        help_text='True якщо новина визнана фейковою'
    )

    ai_verdict_json = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Повна відповідь AI (JSON)',
        help_text='Структурована відповідь від Gemini API'
    )
    ai_response = models.TextField(
        blank=True,
        verbose_name='Текстова відповідь AI'
    )
    pipeline_artifacts = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Проміжні результати пайплайну (Markdown)'
    )

    # Celery задача
    task_id = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='ID Celery задачі',
        db_index=True
    )

    # Часові мітки
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Створено'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Оновлено'
    )

    class Meta:
        verbose_name = 'Перевірка новини'
        verbose_name_plural = 'Перевірки новин'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['url_hash']),
            models.Index(fields=['task_id']),
            models.Index(fields=['created_at']),
            models.Index(fields=['source_domain']),
            models.Index(fields=['verdict']),
        ]

    def __str__(self):
        status = "🔴 ФЕЙК" if self.is_fake else "🟢 ОК"
        return f'{status} | {self.source_domain} | {self.title[:30]}...'

    def save(self, *args, **kwargs):
        """Автоматично генеруємо url_hash перед збереженням"""
        if not self.url_hash:
            self.url_hash = generate_url_hash(self.url)

        # Витягуємо домен з URL
        if self.url and not self.source_domain:
            self.source_domain = extract_domain(self.url)

        # Встановлюємо is_fake на основі verdict
        self.is_fake = self.verdict == self.VerdictChoices.FALSE

        # Захист: не дозволяємо None для task_id (CharField без null=True)
        if self.task_id is None:
            self.task_id = ''

        super().save(*args, **kwargs)

    @staticmethod
    def generate_url_hash(url: str) -> str:
        """Генерує SHA-256 hash для URL (wrapper для сумісності)"""
        return generate_url_hash(url)


class ParserDebugInfo(models.Model):
    """
    Зберігає детальну інформацію про парсинг статті.
    Пов'язана з NewsCheck через FK.
    Доступна як для свіжих, так і для кешованих результатів.
    """

    news_check = models.OneToOneField(
        NewsCheck,
        on_delete=models.CASCADE,
        related_name='parser_debug',
        verbose_name='Перевірка новини'
    )

    # Основні поля парсингу
    parsed_title = models.CharField(
        max_length=500,
        blank=True,
        verbose_name='Заголовок (parsed)'
    )
    parsed_text = models.TextField(
        blank=True,
        verbose_name='Повний текст статті'
    )
    parsed_authors = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Автори'
    )
    parsed_publish_date = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='Дата публікації (raw)'
    )
    parsed_domain = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Домен'
    )
    parsed_meta_description = models.TextField(
        blank=True,
        verbose_name='Meta Description'
    )
    parsed_word_count = models.IntegerField(
        default=0,
        verbose_name='Кількість слів'
    )

    # Дані порівняння всіх парсерів (Bs4, Readability, Trafilatura, Newspaper3k, Goose3)
    parsers_debug = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Порівняння результатів парсерів'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Збережено'
    )

    class Meta:
        verbose_name = 'Parser Debug Info'
        verbose_name_plural = 'Parser Debug Info'

    def __str__(self):
        return f'ParseDebug → NewsCheck #{self.news_check_id}'

    def to_dict(self) -> dict:
        """Повертає дані у форматі, очікуваному фронтендом"""
        return {
            'parsed_title': self.parsed_title,
            'parsed_text': self.parsed_text,
            'parsed_authors': self.parsed_authors or [],
            'parsed_publish_date': self.parsed_publish_date,
            'parsed_domain': self.parsed_domain,
            'parsed_meta_description': self.parsed_meta_description,
            'parsed_word_count': self.parsed_word_count,
            'parsers_debug': self.parsers_debug or [],
        }


class DomainReputation(models.Model):
    """
    Модель для зберігання репутації доменів.
    Дублює Redis для надійності та історії.
    """

    class ReputationType(models.TextChoices):
        WHITELIST = 'whitelist', 'Білий список (достовірні)'
        BLACKLIST = 'blacklist', 'Чорний список (сумнівні)'

    domain = models.CharField(
        max_length=255,
        unique=True,
        verbose_name='Домен',
        help_text='Наприклад: bbc.com, pravda.com.ua'
    )
    reputation_type = models.CharField(
        max_length=20,
        choices=ReputationType.choices,
        verbose_name='Тип репутації'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Опис/причина'
    )
    added_by = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Додав'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Додано'
    )

    class Meta:
        verbose_name = 'Репутація домену'
        verbose_name_plural = 'Репутації доменів'
        ordering = ['reputation_type', 'domain']

    def __str__(self):
        icon = "✅" if self.reputation_type == self.ReputationType.WHITELIST else "⛔"
        return f'{icon} {self.domain}'
