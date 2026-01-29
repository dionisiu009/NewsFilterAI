# ==============================================================================
# NEWSFILTERAI - CONSTANTS
# ==============================================================================
# Константи та конфігурація для модуля news

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


# ==============================================================================
# ВЕРДИКТИ
# ==============================================================================

class Verdict(str, Enum):
    """Можливі вердикти перевірки новини"""
    TRUE = 'true'
    FALSE = 'false'
    PARTIAL = 'partial'
    UNVERIFIABLE = 'unverifiable'
    PENDING = 'pending'
    ERROR = 'error'


VERDICT_DISPLAY = {
    Verdict.TRUE: 'Достовірна',
    Verdict.FALSE: 'Фейк',
    Verdict.PARTIAL: 'Частково правда',
    Verdict.UNVERIFIABLE: 'Неможливо перевірити',
    Verdict.PENDING: 'В обробці',
    Verdict.ERROR: 'Помилка обробки',
}

VERDICT_EMOJI = {
    Verdict.TRUE: '✅',
    Verdict.FALSE: '🔴',
    Verdict.PARTIAL: '🟡',
    Verdict.UNVERIFIABLE: '❓',
    Verdict.PENDING: '⏳',
    Verdict.ERROR: '⚠️',
}


# ==============================================================================
# ЛІМІТИ
# ==============================================================================

# Парсинг статей
MIN_ARTICLE_LENGTH = 50  # Мінімальна кількість символів для аналізу
MAX_CONTENT_LENGTH = 15000  # Максимальна довжина тексту для AI

# URL
MAX_URL_LENGTH = 2048
MAX_TITLE_LENGTH = 500

# Таймаути (секунди)
PARSER_TIMEOUT = 60
AI_REQUEST_TIMEOUT = 120
CELERY_TASK_TIMEOUT = 300


# ==============================================================================
# DATACLASSES ДЛЯ РЕЗУЛЬТАТІВ
# ==============================================================================

@dataclass
class ParsedArticle:
    """Результат парсингу статті"""
    success: bool
    title: str = ''
    text: str = ''
    authors: List[str] = field(default_factory=list)
    publish_date: Optional[str] = None
    top_image: str = ''
    domain: str = ''
    meta_description: str = ''
    meta_keywords: List[str] = field(default_factory=list)
    word_count: int = 0
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Конвертує в словник"""
        return {
            'success': self.success,
            'title': self.title,
            'text': self.text,
            'authors': self.authors,
            'publish_date': self.publish_date,
            'top_image': self.top_image,
            'domain': self.domain,
            'meta_description': self.meta_description,
            'meta_keywords': self.meta_keywords,
            'word_count': self.word_count,
            'error': self.error,
        }


@dataclass
class AIVerificationResult:
    """Результат AI перевірки"""
    verdict: str = 'unverifiable'
    confidence_score: int = 0
    is_fake: bool = False
    summary: str = ''
    analysis: Dict[str, Any] = field(default_factory=dict)
    recommendation: str = ''
    error: bool = False
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Конвертує в словник"""
        result = {
            'verdict': self.verdict,
            'confidence_score': self.confidence_score,
            'is_fake': self.is_fake,
            'summary': self.summary,
            'analysis': self.analysis,
            'recommendation': self.recommendation,
        }
        if self.error:
            result['error'] = True
            result['error_message'] = self.error_message
        return result


@dataclass
class DomainInfo:
    """Інформація про домен"""
    domain: str
    in_whitelist: bool = False
    in_blacklist: bool = False
    reputation: str = 'unknown'  # 'trusted', 'suspicious', 'unknown'

    def to_dict(self) -> Dict[str, Any]:
        """Конвертує в словник"""
        return {
            'domain': self.domain,
            'in_whitelist': self.in_whitelist,
            'in_blacklist': self.in_blacklist,
            'reputation': self.reputation,
        }

