# ==============================================================================
# NEWSFILTERAI - AI SERVICE (Google Gemini)
# ==============================================================================
# Сервіс для взаємодії з Google Gemini AI API

import logging
import json
import re
import requests
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import subprocess
import sys
import os

from django.conf import settings
from google.genai import types

from .constants import MAX_CONTENT_LENGTH, AI_REQUEST_TIMEOUT

logger = logging.getLogger(__name__)


def get_current_time_from_internet() -> datetime:
    """
    Отримує поточний час з інтернету (UTC).
    Використовує кілька надійних джерел з fallback на системний час.
    
    Returns:
        datetime: Поточний час в UTC timezone
    """
    # Спробуємо кілька надійних API джерел
    api_sources = [
        'http://worldtimeapi.org/api/timezone/Etc/UTC',
        'https://timeapi.io/api/Time/current/zone?timeZone=UTC',
    ]
    
    # Спочатку пробуємо API джерела
    for source in api_sources:
        try:
            response = requests.get(source, timeout=2)
            if response.status_code == 200:
                data = response.json()
                
                # World Time API
                if 'datetime' in data:
                    time_str = data.get('datetime')
                    dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                    logger.info(f"✅ Отримано час з {source}")
                    return dt
                
                # TimeAPI.io
                elif 'dateTime' in data:
                    time_str = data.get('dateTime')
                    dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                    logger.info(f"✅ Отримано час з {source}")
                    return dt
                    
        except Exception as e:
            logger.debug(f"Не вдалося отримати час з {source}: {str(e)[:100]}")
            continue
    
    # Якщо API недоступний, спробуємо отримати час з HTTP заголовків
    http_sources = [
        'https://www.google.com',
        'https://www.cloudflare.com',
    ]
    
    for source in http_sources:
        try:
            response = requests.head(source, timeout=2)
            if 'Date' in response.headers:
                from email.utils import parsedate_to_datetime
                dt = parsedate_to_datetime(response.headers['Date'])
                logger.info(f"✅ Отримано час з HTTP заголовків {source}")
                return dt
        except Exception as e:
            logger.debug(f"Не вдалося отримати час з {source}: {str(e)[:100]}")
            continue
    
    # Якщо всі джерела недоступні - використовуємо системний час
    logger.warning("⚠️ Не вдалося отримати час з інтернету, використовуємо системний час UTC")
    return datetime.now(timezone.utc)


class GeminiAIService:
    """
    Сервіс для перевірки новин на достовірність через Google Gemini AI.

    Можливості:
    - Перевірка фактів у новинах
    - Аналіз достовірності джерела
    - Виявлення маніпуляцій та пропаганди

    Використання:
        service = GeminiAIService()
        result = service.verify_news(title="...", content="...", url="...")
    """

    # Оновлений промпт - FLAT JSON (більш надійний для AI)
    VERIFICATION_PROMPT = """
Ти — експерт з фактчекінгу. Проаналізуй новину та надай результат ТІЛЬКИ у форматі JSON.

**ПОТОЧНА ДАТА:** {current_date}
**ЗАГОЛОВОК:** {title}
**ТЕКСТ:** {content}
**URL:** {url}

---

**ПРАВИЛА:**
1. Використовуй вказану поточну дату. Новини про майбутні події (анонси) - це НЕ фейки.
2. В полі 'summary' ПИШИ АНАЛІЗ (2-3 речення), а не просто вердикт!
3. Якщо summary занадто коротке (менше 10 слів), це буде вважатися помилкою.

**ФОРМАТ ВІДПОВІДІ (JSON):**
{{
    "verdict": "true" | "false" | "partial" | "unverifiable",
    "confidence_score": 0-100,
    "summary": "Детальний опис результатів аналізу своїми словами",
    "factual_accuracy": "Оцінка точності фактів (що підтверджено/спростовано)",
    "source_credibility": "Оцінка надійності джерела за цим URL",
    "manipulation_signs": ["ознака 1", "ознака 2"],
    "recommendation": "Порада користувачу"
}}

**ВАЖЛИВО:**
- НЕ пиши "Verdict: false" у summary.
- НЕ використовуй ```json.
- Повертай тільки один JSON об'єкт.
"""


    def __init__(self):
        """Ініціалізація Gemini AI клієнта"""
        self.api_key = settings.GEMINI_API_KEY

        if not self.api_key:
            logger.warning("GEMINI_API_KEY не налаштований!")
            raise ValueError("GEMINI_API_KEY не налаштований. Додайте його до .env файлу.")

        # Замість створення клієнта тут, ми будемо використовувати окремий раннер
        self.model_name = getattr(settings, 'GEMINI_MODEL_NAME', 'gemini-2.5-flash')
        logger.info(f"Ініціалізація Gemini з моделлю: {self.model_name}")

        # Налаштування генерації - оптимізовані для фактчекінгу
        try:
            self.generation_config = types.GenerateContentConfig(
                temperature=0.1,  # Низька температура для стабільних відповідей
                top_p=0.95,
                top_k=40,
                max_output_tokens=4096,  # Достатньо для детальної відповіді
            )
        except Exception:
            # Якщо types не доступний (наприклад у тестах), дозволяємо None
            self.generation_config = None

    def run_gemini_subprocess(self, prompt, model_name=None, timeout=90, max_output_tokens=2048):
        """
        Викликає зовнішній скрипт _gemini_runner.py для роботи з Google GenAI SDK.
        Це дозволяє уникнути проблем з gRPC та fork() у Celery.
        """
        # Використовуємо передану модель або ту, що за замовчуванням
        target_model = model_name or self.model_name
        
        runner_path = os.path.join(os.path.dirname(__file__), '_gemini_runner.py')

        payload = {
            'prompt': prompt,
            'model': target_model,
        }
        if isinstance(max_output_tokens, int):
            payload['max_output_tokens'] = max_output_tokens

        input_bytes = json.dumps(payload).encode('utf-8')

        # Use sys.executable to ensure same Python interpreter
        cmd = [sys.executable, '-u', runner_path]

        try:
            proc = subprocess.run(
                cmd,
                input=input_bytes,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
            )

            stdout = proc.stdout.decode('utf-8', errors='replace')
            stderr = proc.stderr.decode('utf-8', errors='replace')

            if proc.returncode != 0:
                # Виводимо повний stderr для професійної діагностики
                error_msg = stderr.strip() if stderr else "No error message"
                logger.error(f"\n{'!'*20} GEMINI RUNNER FAILURE {'!'*20}\n{error_msg}\n{'!'*40}")
                raise RuntimeError(f"AI_ERROR: {error_msg}")

            return stdout

        except subprocess.TimeoutExpired as e:
            logger.error(f"Gemini runner timeout after {timeout}s")
            raise
        except Exception as e:
            logger.exception("Unexpected error when running gemini subprocess")
            raise

    def verify_news(
        self,
        title: str,
        content: str,
        url: str
    ) -> Dict[str, Any]:
        """
        Перевіряє новину на достовірність через Gemini AI.

        Args:
            title: Заголовок новини
            content: Текст новини
            url: URL джерела

        Returns:
            Словник з результатом перевірки:
            {
                'verdict': str,
                'confidence_score': int,
                'is_fake': bool,
                'summary': str,
                'analysis': dict,
                'recommendation': str
            }
        """
        try:
            # Обмежуємо довжину контенту
            if len(content) > MAX_CONTENT_LENGTH:
                content = content[:MAX_CONTENT_LENGTH] + "\n\n[...текст обрізано для аналізу...]"
                logger.info(f"Контент обрізано до {MAX_CONTENT_LENGTH} символів")

            # Отримуємо поточну дату і час з інтернету (UTC)
            current_datetime = get_current_time_from_internet()
            # Форматуємо в зрозумілому вигляді: "29 грудня 2024 року, 15:47 UTC"
            months_uk = [
                'січня', 'лютого', 'березня', 'квітня', 'травня', 'червня',
                'липня', 'серпня', 'вересня', 'жовтня', 'листопада', 'грудня'
            ]
            current_date_str = f"{current_datetime.day} {months_uk[current_datetime.month - 1]} {current_datetime.year} року, {current_datetime.strftime('%H:%M')} UTC"
            logger.info(f"Поточна дата для AI: {current_date_str}")
            
            # Формуємо промпт з поточною датою
            prompt = self.VERIFICATION_PROMPT.format(
                current_date=current_date_str,
                title=title or "Без заголовку",
                content=content or "Текст відсутній",
                url=url
            )

            logger.info(f"Запит до Gemini AI ({self.model_name}): {url[:50]}...")
            logger.debug(f"Довжина промпту: {len(prompt)} символів")

            # ПРОФЕСІЙНИЙ ЛАНЦЮЖОК FALLBACK (на основі ваших доступних моделей)
            fallback_chain = ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-3-flash", "gemini-2.0-flash-exp", "gemini-1.5-flash"]
            
            # Якщо поточна модель не в списку, додаємо її на початок
            if self.model_name not in fallback_chain:
                fallback_chain.insert(0, self.model_name)
            
            raw_response = None
            last_error = None
            
            for model_attempt in fallback_chain:
                try:
                    logger.info(f"Спроба отримати аналіз від моделі: {model_attempt}")
                    
                    # Викликаємо раннер
                    raw_response = self.run_gemini_subprocess(prompt, model_name=model_attempt, timeout=AI_REQUEST_TIMEOUT, max_output_tokens=4096)
                    if raw_response:
                        logger.info(f"✅ Успішно отримано результат від {model_attempt}")
                        break # Успіх!
                        
                except Exception as e:
                    last_error = e
                    error_str = str(e).upper()
                    # КРИТИЧНО ПРАВИЛЬНА ЛОГІКА: 
                    # Якщо квота вичерпана (429) АБО модель не знайдена (404), пробуємо наступну!
                    if any(x in error_str for x in ["RESOURCE_EXHAUSTED", "429", "QUOTA", "NOT_FOUND", "404"]):
                        logger.warning(f"Модель {model_attempt} недоступна або ліміт вичерпано. Пробую наступну в ланцюжку...")
                        continue
                    else:
                        # Якщо це інша помилка (наприклад, мережевий збій), повертаємо її
                        return self._error_response(f"Помилка AI ({model_attempt}): {str(e)}")
            
            if not raw_response:
                return self._error_response(f"На жаль, усі доступні моделі AI (Gemini 2.5, 3, 2.0) вичерпали свої ліміти. Останній статус: {str(last_error)}")

            # Логуємо успіх
            logger.debug(f"AI обробка завершена успішно")

            # Парсимо відповідь
            result = self._parse_response(raw_response)

            logger.info(
                f"Gemini verdict: {result.get('verdict')} "
                f"(confidence: {result.get('confidence_score')}%)"
            )

            return result

        except Exception as e:
            logger.error(f"Помилка Gemini AI: {str(e)}")
            return self._error_response(str(e))

    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """
        Парсить JSON відповідь від Gemini.

        Args:
            response_text: Текстова відповідь від AI

        Returns:
            Розпарсений JSON або error response
        """
        try:
            logger.debug(f"Парсинг відповіді довжиною {len(response_text)} символів")

            # Очищаємо відповідь від markdown code blocks
            clean_text = response_text.strip()

            # Видаляємо ```json ... ``` або ``` ... ```
            if clean_text.startswith('```'):
                first_newline = clean_text.find('\n')
                if first_newline != -1:
                    clean_text = clean_text[first_newline + 1:]
                if clean_text.endswith('```'):
                    clean_text = clean_text[:-3]
                clean_text = clean_text.strip()

            logger.debug(f"Очищений текст (перші 200 символів): {clean_text[:200]}")

            # 1) Спроба розпарсити всю відповідь як JSON
            try:
                result = json.loads(clean_text)
                logger.debug("JSON успішно розпарсено напряму")
            except Exception:
                result = None

            # 2) Якщо прямий парсинг не вдався — намагаємося відновити JSON-фрагмент
            if result is None:
                json_start = clean_text.find('{')
                if json_start == -1:
                    logger.warning("JSON не знайдено у відповіді Gemini (не знайдено '{')")
                    logger.warning(f"Перші 500 символів очищеної відповіді: {clean_text[:500]}")
                    return self._fallback_response(response_text)

                frag = clean_text[json_start:]
                logger.debug(f"Знайдено JSON-фрагмент довжиною {len(frag)} символів, пробуємо відновити")

                # Балансування фігурних дужок
                open_braces = frag.count('{')
                close_braces = frag.count('}')
                frag_fixed = frag + ('}' * (open_braces - close_braces)) if open_braces > close_braces else frag

                # Видаляємо зайві коми перед закриваючою дужкою
                frag_fixed = re.sub(r',\s*,', ',', frag_fixed)
                frag_fixed = re.sub(r',\s*(}+)', r'\g<1>', frag_fixed)

                # Додаткові спроби "виправити" часткові числові/булеві значення
                # Приклади: "confidence_score": 1...  -> "confidence_score": 1
                frag_fixed = re.sub(r'("confidence_score"\s*:\s*\d+)[^\d},\n\r]*', r'\g<1>', frag_fixed)
                # Якщо після key немає числа, підставимо 0
                frag_fixed = re.sub(r'("confidence_score"\s*:\s*)([^0-9-\s"]+)([,}])', r'\g<1>0\g<3>', frag_fixed)
                # Спроба полагодити is_fake якщо там обрізано (true/false)
                frag_fixed = re.sub(r'("is_fake"\s*:\s*)(true|false)[^a-zA-Z]*', r'\g<1>\g<2>', frag_fixed)

                # Намагаємося розпарсити відновлений фрагмент
                try:
                    result = json.loads(frag_fixed)
                    logger.info("Успішно відновили та розпарсили JSON-фрагмент з відповіді AI")
                except Exception as e:
                    logger.warning(f"Не вдалося відновити JSON-фрагмент: {e}")
                    # Спробуємо витягти часткові поля
                    result = self._extract_partial_json(frag)
                    if result is None:
                        logger.debug(f"Фрагмент для дебагу: {frag[:1000]}")
                        return self._fallback_response(response_text)

            # Тепер у нас повинен бути словник result
            if not isinstance(result, dict):
                result = {}

            # --- РОЗШИРЕНИЙ ВИДОБУТОК (якщо JSON був неповним або дивним) ---
            # Завжди пробуємо витягти поля регулярками для надійності
            extracted = self._extract_partial_json(response_text)
            if extracted:
                for k, v in extracted.items():
                    if v and (k not in result or not result[k]):
                        result[k] = v
                
                # Окремо для вкладеного аналізу
                if 'analysis' in extracted and isinstance(extracted['analysis'], dict):
                    if 'analysis' not in result or not isinstance(result['analysis'], dict):
                        result['analysis'] = {}
                    for ak, av in extracted['analysis'].items():
                        if av and (ak not in result['analysis'] or not result['analysis'][ak]):
                            result['analysis'][ak] = av

            logger.info(f"Дані зібрано: verdict={result.get('verdict')}, summary_len={len(str(result.get('summary', '')))}")

            # --- НОРМАЛІЗАЦІЯ ДАНИХ ---
            
            # 1. Поля аналізу можуть бути розкидані
            if 'analysis' not in result or not isinstance(result['analysis'], dict):
                result['analysis'] = {}
            
            for field in ['factual_accuracy', 'source_credibility', 'manipulation_signs', 'verified_facts']:
                if field in result and field not in result['analysis']:
                    val = result.pop(field)
                    if val: result['analysis'][field] = val

            # 2. Валідуємо обов'язкові поля
            required_fields = ['verdict', 'confidence_score', 'is_fake', 'summary']
            for field in required_fields:
                if not result.get(field):
                    result[field] = self._get_default_value(field)

            # 3. Виправляємо технічні summary
            summary = str(result.get('summary', ''))
            is_poor = len(summary) < 50 or 'verdict' in summary.lower() or summary.strip() == str(result.get('verdict'))
            
            if is_poor and result['analysis']:
                acc = result['analysis'].get('factual_accuracy', '')
                src = result['analysis'].get('source_credibility', '')
                combined = f"{acc} {src}".strip()
                if len(combined) > len(summary):
                    result['summary'] = combined

            # 4. Нормалізація статусів
            valid_v = ['true', 'false', 'partial', 'unverifiable']
            if result.get('verdict') not in valid_v:
                result['verdict'] = 'unverifiable'
            
            result['is_fake'] = result.get('verdict') == 'false'
            
            # Забезпечуємо наявність recommendation
            if not result.get('recommendation'):
                result['recommendation'] = self._get_default_value('recommendation')

            return result

        except Exception as e:
            logger.error(f"Неочікувана помилка парсингу: {e}")
            return self._fallback_response(response_text)

    def _get_default_value(self, field: str) -> Any:
        """Повертає значення за замовчуванням для поля"""
        defaults = {
            'verdict': 'unverifiable',
            'confidence_score': 0,
            'is_fake': False,
            'summary': 'Не вдалося провести аналіз',
            'analysis': {},
            'recommendation': 'Перевірте інформацію в інших джерелах'
        }
        return defaults.get(field)

    def _extract_partial_json(self, json_str: str) -> Optional[Dict[str, Any]]:
        """
        Витягує основні поля з неповного JSON або сильно пошкодженого тексту.
        """
        logger.info("Спроба випробувати розширений видобуток даних з тексту...")

        result = {}

        # 1. Прості поля (verdict, score, is_fake)
        verdict_match = re.search(r'"verdict"\s*:\s*"(true|false|partial|unverifiable)"', json_str)
        if verdict_match:
            result['verdict'] = verdict_match.group(1)
            
        confidence_match = re.search(r'"confidence_score"\s*:\s*(\d+)', json_str)
        if confidence_match:
            result['confidence_score'] = int(confidence_match.group(1))

        is_fake_match = re.search(r'"is_fake"\s*:\s*(true|false)', json_str)
        if is_fake_match:
            result['is_fake'] = is_fake_match.group(1) == 'true'

        # 2. Текстові поля (summary, recommendation) - шукаємо з урахуванням екранованих лапок
        # Regex: "key"\s*:\s*" ( (ек ранована лапка або не-лапка)* ) "
        def extract_text_field(field_name, text):
            # Шукаємо повне поле з закритими лапками
            pattern = rf'"{field_name}"\s*:\s*"((?:[^"\\]|\\.)*)"'
            match = re.search(pattern, text)
            if match:
                return match.group(1).replace('\\"', '"').replace('\\n', '\n')
            
            # Якщо лапка не закрита, беремо що є до кінця (якщо це останнє поле або обрізано)
            pattern_open = rf'"{field_name}"\s*:\s*"((?:[^"\\]|\\.)*)$'
            match_open = re.search(pattern_open, text)
            if match_open:
                return match_open.group(1).replace('\\"', '"').strip().rstrip(',')
            return None

        result['summary'] = extract_text_field('summary', json_str)
        result['recommendation'] = extract_text_field('recommendation', json_str)

        # 3. ПОЛЯ АНАЛІЗУ
        analysis = {}
        analysis['factual_accuracy'] = extract_text_field('factual_accuracy', json_str)
        analysis['source_credibility'] = extract_text_field('source_credibility', json_str)
        
        # Видаляємо None значення з аналізу
        analysis = {k: v for k, v in analysis.items() if v is not None}

        # Спроба знайти масиви (спрощено)
        signs_match = re.search(r'"manipulation_signs"\s*:\s*\[([^\]]+)\]', json_str)
        if signs_match:
            signs_raw = signs_match.group(1)
            analysis['manipulation_signs'] = [s.strip().strip('"') for s in signs_raw.split(',')]

        if analysis:
            result['analysis'] = analysis

        # Перевірка мінімальної життєздатності
        if 'verdict' in result:
            # Fallbacks
            if 'confidence_score' not in result: result['confidence_score'] = 50
            if 'is_fake' not in result: result['is_fake'] = (result['verdict'] == 'false')
            if 'summary' not in result: 
                if analysis.get('factual_accuracy'):
                    result['summary'] = analysis['factual_accuracy']
                else:
                    result['summary'] = f"Результат аналізу: {result['verdict']}"
            
            return result

        return None

    def _fallback_response(self, raw_text: str) -> Dict[str, Any]:
        """
        Створює структуровану відповідь коли JSON парсинг не вдався.
        Позначається як error щоб НЕ кешуватись.
        """
        return {
            'verdict': 'error',  # Позначаємо як error щоб не кешувалось
            'confidence_score': 0,
            'is_fake': False,
            'summary': 'Не вдалося структурувати відповідь AI',
            'analysis': {
                'raw_response': raw_text[:1000]  # Обмежуємо довжину
            },
            'recommendation': 'Спробуйте ще раз або перевірте вручну',
            'error': True,
            'parse_error': True
        }

    def _error_response(self, error_message: str) -> Dict[str, Any]:
        """
        Створює відповідь при помилці API.
        """
        return {
            'verdict': 'error',
            'confidence_score': 0,
            'is_fake': False,
            'summary': f'Помилка AI: {error_message}',
            'analysis': {},
            'recommendation': 'Спробуйте пізніше',
            'error': True,
            'error_message': error_message
        }


# Глобальний інстанс сервісу (lazy initialization)
_gemini_service: Optional[GeminiAIService] = None


def get_gemini_service() -> GeminiAIService:
    """
    Отримує або створює інстанс GeminiAIService.
    Використовує lazy initialization для уникнення помилок при імпорті.
    """
    global _gemini_service

    # Завжди створюємо новий інстанс для підхоплення змін налаштувань
    _gemini_service = GeminiAIService()

    return _gemini_service

