# ==============================================================================
# NEWSFILTERAI - NEWS VIEWS (API Endpoints)
# ==============================================================================
# API endpoints для перевірки новин на достовірність

import logging
import traceback
from celery.result import AsyncResult

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from django.conf import settings

from .models import NewsCheck
from .serializers import (
    NewsCheckInputSerializer,
    NewsCheckSerializer,
    NewsCheckShortSerializer,
)
from .services import domain_list_service, news_cache_service
from .tasks import check_news_task

logger = logging.getLogger(__name__)

# Debug mode - показувати детальні помилки
DEBUG_MODE = getattr(settings, 'DEBUG', False)


class HealthCheckView(APIView):
    """
    Health check endpoint для перевірки працездатності API.
    GET /api/health/
    """

    def get(self, request):
        return Response({
            'status': 'healthy',
            'service': 'NewsFilter API',
            'version': '1.0.0'
        }, status=status.HTTP_200_OK)


class CheckNewsView(APIView):
    """
    Endpoint для перевірки новини на достовірність.
    POST /api/check/

    Алгоритм:
    1. Перевіряє Redis кеш - якщо є, повертає одразу (Cache HIT)
    2. Якщо немає - створює запис в БД та запускає Celery задачу
    3. Повертає task_id для polling статусу

    Request body:
        {"url": "https://example.com/news/article"}

    Response (Cache HIT):
        {"cached": true, "result": {...}}

    Response (Cache MISS):
        {"cached": false, "task_id": "...", "status": "processing", "check_id": 123}
    """

    def post(self, request):
        # Валідуємо вхідні дані
        serializer = NewsCheckInputSerializer(data=request.data)

        if not serializer.is_valid():
            return Response({
                'error': 'Невалідні дані',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        url = serializer.validated_data['url']
        logger.info(f"Отримано запит на перевірку: {url[:60]}...")

        # =====================================================================
        # КРОК 1: Перевіряємо Redis кеш
        # =====================================================================
        try:
            cached_result = news_cache_service.get(url)

            if cached_result:
                logger.info(f"Cache HIT для {url[:50]}...")
                return Response({
                    'cached': True,
                    'result': cached_result
                }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.warning(f"Помилка перевірки кешу: {str(e)}\n{traceback.format_exc()}")
            # Продовжуємо без кешу

        logger.info(f"Cache MISS для {url[:50]}...")

        # =====================================================================
        # КРОК 2: Перевіряємо/створюємо запис в БД
        # =====================================================================
        try:
            # Генеруємо hash для URL
            url_hash = NewsCheck.generate_url_hash(url)

            # Перевіряємо чи вже є запис для цього URL
            existing_check = NewsCheck.objects.filter(url_hash=url_hash).first()

            if existing_check:
                # Запис вже існує - перевіряємо його статус
                if existing_check.verdict == NewsCheck.VerdictChoices.PENDING and existing_check.task_id:
                    # Вже є активна задача - повертаємо її ID
                    logger.info(f"Знайдено активну задачу: {existing_check.task_id}")
                    return Response({
                        'cached': False,
                        'status': 'already_processing',
                        'task_id': existing_check.task_id,
                        'check_id': existing_check.id,
                        'message': 'Ця новина вже перевіряється'
                    }, status=status.HTTP_202_ACCEPTED)

                # Перевіряємо чи це помилка (ERROR verdict або parse_error в JSON)
                is_error_result = (
                    existing_check.verdict == NewsCheck.VerdictChoices.ERROR or
                    (existing_check.ai_verdict_json and existing_check.ai_verdict_json.get('error')) or
                    (existing_check.ai_verdict_json and existing_check.ai_verdict_json.get('parse_error'))
                )

                if is_error_result:
                    # Попередня перевірка була з помилкою - спробуємо ще раз
                    logger.info(f"Попередня перевірка завершилась з помилкою, повторюємо спробу: {existing_check.id}")
                    existing_check.verdict = NewsCheck.VerdictChoices.PENDING
                    # Уникнути збереження NULL у CharField task_id -> використати пусту строку
                    existing_check.task_id = ''
                    existing_check.ai_verdict_json = {}  # Пустий dict замість None
                    existing_check.ai_response = ''
                    existing_check.save(update_fields=['verdict', 'task_id', 'ai_verdict_json', 'ai_response', 'updated_at'])
                    news_check = existing_check

                else:
                    # Є успішний результат - повертаємо його
                    logger.info(f"Знайдено існуючий результат в БД: {existing_check.id}")
                    from .tasks import _format_result
                    result = _format_result(existing_check)
                    # Кешуємо результат в Redis
                    news_cache_service.set(url, {**result, 'cached': True})
                    return Response({
                        'cached': True,
                        'result': result
                    }, status=status.HTTP_200_OK)
            else:
                # Створюємо новий запис
                news_check = NewsCheck.objects.create(
                    url=url,
                    url_hash=url_hash,
                    verdict=NewsCheck.VerdictChoices.PENDING
                )
                logger.info(f"Створено NewsCheck id={news_check.id}")

        except Exception as e:
            error_trace = traceback.format_exc()
            logger.error(f"Помилка створення запису в БД: {str(e)}\n{error_trace}")
            error_response = {
                'error': 'Помилка сервера при створенні запису',
                'error_code': 'DB_CREATE_ERROR',
                'message': str(e)
            }
            if DEBUG_MODE:
                error_response['traceback'] = error_trace
            return Response(error_response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # =====================================================================
        # КРОК 3: Запускаємо Celery задачу
        # =====================================================================
        try:
            task = check_news_task.delay(url, news_check.id)

            # Зберігаємо task_id в БД
            news_check.task_id = task.id
            news_check.save(update_fields=['task_id'])

            logger.info(f"Запущено Celery задачу: {task.id}")

            return Response({
                'cached': False,
                'status': 'processing',
                'task_id': task.id,
                'check_id': news_check.id,
                'message': 'Новина відправлена на перевірку. Використовуйте task_id для отримання результату.'
            }, status=status.HTTP_202_ACCEPTED)

        except Exception as e:
            error_trace = traceback.format_exc()
            logger.error(f"Помилка запуску Celery задачі: {str(e)}\n{error_trace}")

            # Оновлюємо статус на помилку
            news_check.verdict = NewsCheck.VerdictChoices.ERROR
            news_check.ai_response = f"Помилка запуску задачі: {str(e)}"
            news_check.save()

            error_response = {
                'error': 'Помилка запуску задачі перевірки',
                'error_code': 'CELERY_TASK_ERROR',
                'message': str(e)
            }
            if DEBUG_MODE:
                error_response['traceback'] = error_trace
            return Response(error_response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TaskStatusView(APIView):
    """
    Endpoint для перевірки статусу Celery задачі.
    GET /api/task-status/<task_id>/

    Response:
        - PENDING: {"status": "pending", "message": "Задача в черзі"}
        - STARTED: {"status": "started", "message": "Задача виконується"}
        - SUCCESS: {"status": "success", "result": {...}}
        - FAILURE: {"status": "failure", "error": "..."}
    """

    def get(self, request, task_id):
        try:
            # Отримуємо статус задачі з Celery
            task_result = AsyncResult(task_id)

            response_data = {
                'task_id': task_id,
                'status': task_result.status.lower(),
            }

            if task_result.status == 'PENDING':
                response_data['message'] = 'Задача в черзі на обробку'

            elif task_result.status == 'STARTED':
                response_data['message'] = 'Задача виконується'

            elif task_result.status == 'SUCCESS':
                response_data['result'] = task_result.result
                response_data['message'] = 'Перевірка завершена'

            elif task_result.status == 'FAILURE':
                response_data['error'] = str(task_result.result)
                response_data['message'] = 'Помилка при перевірці'

            else:
                response_data['message'] = f'Статус: {task_result.status}'

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Помилка отримання статусу задачі {task_id}: {str(e)}")
            return Response({
                'task_id': task_id,
                'status': 'error',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class NewsCheckDetailView(APIView):
    """
    Endpoint для отримання деталей перевірки за ID.
    GET /api/check/<check_id>/
    """

    def get(self, request, check_id):
        try:
            news_check = NewsCheck.objects.get(id=check_id)
            serializer = NewsCheckSerializer(news_check)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except NewsCheck.DoesNotExist:
            return Response({
                'error': 'Перевірку не знайдено',
                'check_id': check_id
            }, status=status.HTTP_404_NOT_FOUND)


class NewsCheckHistoryView(APIView):
    """
    Endpoint для отримання історії перевірок.
    GET /api/history/

    Query params:
        - limit: кількість записів (default: 20, max: 100)
        - offset: зміщення для пагінації
        - domain: фільтр по домену
        - verdict: фільтр по вердикту
    """

    def get(self, request):
        # Параметри пагінації
        limit = min(int(request.query_params.get('limit', 20)), 100)
        offset = int(request.query_params.get('offset', 0))

        # Фільтри
        domain = request.query_params.get('domain')
        verdict = request.query_params.get('verdict')

        # Check cache if no filters and offset=0
        cache_key = None
        if offset == 0 and not domain and not verdict:
            cache_key = f"news_history_l{limit}"
            from django.core.cache import cache
            cached_data = cache.get(cache_key)
            if cached_data:
                return Response(cached_data, status=status.HTTP_200_OK)

        # Базовий queryset
        queryset = NewsCheck.objects.exclude(
            verdict=NewsCheck.VerdictChoices.PENDING
        ).order_by('-created_at')

        # Застосовуємо фільтри
        if domain:
            queryset = queryset.filter(source_domain__icontains=domain)
        if verdict:
            queryset = queryset.filter(verdict=verdict)

        # Пагінація
        total = queryset.count()
        news_checks = queryset[offset:offset + limit]

        serializer = NewsCheckShortSerializer(news_checks, many=True)

        response_data = {
            'total': total,
            'limit': limit,
            'offset': offset,
            'results': serializer.data
        }

        # Save to cache for 1 minute if no filters and offset=0
        if cache_key:
            from django.core.cache import cache
            cache.set(cache_key, response_data, 60)

        return Response(response_data, status=status.HTTP_200_OK)


class DomainCheckView(APIView):
    """
    Endpoint для перевірки репутації домену.
    GET /api/domain-check/?domain=example.com
    POST /api/domain-check/ {"url": "https://example.com/..."}
    """

    def get(self, request):
        domain = request.query_params.get('domain')

        if not domain:
            return Response({
                'error': 'Параметр domain обов\'язковий'
            }, status=status.HTTP_400_BAD_REQUEST)

        result = domain_list_service.check_domain(domain)
        return Response(result, status=status.HTTP_200_OK)

    def post(self, request):
        url = request.data.get('url')

        if not url:
            return Response({
                'error': 'Поле url обов\'язкове'
            }, status=status.HTTP_400_BAD_REQUEST)

        result = domain_list_service.check_url(url)
        return Response(result, status=status.HTTP_200_OK)


class DomainListView(APIView):
    """
    Endpoint для отримання списків доменів.
    GET /api/domains/
    GET /api/domains/?type=whitelist
    GET /api/domains/?type=blacklist
    """

    def get(self, request):
        list_type = request.query_params.get('type', 'all')

        result = {
            'stats': domain_list_service.get_stats()
        }

        if list_type in ['all', 'whitelist']:
            result['whitelist'] = domain_list_service.get_whitelist()

        if list_type in ['all', 'blacklist']:
            result['blacklist'] = domain_list_service.get_blacklist()

        return Response(result, status=status.HTTP_200_OK)


class DebugCheckView(APIView):
    """
    Debug endpoint для діагностики проблем з перевіркою новин.
    POST /api/debug/check/

    Виконує покрокову діагностику:
    1. Перевірка URL валідації
    2. Перевірка Redis кешу
    3. Перевірка підключення до БД
    4. Перевірка Celery
    5. Перевірка парсингу статті
    6. Перевірка Gemini API
    """

    def post(self, request):
        from .parser_service import article_parser
        from .ai_service import get_gemini_service
        from celery import current_app as celery_app
        import redis

        url = request.data.get('url', '')
        steps = []
        overall_success = True

        # =================================================================
        # КРОК 1: Валідація URL
        # =================================================================
        step1 = {'step': 1, 'name': 'URL Validation', 'success': False}
        try:
            serializer = NewsCheckInputSerializer(data={'url': url})
            if serializer.is_valid():
                step1['success'] = True
                step1['message'] = f"URL валідний: {url[:60]}..."
                step1['validated_url'] = serializer.validated_data['url']
            else:
                step1['message'] = f"URL невалідний: {serializer.errors}"
                overall_success = False
        except Exception as e:
            step1['message'] = f"Помилка валідації: {str(e)}"
            step1['traceback'] = traceback.format_exc()
            overall_success = False
        steps.append(step1)

        if not step1['success']:
            return Response({
                'overall_success': False,
                'steps': steps,
                'error': 'Перевірку зупинено через невалідний URL'
            }, status=status.HTTP_400_BAD_REQUEST)

        # =================================================================
        # КРОК 2: Перевірка Redis
        # =================================================================
        step2 = {'step': 2, 'name': 'Redis Connection', 'success': False}
        try:
            from django_redis import get_redis_connection
            redis_conn = get_redis_connection("default")
            redis_conn.ping()
            step2['success'] = True
            step2['message'] = "Redis підключено успішно"

            # Перевіряємо кеш
            cached = news_cache_service.get(url)
            step2['cached_result'] = cached is not None
            if cached:
                step2['cached_data'] = cached
        except Exception as e:
            step2['message'] = f"Помилка Redis: {str(e)}"
            step2['traceback'] = traceback.format_exc()
            overall_success = False
        steps.append(step2)

        # =================================================================
        # КРОК 3: Перевірка PostgreSQL
        # =================================================================
        step3 = {'step': 3, 'name': 'Database Connection', 'success': False}
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            step3['success'] = True
            step3['message'] = "PostgreSQL підключено успішно"
            step3['news_check_count'] = NewsCheck.objects.count()
        except Exception as e:
            step3['message'] = f"Помилка PostgreSQL: {str(e)}"
            step3['traceback'] = traceback.format_exc()
            overall_success = False
        steps.append(step3)

        # =================================================================
        # КРОК 4: Перевірка Celery
        # =================================================================
        step4 = {'step': 4, 'name': 'Celery Connection', 'success': False}
        try:
            inspector = celery_app.control.inspect()
            active_workers = inspector.active()
            if active_workers:
                step4['success'] = True
                step4['message'] = f"Celery працює. Workers: {list(active_workers.keys())}"
                step4['workers'] = list(active_workers.keys())
            else:
                step4['message'] = "Немає активних Celery workers!"
                overall_success = False
        except Exception as e:
            step4['message'] = f"Помилка Celery: {str(e)}"
            step4['traceback'] = traceback.format_exc()
            overall_success = False
        steps.append(step4)

        # =================================================================
        # КРОК 5: Перевірка парсингу статті
        # =================================================================
        step5 = {'step': 5, 'name': 'Article Parsing', 'success': False}
        try:
            parsed = article_parser.parse_url(url)
            if parsed['success']:
                step5['success'] = True
                step5['message'] = f"Парсинг успішний: '{parsed['title'][:50]}...'"
                step5['parsed_data'] = {
                    'title': parsed['title'][:100],
                    'text_length': len(parsed['text']),
                    'word_count': parsed['word_count'],
                    'domain': parsed['domain'],
                    'has_authors': len(parsed['authors']) > 0
                }
            else:
                step5['message'] = f"Помилка парсингу: {parsed['error']}"
                overall_success = False
        except Exception as e:
            step5['message'] = f"Виняток при парсингу: {str(e)}"
            step5['traceback'] = traceback.format_exc()
            overall_success = False
        steps.append(step5)

        # =================================================================
        # КРОК 6: Перевірка Gemini API (тільки ініціалізація)
        # =================================================================
        step6 = {'step': 6, 'name': 'Gemini AI API', 'success': False}
        try:
            gemini_service = get_gemini_service()
            step6['success'] = True
            step6['message'] = "Gemini AI сервіс ініціалізовано успішно"
            step6['model'] = getattr(settings, 'GEMINI_MODEL_NAME', 'gemini-1.5-flash')
        except Exception as e:
            step6['message'] = f"Помилка Gemini: {str(e)}"
            step6['traceback'] = traceback.format_exc()
            overall_success = False
        steps.append(step6)

        # =================================================================
        # КРОК 7: Перевірка домену
        # =================================================================
        step7 = {'step': 7, 'name': 'Domain Check', 'success': False}
        try:
            domain_info = domain_list_service.check_url(url)
            step7['success'] = True
            step7['message'] = f"Домен: {domain_info['domain']}, репутація: {domain_info['reputation']}"
            step7['domain_info'] = domain_info
        except Exception as e:
            step7['message'] = f"Помилка перевірки домену: {str(e)}"
            step7['traceback'] = traceback.format_exc()
            overall_success = False
        steps.append(step7)

        return Response({
            'overall_success': overall_success,
            'url': url,
            'steps': steps,
            'summary': {
                'total_steps': len(steps),
                'successful_steps': sum(1 for s in steps if s['success']),
                'failed_steps': [s['name'] for s in steps if not s['success']]
            }
        }, status=status.HTTP_200_OK if overall_success else status.HTTP_500_INTERNAL_SERVER_ERROR)


class ClearCacheView(APIView):
    """
    Endpoint для очищення кешу.
    POST /api/cache/clear/ - очистити весь кеш
    POST /api/cache/clear/ {"url": "..."} - очистити кеш для конкретного URL
    DELETE /api/cache/clear/ - очистити весь кеш
    """

    def post(self, request):
        from django.core.cache import cache

        url = request.data.get('url')

        if url:
            # Очищаємо кеш для конкретного URL
            news_cache_service.delete(url)
            return Response({
                'success': True,
                'message': f'Кеш для URL очищено',
                'url': url
            }, status=status.HTTP_200_OK)
        else:
            # Очищаємо весь кеш
            cache.clear()
            return Response({
                'success': True,
                'message': 'Весь кеш очищено'
            }, status=status.HTTP_200_OK)

    def delete(self, request):
        from django.core.cache import cache
        cache.clear()
        return Response({
            'success': True,
            'message': 'Весь кеш очищено'
        }, status=status.HTTP_200_OK)


class NewsCheckBulkDeleteView(APIView):
    """
    Endpoint для масового видалення перевірок.
    POST /api/history/delete/ {"ids": [1, 2, 3]}
    """

    def post(self, request):
        ids = request.data.get('ids', [])
        if not ids:
            return Response({
                'success': False,
                'error': 'Не вказано ID для видалення'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Отримуємо об'єкти для видалення (щоб знати їх URL для очищення кешу)
        news_checks = NewsCheck.objects.filter(id__in=ids)
        
        count = 0
        urls_to_clear = []
        for check in news_checks:
            urls_to_clear.append(check.url)
            check.delete()
            count += 1
            
        # Очищаємо кеш Redis для кожного URL
        for url in urls_to_clear:
            news_cache_service.delete(url)
            
        # Очищаємо кеш історії
        from django.core.cache import cache
        # Спробуємо видалити відомі ключі пагінації
        cache.delete("news_history_l20")
        cache.delete("news_history_l100")
        # Якщо використовується django-redis, можна спробувати видалити за шаблоном
        try:
            cache.delete_pattern("news_history_*")
        except AttributeError:
            pass
        
        return Response({
            'success': True,
            'deleted_count': count
        }, status=status.HTTP_200_OK)
