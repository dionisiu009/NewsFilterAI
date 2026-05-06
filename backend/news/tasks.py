# ==============================================================================
# NEWSFILTERAI - CELERY TASKS
# ==============================================================================
# Асинхронні задачі для перевірки новин

import logging
import traceback
from typing import Dict, Any
from dataclasses import dataclass

from celery import shared_task

from .models import NewsCheck, ParserDebugInfo
from .services import domain_list_service, news_cache_service
from .parser_service import article_parser
from .ai_service import get_gemini_service

logger = logging.getLogger(__name__)


@dataclass
class CheckResult:
    """Структура результату перевірки"""
    success: bool
    is_error: bool = False
    error_message: str = ""


@shared_task(
    bind=True,
    max_retries=2,  # Зменшено з 3 до 2 для швидшого фідбеку
    default_retry_delay=30,  # 30 секунд між спробами
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=120,  # Максимум 2 хвилини затримки
    retry_jitter=True,
)
def check_news_task(self, url: str, news_check_id: int) -> Dict[str, Any]:
    """
    Celery задача для перевірки новини на достовірність.

    Алгоритм:
    1. Перевіряє домен у білому/чорному списку
    2. Парсить статтю за URL (trafilatura)
    3. Відправляє текст в Google Gemini AI
    4. Зберігає результат в PostgreSQL
    5. Кешує результат в Redis

    Args:
        url: URL новини для перевірки
        news_check_id: ID запису NewsCheck в БД

    Returns:
        dict: Результат перевірки з вердиктом та аналізом
    """
    task_id = self.request.id
    logger.info(f"[Task {task_id}] Початок перевірки: {url[:60]}...")

    try:
        # Отримуємо запис з БД
        news_check = NewsCheck.objects.get(id=news_check_id)

        # =====================================================================
        # КРОК 1: Перевірка домену в білому/чорному списку
        # =====================================================================
        domain_info = domain_list_service.check_url(url)
        domain = domain_info['domain']

        logger.info(f"Домен: {domain}, репутація: {domain_info['reputation']}")

        # Якщо домен у чорному списку - одразу позначаємо як підозрілий
        if domain_info['in_blacklist']:
            result = _handle_blacklisted_domain(news_check, domain_info)
            _cache_result(url, result)
            return result

        # =====================================================================
        # КРОК 2: Парсинг статті
        # =====================================================================
        logger.info(f"Парсинг статті...")
        parsed = article_parser.parse_url(url)

        if not parsed['success']:
            result = _handle_parsing_error(news_check, parsed['error'])
            return result

        # Оновлюємо запис з даними статті
        news_check.title = parsed['title'][:500] if parsed['title'] else ''
        news_check.source_domain = domain
        news_check.save(update_fields=['title', 'source_domain'])

        # =====================================================================
        # КРОК 3: Перевірка через Gemini AI
        # =====================================================================
        logger.info(f"Відправка в Gemini AI...")

        # Якщо домен у білому списку - додаємо це до контексту
        extra_context = ""
        if domain_info['in_whitelist']:
            extra_context = f"\n\n[ПРИМІТКА: Джерело {domain} знаходиться у білому списку достовірних ЗМІ]"

        def on_pipeline_progress(current_artifacts):
            """Зберігаємо проміжні результати в БД"""
            try:
                # Використовуємо .update() для уникнення проблем з конкурентністю та гонкою станів
                # Хоча Celery task виконується послідовно в одному воркері
                NewsCheck.objects.filter(id=news_check_id).update(
                    pipeline_artifacts=current_artifacts,
                    updated_at=datetime.now()
                )
                logger.info(f"Проміжні результати збережені ({len(current_artifacts)} файлів)")
            except Exception as e:
                logger.warning(f"Помилка збереження проміжних результатів: {e}")

        import asyncio
        from .council_pipeline import execute_pipeline
        from datetime import datetime
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            pipeline_task = execute_pipeline(
                news_title=parsed['title'],
                news_content=parsed['text'],
                on_progress=on_pipeline_progress
            )
            raw_judge_verdict = loop.run_until_complete(
                asyncio.wait_for(pipeline_task, timeout=240.0)
            )
            
            if raw_judge_verdict and not raw_judge_verdict.get("error"):
                logger.info("Pipeline успішно завершив роботу. Форматуємо результат...")
                ai_result = {
                    'verdict': raw_judge_verdict.get('final_verdict', 'unverifiable'),
                    'is_fake': raw_judge_verdict.get('final_verdict') in ['false-fake', 'false'],
                    'summary': raw_judge_verdict.get('overall_summary', ''),
                    'analysis': raw_judge_verdict.get('intents_analysis', []),
                    'recommendation': raw_judge_verdict.get('recommendation', ''),
                    'artifacts': raw_judge_verdict.get('artifacts', {})
                }
            else:
                raise Exception("Pipeline повернув пустий або помилковий результат")
        finally:
            loop.close()

        # =====================================================================
        # КРОК 4: Збереження результату в БД
        # =====================================================================
        result = _save_result(news_check, ai_result, domain_info, parsed)

        # =====================================================================
        # КРОК 5: Кешування в Redis
        # =====================================================================
        _cache_result(url, result)

        logger.info(
            f"[Task {task_id}] Завершено: verdict={result['verdict']}"
        )

        return result

    except NewsCheck.DoesNotExist:
        logger.error(f"NewsCheck з id={news_check_id} не знайдено")
        raise

    except Exception as e:
        error_trace = traceback.format_exc()
        logger.error(f"[Task {task_id}] Помилка: {str(e)}")
        logger.debug(f"Traceback: {error_trace}")

        # Оновлюємо статус в БД як помилку
        _save_error_result(news_check_id, e, error_trace)

        # Піднімаємо виняток для retry механізму Celery
        raise


def _save_error_result(news_check_id: int, error: Exception, error_trace: str) -> None:
    """
    Зберігає помилку в БД.

    Args:
        news_check_id: ID запису в БД
        error: Виняток
        error_trace: Traceback
    """
    try:
        news_check = NewsCheck.objects.get(id=news_check_id)
        news_check.verdict = NewsCheck.VerdictChoices.ERROR
        news_check.ai_response = f"Помилка обробки: {str(error)}"
        news_check.ai_verdict_json = {
            'verdict': 'error',
            'is_fake': False,
            'summary': f'Помилка при обробці: {str(error)}',
            'error': True,
            'error_type': type(error).__name__,
            'error_message': str(error),
        }
        news_check.save(update_fields=['verdict', 'ai_response', 'ai_verdict_json', 'updated_at'])
        logger.info(f"Статус помилки збережено для NewsCheck id={news_check_id}")
    except Exception as save_error:
        logger.error(f"Помилка збереження статусу помилки: {save_error}")



def _handle_blacklisted_domain(
    news_check: NewsCheck,
    domain_info: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Обробляє випадок коли домен у чорному списку.
    """
    logger.warning(f"Домен {domain_info['domain']} у чорному списку!")

    news_check.verdict = NewsCheck.VerdictChoices.FALSE
    news_check.is_fake = True
    news_check.source_domain = domain_info['domain']
    news_check.ai_verdict_json = {
        'verdict': 'false',
        'is_fake': True,
        'summary': f"Джерело {domain_info['domain']} знаходиться у чорному списку сумнівних ресурсів",
        'analysis': {
            'source_credibility': 'Джерело має сумнівну репутацію',
            'blacklisted': True
        },
        'recommendation': 'Не рекомендуємо довіряти цьому джерелу. Перевірте інформацію в інших ЗМІ.'
    }
    news_check.ai_response = news_check.ai_verdict_json['summary']
    news_check.save()

    return _format_result(news_check)


def _handle_parsing_error(
    news_check: NewsCheck,
    error_message: str
) -> Dict[str, Any]:
    """
    Обробляє помилку парсингу.
    НЕ кешує результат - дозволяє повторну спробу пізніше.

    Args:
        news_check: Об'єкт NewsCheck
        error_message: Повідомлення про помилку

    Returns:
        Результат з позначкою помилки
    """
    logger.warning(f"Помилка парсингу для NewsCheck id={news_check.id}: {error_message}")

    news_check.verdict = NewsCheck.VerdictChoices.ERROR
    news_check.ai_verdict_json = {
        'verdict': 'error',
        'is_fake': False,
        'summary': f'Не вдалося отримати текст статті: {error_message}',
        'error': True,
        'parse_error': True
    }
    news_check.ai_response = error_message
    news_check.save(update_fields=['verdict', 'ai_verdict_json', 'ai_response', 'updated_at'])

    result = _format_result(news_check)
    result['_is_error'] = True  # Не кешувати
    return result


def _save_result(
    news_check: NewsCheck,
    ai_result: Dict[str, Any],
    domain_info: Dict[str, Any],
    parsed_info: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Зберігає результат AI перевірки в БД.

    Args:
        news_check: Об'єкт NewsCheck
        ai_result: Результат від AI
        domain_info: Інформація про домен
        parsed_info: Інформація про парсинг (опціонально)

    Returns:
        Форматований результат для відповіді
    """
    # Мапимо verdict з AI на Django choices
    verdict_map = {
        'fact': NewsCheck.VerdictChoices.FACT,
        'true': NewsCheck.VerdictChoices.TRUE,
        'false-fake': NewsCheck.VerdictChoices.FALSE_FAKE,
        'false': NewsCheck.VerdictChoices.FALSE,
        'partial': NewsCheck.VerdictChoices.PARTIALLY_TRUE,
        'clickbait': NewsCheck.VerdictChoices.CLICKBAIT,
        'opinion': NewsCheck.VerdictChoices.OPINION,
        'satire': NewsCheck.VerdictChoices.SATIRE,
        'unverifiable': NewsCheck.VerdictChoices.UNVERIFIABLE,
        'error': NewsCheck.VerdictChoices.ERROR,
    }

    ai_verdict = ai_result.get('verdict', 'unverifiable')
    is_error = ai_verdict == 'error' or ai_result.get('error', False)

    # Оновлюємо NewsCheck
    news_check.verdict = verdict_map.get(ai_verdict, NewsCheck.VerdictChoices.UNVERIFIABLE)
    news_check.is_fake = ai_result.get('is_fake', False) or ai_verdict in ['false', 'false-fake']
    news_check.ai_response = ai_result.get('summary', '')

    # Додаємо інформацію про домен до JSON
    ai_result['domain_info'] = domain_info
    news_check.ai_verdict_json = ai_result
    
    if 'artifacts' in ai_result:
        news_check.pipeline_artifacts = ai_result.pop('artifacts')

    news_check.save(update_fields=[
        'verdict', 'is_fake',
        'ai_response', 'ai_verdict_json', 'pipeline_artifacts', 'updated_at'
    ])

    # Очищуємо кеш історії
    try:
        from django.core.cache import cache
        from django_redis import get_redis_connection
        
        # Видаляємо всі ключі історії
        redis_conn = get_redis_connection("default")
        history_keys = redis_conn.keys("*news_history_*")
        if history_keys:
            redis_conn.delete(*history_keys)
            logger.info(f"Кеш історії очищено ({len(history_keys)} ключів)")
    except Exception as e:
        logger.warning(f"Помилка очищення кешу історії: {e}")

    logger.info(f"Результат збережено: NewsCheck id={news_check.id}, verdict={ai_verdict}")

    # Збережемо parser debug info в окрему записі БД
    if parsed_info:
        try:
            ParserDebugInfo.objects.update_or_create(
                news_check=news_check,
                defaults={
                    'parsed_title': (parsed_info.get('title') or '')[:500],
                    'parsed_text': parsed_info.get('text', ''),
                    'parsed_authors': parsed_info.get('authors', []),
                    'parsed_publish_date': str(parsed_info.get('publish_date', '')) or None,
                    'parsed_domain': parsed_info.get('domain', ''),
                    'parsed_meta_description': parsed_info.get('meta_description', ''),
                    'parsed_word_count': parsed_info.get('word_count', 0),
                    'parsers_debug': parsed_info.get('parsers_debug', []),
                }
            )
            logger.info(f"ParserDebugInfo збережено для NewsCheck id={news_check.id}")
        except Exception as e:
            logger.warning(f"Помилка збереження ParserDebugInfo: {e}")

    result = _format_result(news_check, parsed_info)
    result['_is_error'] = is_error
    return result


def _format_result(news_check: NewsCheck, parsed_info: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Форматує результат для відповіді API та кешування.
    debug_info завжди підтягується з БД (ParserDebugInfo), якщо доступна.

    Args:
        news_check: Об'єкт NewsCheck з БД
        parsed_info: Інформація про парсинг (для свіжої перевірки)

    Returns:
        Словник з результатом перевірки
    """
    ai_json = news_check.ai_verdict_json or {}

    result = {
        'id': news_check.id,
        'url': news_check.url,
        'url_hash': news_check.url_hash,
        'title': news_check.title,
        'source_domain': news_check.source_domain,
        'verdict': news_check.verdict,
        'verdict_display': news_check.get_verdict_display(),
        'is_fake': news_check.is_fake,
        'ai_verdict_json': ai_json,
        'summary': ai_json.get('summary', news_check.ai_response),
        'recommendation': ai_json.get('recommendation', ''),
        'analysis': ai_json.get('analysis', {}),
        'checked_at': news_check.updated_at.isoformat(),
        'cached': False
    }

    # 1. Намагаємось завантажити debug_info з БД (ParserDebugInfo) — працює і для кешу
    try:
        parser_debug = ParserDebugInfo.objects.get(news_check=news_check)
        result['debug_info'] = parser_debug.to_dict()
    except ParserDebugInfo.DoesNotExist:
        # 2. Якщо в БД нема запису — намагаємось використати parsed_info (для свіжої перевірки)
        if parsed_info:
            result['debug_info'] = {
                'parsed_title': parsed_info.get('title', '')[:100],
                'parsed_text': parsed_info.get('text', ''),
                'parsed_authors': parsed_info.get('authors', []),
                'parsed_publish_date': parsed_info.get('publish_date'),
                'parsed_domain': parsed_info.get('domain', ''),
                'parsed_meta_description': parsed_info.get('meta_description', ''),
                'parsed_word_count': parsed_info.get('word_count', 0),
                'parsers_debug': parsed_info.get('parsers_debug', [])
            }

    return result


def _cache_result(url: str, result: Dict[str, Any]) -> None:
    """
    Кешує результат в Redis.
    Логіка кешування (ігнорування помилок) перенесена в NewsCacheService.

    Args:
        url: URL новини
        result: Результат перевірки
    """
    try:
        news_cache_service.set(url, result)
    except Exception as e:
        logger.error(f"Помилка кешування: {str(e)}")
        # Не викидаємо помилку - кешування не критичне


@shared_task(bind=True)
def cleanup_old_cache(self) -> Dict[str, int]:
    """
    Періодична задача для очищення старого кешу.
    Можна налаштувати в Celery Beat.
    """
    # Поки що просто логуємо
    logger.info("Запуск очищення старого кешу...")
    return {'cleaned': 0}


