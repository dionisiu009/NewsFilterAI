# ==============================================================================
# NEWSFILTERAI - REDIS SERVICES
# ==============================================================================
# Сервіси для роботи з Redis: кешування та списки доменів

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from django.conf import settings
from django.core.cache import cache
from django_redis import get_redis_connection

from .utils import normalize_domain, extract_domain, generate_url_hash

logger = logging.getLogger(__name__)


class DomainListService:
    """
    Сервіс для управління білим та чорним списком доменів у Redis.

    Використовує Redis Sets для швидкого пошуку O(1).

    Структура в Redis:
    - domains:whitelist -> SET of domains (достовірні джерела)
    - domains:blacklist -> SET of domains (сумнівні джерела)
    """

    def __init__(self):
        self.redis = get_redis_connection("default")
        self.whitelist_key = settings.REDIS_WHITELIST_KEY
        self.blacklist_key = settings.REDIS_BLACKLIST_KEY

    # =========================================================================
    # БІЛИЙ СПИСОК (Whitelist) - Достовірні джерела
    # =========================================================================

    def add_to_whitelist(self, domain: str) -> bool:
        """
        Додає домен до білого списку.
        Автоматично видаляє з чорного списку якщо він там був.

        Args:
            domain: Домен (наприклад: 'bbc.com')

        Returns:
            True якщо домен було додано, False якщо вже існував
        """
        domain = normalize_domain(domain)

        # Видаляємо з чорного списку якщо він там є
        self.redis.srem(self.blacklist_key, domain)

        # Додаємо до білого списку
        result = self.redis.sadd(self.whitelist_key, domain)

        logger.info(f"Домен '{domain}' додано до білого списку")
        return result > 0

    def remove_from_whitelist(self, domain: str) -> bool:
        """Видаляє домен з білого списку"""
        domain = normalize_domain(domain)
        result = self.redis.srem(self.whitelist_key, domain)

        if result > 0:
            logger.info(f"Домен '{domain}' видалено з білого списку")
        return result > 0

    def is_whitelisted(self, domain: str) -> bool:
        """Перевіряє чи домен у білому списку"""
        domain = normalize_domain(domain)
        return self.redis.sismember(self.whitelist_key, domain)

    def get_whitelist(self) -> List[str]:
        """Повертає всі домени з білого списку"""
        domains = self.redis.smembers(self.whitelist_key)
        return sorted([d.decode('utf-8') if isinstance(d, bytes) else d for d in domains])

    # =========================================================================
    # ЧОРНИЙ СПИСОК (Blacklist) - Сумнівні джерела
    # =========================================================================

    def add_to_blacklist(self, domain: str) -> bool:
        """
        Додає домен до чорного списку.
        Автоматично видаляє з білого списку якщо він там був.

        Args:
            domain: Домен (наприклад: 'fake-news.com')

        Returns:
            True якщо домен було додано, False якщо вже існував
        """
        domain = normalize_domain(domain)

        # Видаляємо з білого списку якщо він там є
        self.redis.srem(self.whitelist_key, domain)

        # Додаємо до чорного списку
        result = self.redis.sadd(self.blacklist_key, domain)

        logger.info(f"Домен '{domain}' додано до чорного списку")
        return result > 0

    def remove_from_blacklist(self, domain: str) -> bool:
        """Видаляє домен з чорного списку"""
        domain = normalize_domain(domain)
        result = self.redis.srem(self.blacklist_key, domain)

        if result > 0:
            logger.info(f"Домен '{domain}' видалено з чорного списку")
        return result > 0

    def is_blacklisted(self, domain: str) -> bool:
        """Перевіряє чи домен у чорному списку"""
        domain = normalize_domain(domain)
        return self.redis.sismember(self.blacklist_key, domain)

    def get_blacklist(self) -> List[str]:
        """Повертає всі домени з чорного списку"""
        domains = self.redis.smembers(self.blacklist_key)
        return sorted([d.decode('utf-8') if isinstance(d, bytes) else d for d in domains])

    # =========================================================================
    # ЗАГАЛЬНІ МЕТОДИ
    # =========================================================================

    def check_domain(self, domain: str) -> Dict[str, Any]:
        """
        Перевіряє репутацію домену.

        Returns:
            {
                'domain': 'example.com',
                'in_whitelist': True/False,
                'in_blacklist': True/False,
                'reputation': 'trusted' | 'suspicious' | 'unknown'
            }
        """
        domain = normalize_domain(domain)

        in_whitelist = self.is_whitelisted(domain)
        in_blacklist = self.is_blacklisted(domain)

        if in_whitelist:
            reputation = 'trusted'
        elif in_blacklist:
            reputation = 'suspicious'
        else:
            reputation = 'unknown'

        return {
            'domain': domain,
            'in_whitelist': in_whitelist,
            'in_blacklist': in_blacklist,
            'reputation': reputation
        }

    def check_url(self, url: str) -> Dict[str, Any]:
        """
        Витягує домен з URL та перевіряє його репутацію.

        Args:
            url: Повний URL (наприклад: 'https://bbc.com/news/article')

        Returns:
            Результат check_domain()
        """
        domain = extract_domain(url)
        return self.check_domain(domain)

    def get_stats(self) -> Dict[str, int]:
        """Повертає статистику списків"""
        return {
            'whitelist_count': self.redis.scard(self.whitelist_key),
            'blacklist_count': self.redis.scard(self.blacklist_key)
        }

    def seed_default_lists(self) -> Dict[str, int]:
        """
        Заповнює списки початковими даними.
        Викликається при першому запуску.
        """
        # Білий список - відомі достовірні джерела
        whitelist_domains = [
            # =====================================================
            # МІЖНАРОДНІ АГЕНТСТВА ТА МЕДІА
            # =====================================================
            'bbc.com',
            'reuters.com',
            'apnews.com',
            'theguardian.com',
            'nytimes.com',
            'washingtonpost.com',
            'dw.com',
            'france24.com',
            'aljazeera.com',
            'cnn.com',
            'euronews.com',
            'politico.eu',
            'ft.com',
            'economist.com',
            'afp.com',

            # =====================================================
            # УКРАЇНСЬКІ ІНФОРМАЦІЙНІ АГЕНТСТВА
            # =====================================================
            'ukrinform.ua',           # Національне інформагентство
            'unian.ua',               # УНІАН
            'interfax.com.ua',        # Інтерфакс-Україна
            'ukranews.com',           # Українські новини

            # =====================================================
            # УКРАЇНСЬКІ ІНТЕРНЕТ-ВИДАННЯ
            # =====================================================
            'pravda.com.ua',          # Українська правда
            'epravda.com.ua',         # Економічна правда
            'eurointegration.com.ua', # Європейська правда
            'liga.net',               # ЛІГА.net
            'nv.ua',                  # Новий час / NV
            'hromadske.ua',           # Громадське
            'zn.ua',                  # Дзеркало тижня
            'lb.ua',                  # Лівий берег
            'focus.ua',               # Фокус
            'apostrophe.ua',          # Апостроф
            'censor.net',             # Цензор.нет
            'obozrevatel.com',        # Обозреватель
            'segodnya.ua',            # Сьогодні
            'gazeta.ua',              # Газета.ua
            'day.kyiv.ua',            # День
            'tyzhden.ua',             # Тиждень
            'detector.media',         # Детектор медіа
            'texty.org.ua',           # Тексти.org.ua
            'journalists.media',      # Медіа журналісти
            'babel.ua',               # Бабель
            'thevillage.com.ua',      # The Village Україна
            'bird.in.ua',             # Bird in Flight
            'platfor.ma',             # Platfor.ma
            'reporters.media',        # Репортери

            # =====================================================
            # СУСПІЛЬНЕ МОВЛЕННЯ ТА РАДІО
            # =====================================================
            'suspilne.media',         # Суспільне мовлення
            'radiosvoboda.org',       # Радіо Свобода
            'bbc.com/ukrainian',      # BBC Україна
            'dw.com/uk',              # Deutsche Welle Україна
            'npu.gov.ua',             # Національне радіо
            'uacrisis.org',           # Український кризовий медіа-центр

            # =====================================================
            # РЕГІОНАЛЬНІ УКРАЇНСЬКІ ЗМІ
            # =====================================================
            'city.kharkov.ua',        # Харків
            'dozorro.org',            # Дозорро (антикорупція)
            'nashkiev.ua',            # Наш Київ
            'odessa-life.od.ua',      # Одеса
            'zaxid.net',              # Західна Україна
            'vn.ua',                  # Вінниця
            'ye.ua',                  # Житомир
            'volyn.com.ua',           # Волинь
            'galinfo.com.ua',         # Галичина
            'poltava.to',             # Полтава
            'cheline.com.ua',         # Черкаси
            '04563.com.ua',           # Бориспіль
            'mukachevo.net',          # Мукачево
            'rivne1.tv',              # Рівне

            # =====================================================
            # ОФІЦІЙНІ ДЕРЖАВНІ ДЖЕРЕЛА УКРАЇНИ
            # =====================================================
            'president.gov.ua',       # Офіс Президента
            'kmu.gov.ua',             # Кабінет Міністрів
            'rada.gov.ua',            # Верховна Рада
            'mfa.gov.ua',             # МЗС України
            'moz.gov.ua',             # МОЗ України
            'mvs.gov.ua',             # МВС України
            'mon.gov.ua',             # МОН України
            'minre.gov.ua',           # Міненерго
            'me.gov.ua',              # Мінекономіки
            'minfin.gov.ua',          # Мінфін
            'mil.gov.ua',             # Міноборони
            'bank.gov.ua',            # НБУ
            'ssu.gov.ua',             # СБУ
            'gp.gov.ua',              # Офіс Генпрокурора
            'nabu.gov.ua',            # НАБУ
            'nazk.gov.ua',            # НАЗК
            'cvu.org.ua',             # ЦВК
            'nrada.gov.ua',           # Нацрада з ТБ
            'nkrzi.gov.ua',           # НКРЗІ
            'amc.gov.ua',             # АМКУ
            'kse.ua',                 # Київська школа економіки
            'niss.gov.ua',            # Націнститут стратегічних досліджень

            # =====================================================
            # АНАЛІТИЧНІ ЦЕНТРИ ТА ФАКТЧЕКЕРИ
            # =====================================================
            'voxukraine.org',         # VoxUkraine
            'stopfake.org',           # StopFake
            'factcheck.org',          # FactCheck
            'snopes.com',             # Snopes
            'mythdetector.ge',        # MythDetector
            'euvsdisinfo.eu',         # EU vs Disinfo
            'icps.com.ua',            # МЦПД
            'razumkov.org.ua',        # Центр Разумкова
            'ucmc.org.ua',            # УКМЦ
        ]

        # Чорний список - відомі джерела дезінформації та пропаганди
        blacklist_domains = [
            # =====================================================
            # РОСІЙСЬКІ ПРОПАГАНДИСТСЬКІ ЗМІ
            # =====================================================
            'rt.com',                 # Russia Today
            'sputniknews.com',        # Sputnik
            'ria.ru',                 # РИА Новости
            'tass.ru',                # ТАСС
            'tass.com',               # ТАСС (англ.)
            'rbc.ru',                 # РБК
            'gazeta.ru',              # Газета.ру
            'lenta.ru',               # Лента.ру
            'iz.ru',                  # Известия
            'kp.ru',                  # Комсомольська правда
            'aif.ru',                 # АиФ
            'mk.ru',                  # Московський комсомолець
            'vesti.ru',               # Вести
            'russian.rt.com',         # RT Russian
            'rusvesna.su',            # Російська весна
            'pravda.ru',              # Правда.ру (не плутати з pravda.com.ua!)
            'tsargrad.tv',            # Царьград
            'ura.news',               # URA.ru
            'regnum.ru',              # REGNUM
            'newizv.ru',              # Новые известия
            'life.ru',                # Life.ru
            '360tv.ru',               # 360
            'russian7.ru',            # Російська сімка
            'politnavigator.net',     # Политнавигатор
            'riafan.ru',              # ФАН
            'ukraina.ru',             # Украина.ру
            'news-front.info',        # News Front
            'southfront.org',         # South Front
            'anna-news.info',         # ANNA News

            # =====================================================
            # ПРОРОСІЙСЬКІ РЕСУРСИ ПСЕВДОРЕСПУБЛІК
            # =====================================================
            'dnr-news.com',
            'lug-info.com',
            'dan-news.info',
            'novorosinform.org',
            'novorossia.su',

            # =====================================================
            # ВІДОМІ САЙТИ ДЕЗІНФОРМАЦІЇ
            # =====================================================
            'infowars.com',           # InfoWars
            'globalresearch.ca',      # Global Research
            'zerohedge.com',          # ZeroHedge
            'naturalnews.com',        # Natural News
            'beforeitsnews.com',      # Before It's News
            'thegatewaypundit.com',   # Gateway Pundit
            'breitbart.com',          # Breitbart

            # =====================================================
            # ЗАБЛОКОВАНІ В УКРАЇНІ РЕСУРСИ
            # =====================================================
            'strana.ua',              # Страна.ua (заблокований)
            'timer-odessa.net',       # Таймер
            'vesti-ukr.com',          # Вести
            'from-ua.com',            # From-ua
            'antifashist.com',        # Антифашист
            'rubaltic.ru',            # RuBaltic
            '112ua.tv',               # 112 (заблокований)
            'newsone.ua',             # NewsOne (заблокований)
            'zik.ua',                 # ZIK (заблокований)
        ]

        added_white = 0
        added_black = 0

        for domain in whitelist_domains:
            if self.add_to_whitelist(domain):
                added_white += 1

        for domain in blacklist_domains:
            if self.add_to_blacklist(domain):
                added_black += 1

        logger.info(f"Seed завершено: {added_white} доменів до whitelist, {added_black} до blacklist")

        return {
            'whitelist_added': added_white,
            'blacklist_added': added_black
        }



class NewsCacheService:
    """
    Сервіс для кешування результатів перевірки новин у Redis.

    Можливості:
    - Кешування успішних результатів
    - Автоматичне видалення після TTL
    - НЕ кешує помилки (дозволяє повторну перевірку)

    Структура ключів:
    - news:check:<url_hash> -> JSON з результатом перевірки
    """

    def __init__(self):
        self.prefix = settings.REDIS_NEWS_CACHE_PREFIX
        self.default_ttl = settings.NEWS_CACHE_TTL  # 6 годин за замовчуванням

    def _get_cache_key(self, url: str) -> str:
        """Генерує унікальний ключ кешу для URL"""
        url_hash = generate_url_hash(url)
        return f"{self.prefix}{url_hash}"

    def get(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Отримує результат перевірки з кешу.

        Args:
            url: URL новини

        Returns:
            Словник з результатом або None якщо кеш відсутній/невалідний
        """
        cache_key = self._get_cache_key(url)
        cached_data = cache.get(cache_key)

        if cached_data:
            # Валідуємо структуру кешу
            if self._is_valid_cached_result(cached_data):
                logger.debug(f"Cache HIT для {url[:50]}...")
                return cached_data
            else:
                logger.warning(f"Невалідний кеш для {url[:50]}, видаляємо...")
                cache.delete(cache_key)

        logger.debug(f"Cache MISS для {url[:50]}...")
        return None

    def _is_valid_cached_result(self, data: Dict[str, Any]) -> bool:
        """Перевіряє чи кешований результат валідний"""
        required_fields = ['verdict', 'url']
        return all(field in data for field in required_fields)

    def set(self, url: str, result: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """
        Зберігає результат перевірки в кеш.
        НЕ зберігає помилки.

        Args:
            url: URL новини
            result: Результат перевірки для кешування
            ttl: Час життя в секундах (за замовчуванням з settings)

        Returns:
            True якщо успішно збережено, False якщо це помилка
        """
        # НЕ кешуємо помилки
        if result.get('verdict') == 'error' or result.get('_is_error'):
            logger.debug(f"Результат з помилкою НЕ кешується: {url[:50]}...")
            return False

        cache_key = self._get_cache_key(url)
        ttl = ttl or self.default_ttl

        # Копіюємо результат та видаляємо внутрішні прапорці
        result_to_cache = result.copy()
        result_to_cache.pop('_is_error', None)
        result_to_cache['cached'] = True
        result_to_cache['cached_at'] = datetime.now().isoformat()

        cache.set(cache_key, result_to_cache, ttl)
        logger.info(f"Результат закешовано: {url[:50]}... (TTL: {ttl}s)")
        return True

    def delete(self, url: str) -> bool:
        """Видаляє результат з кешу"""
        cache_key = self._get_cache_key(url)
        cache.delete(cache_key)
        logger.info(f"Кеш видалено для {url[:50]}...")
        return True

    def exists(self, url: str) -> bool:
        """Перевіряє чи існує кеш для URL"""
        cache_key = self._get_cache_key(url)
        return cache.get(cache_key) is not None

    def get_stats(self) -> Dict[str, Any]:
        """Повертає статистику кешу (якщо доступно)"""
        try:
            from django_redis import get_redis_connection
            redis_conn = get_redis_connection("default")
            info = redis_conn.info('memory')
            return {
                'used_memory': info.get('used_memory_human', 'N/A'),
                'connected': True
            }
        except Exception as e:
            logger.warning(f"Не вдалося отримати статистику кешу: {e}")
            return {'connected': False, 'error': str(e)}


# Глобальні інстанси сервісів (Singleton pattern)
domain_list_service = DomainListService()
news_cache_service = NewsCacheService()

