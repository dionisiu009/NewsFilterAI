# ==============================================================================
# NEWSFILTERAI - ARTICLE PARSER SERVICE
# ==============================================================================
# Сервіс для парсингу новинних статей за допомогою мульти-парсингу (voting system)

import json
import logging
import concurrent.futures
import requests
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
from difflib import SequenceMatcher
from collections import Counter
from datetime import datetime
import re
from dateutil import parser as dateutil_parser

# Third-party parsers
import trafilatura
from newspaper import Article as NewspaperArticle
from readability import Document
from goose3 import Goose
from bs4 import BeautifulSoup

from .utils import extract_domain, clean_text
from .constants import MIN_ARTICLE_LENGTH, PARSER_TIMEOUT

logger = logging.getLogger(__name__)

# Config
USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/120.0.0.0 Safari/537.36'
)


def similar(a: str, b: str) -> float:
    """Повертає коефіцієнт схожості рядків (0.0 - 1.0)"""
    return SequenceMatcher(None, a, b).ratio()

def normalize_whitespace(text: str) -> str:
    if not text:
        return text
    text = re.sub(r'\n{3,}', '\n\n', text)
    lines = [line.rstrip() for line in text.split('\n')]
    return '\n'.join(lines).strip()

class BaseParser(ABC):
    """Абстрактний клас для парсера"""
    
    @abstractmethod
    def parse(self, html: str, url: str) -> Dict[str, Any]:
        """
        Парсить HTML і повертає словник {title, text, date, image, authors}.
        Якщо не вдалося - повертає порожні значення.
        """
        pass

class TrafilaturaParser(BaseParser):
    def parse(self, html: str, url: str) -> Dict[str, Any]:
        try:
            # Trafilatura краще працює, якщо йому дати HTML
            extracted = trafilatura.extract(
                html,
                include_comments=False,
                include_tables=False,
                output_format='json',
                with_metadata=True,
                url=url
            )
            if not extracted:
                return {}
            
            data = json.loads(extracted)
            text = normalize_whitespace(data.get('text'))
            return {
                'title': data.get('title'),
                'text': text,
                'date': data.get('date'),
                'image': data.get('image'),
                'authors': data.get('author', '').split(',') if data.get('author') else [],
                'source': 'trafilatura'
            }
        except Exception as e:
            logger.warning(f"Trafilatura error: {e}")
            return {}

class NewspaperParser(BaseParser):
    def parse(self, html: str, url: str) -> Dict[str, Any]:
        try:
            article = NewspaperArticle(url)
            article.set_html(html)
            article.parse()
            
            return {
                'title': article.title,
                'text': normalize_whitespace(article.text),
                'date': str(article.publish_date) if article.publish_date else None,
                'image': article.top_image,
                'authors': article.authors,
                'source': 'newspaper3k'
            }
        except Exception as e:
            logger.warning(f"Newspaper3k error: {e}")
            return {}

class ReadabilityParser(BaseParser):
    def parse(self, html: str, url: str) -> Dict[str, Any]:
        try:
            doc = Document(html)
            title = doc.title()
            
            # Readability повертає HTML контент, треба його почистити
            summary_html = doc.summary()
            soup = BeautifulSoup(summary_html, 'html.parser')
            text = normalize_whitespace(soup.get_text(separator='\n\n'))
            
            return {
                'title': title,
                'text': text,
                'date': None, # Readability погано витягує дату
                'image': None,
                'authors': [],
                'source': 'readability'
            }
        except Exception as e:
            logger.warning(f"Readability error: {e}")
            return {}

class GooseParser(BaseParser):
    def parse(self, html: str, url: str) -> Dict[str, Any]:
        g = Goose({'enable_image_fetching': True})
        try:
            article = g.extract(raw_html=html)
            return {
                'title': article.title,
                'text': normalize_whitespace(article.cleaned_text),
                'date': article.publish_date,
                'image': article.top_image.src if article.top_image else None,
                'authors': article.authors,
                'source': 'goose3'
            }
        except Exception as e:
            logger.warning(f"Goose3 error: {e}")
            return {}
        finally:
            g.close()

class BS4Parser(BaseParser):
    """Fallback парсер, використовує мета-теги та евристику"""
    def parse(self, html: str, url: str) -> Dict[str, Any]:
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Title
            title = None
            og_title = soup.find('meta', property='og:title')
            if og_title:
                title = og_title.get('content')
            if not title:
                title_tag = soup.find('title')
                if title_tag:
                    title = title_tag.get_text()
            
            # Date
            date = None
            date_meta = soup.find('meta', property='article:published_time')
            if date_meta:
                date = date_meta.get('content')
            
            # Image
            image = None
            og_image = soup.find('meta', property='og:image')
            if og_image:
                image = og_image.get('content')
                
            # Text (Дуже примітивно - беремо всі P)
            # Це слабке місце, але як fallback може спрацювати для простих сторінок
            paragraphs = soup.find_all('p')
            text = normalize_whitespace(
                '\n\n'.join([p.get_text() for p in paragraphs if len(p.get_text().strip()) > 30])
            )
            
            return {
                'title': title,
                'text': text,
                'date': date,
                'image': image,
                'authors': [],
                'source': 'bs4'
            }
        except Exception as e:
            logger.warning(f"BS4 error: {e}")
            return {}

class ArticleParserService:
    """
    Агрегатор парсерів. Запускає декілька парсерів паралельно і обирає найкращий результат.
    """
    
    def __init__(self, timeout: int = PARSER_TIMEOUT):
        self.timeout = timeout
        self.parsers: List[BaseParser] = [
            TrafilaturaParser(),
            NewspaperParser(),
            GooseParser(),
            ReadabilityParser(),
            BS4Parser()
        ]

    def _fetch_html(self, url: str) -> Optional[str]:
        """Завантажує HTML сторінку"""
        try:
            response = requests.get(
                url, 
                headers={'User-Agent': USER_AGENT}, 
                timeout=self.timeout
            )
            response.raise_for_status()
            
            # Detect encoding
            if response.encoding is None:
                response.encoding = response.apparent_encoding
                
            return response.text
        except Exception as e:
            logger.error(f"Error fetching URL {url}: {e}")
            return None

    def parse_url(self, url: str) -> Dict[str, Any]:
        """
        Основний метод.
        1. Завантажує HTML.
        2. Запускає всі парсери паралельно.
        3. Агрегує результати (voting).
        """
        logger.info(f"Starting multi-parser for: {url}")
        
        # 1. Fetch HTML
        html = self._fetch_html(url)
        if not html:
            return self._error_response("Failed to download page")

        # 2. Run parsers in parallel
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_parser = {executor.submit(p.parse, html, url): p for p in self.parsers}
            
            for future in concurrent.futures.as_completed(future_to_parser):
                parser_name = future_to_parser[future].__class__.__name__
                try:
                    data = future.result()
                    if data and data.get('text') and len(data.get('text').strip()) > MIN_ARTICLE_LENGTH:
                        results.append(data)
                        logger.debug(f"Parser {parser_name} succeeded")
                    else:
                        logger.debug(f"Parser {parser_name} returned empty or short content")
                except Exception as exc:
                    logger.error(f"Parser {parser_name} generated an exception: {exc}")

        if not results:
            return self._error_response("No parser could extract content")

        # 3. Aggregate results
        best_result = self._aggregate_results(results, url)
        
        logger.info(
            f"Parsing finished. Winner source: {best_result.get('source', 'unknown')}. "
            f"Title: {best_result['title'][:50]}..."
        )
        
        return best_result

    def _aggregate_results(self, results: List[Dict[str, Any]], url: str) -> Dict[str, Any]:
        """Вибирає найкращі дані серед результатів парсерів"""
        
        # --- TITLE VOTING ---
        titles = [r['title'] for r in results if r.get('title')]
        best_title = self._get_best_text_match(titles) or "No Title"

        # --- TEXT VOTING ---
        # 1. Збираємо всі непусті тексти та їх кількість слів
        texts_info = []  # list of (text, word_count, parser_index)
        for idx, r in enumerate(results):
            t = r.get('text')
            if t and len(t.strip()) > 0:
                wc = len(t.split())
                texts_info.append((t, wc, idx))

        # 2. Якщо є хоча б два парсера з однаковим числом слів - обираємо серед них (йде пріоритет совпадіння кількості)
        best_text = ""
        chosen_text_index = None
        if texts_info:
            # Map word_count -> list of (text, idx)
            wc_map = {}
            for t, wc, idx in texts_info:
                wc_map.setdefault(wc, []).append((t, idx))

            # Look for a word count that appears in at least 2 parsers
            duplicate_wc = None
            for wc, items in wc_map.items():
                if len(items) >= 2:
                    duplicate_wc = wc
                    break

            if duplicate_wc is not None:
                # choose the longest text among parsers that have this word count
                candidates = wc_map[duplicate_wc]
                best_text, chosen_text_index = max(candidates, key=lambda it: len(it[0]))
                logger.info(f"Chosen text by duplicate word count={duplicate_wc} (count {len(candidates)} parsers)")
            else:
                # No duplicate counts -> choose parser with max word count
                best_text, best_wc, chosen_text_index = max(texts_info, key=lambda it: it[1])
                logger.info(f"Chosen text by max word count={best_wc}")
        else:
            best_text = ""

        # --- DATE VOTING ---
        # Normalize dates to YYYY-MM-DD (if possible) for comparison
        def normalize_date(d: Any) -> Optional[str]:
            if not d:
                return None
            if isinstance(d, datetime):
                return d.date().isoformat()
            try:
                # Use dateutil for robust parsing of many date formats
                if isinstance(d, str):
                    dt = dateutil_parser.parse(d, dayfirst=False)
                    return dt.date().isoformat()
                return None
            except Exception:
                return None

        normalized_dates = []  # list of (normalized_date, parser_index, raw)
        for idx, r in enumerate(results):
            d = r.get('date')
            nd = normalize_date(d)
            if nd:
                normalized_dates.append((nd, idx, d))

        best_date = None
        if normalized_dates:
            # Count occurrences of normalized date
            nd_counts = Counter([nd for nd, _, _ in normalized_dates])
            # Find any date that appears in at least 2 parsers
            common_nd = None
            for nd, cnt in nd_counts.items():
                if cnt >= 2:
                    common_nd = nd
                    break
            if common_nd:
                best_date = common_nd
                logger.info(f"Chosen publish_date by consensus: {best_date}")
            else:
                # Fallback: take first normalized date
                best_date = normalized_dates[0][0]

        # --- AUTHORS VOTING ---
        # Count individual author occurrences across parsers
        author_counter = Counter()
        parser_authors = []  # store list per parser
        for idx, r in enumerate(results):
            a_list = r.get('authors') or []
            parser_authors.append(a_list)
            for a in a_list:
                if a and len(a.strip()) > 0:
                    author_counter[a.strip()] += 1

        best_authors = []
        if author_counter:
            # prefer authors that appear in at least 2 parsers
            common_authors = [a for a, c in author_counter.items() if c >= 2]
            if common_authors:
                best_authors = common_authors
                logger.info(f"Chosen authors by consensus: {best_authors}")
            else:
                # fallback: take authors from parser with longest text (chosen_text_index)
                if chosen_text_index is not None and parser_authors[chosen_text_index]:
                    best_authors = parser_authors[chosen_text_index]
                else:
                    # last resort: union of all authors
                    best_authors = list({a for lst in parser_authors for a in lst if a})

        # --- Mark winners in parsers_debug ---
        for idx, r in enumerate(results):
            # set default flags
            r['is_winner_title'] = False
            r['is_winner_text'] = False
            r['is_winner_date'] = False
            r['is_winner_authors'] = False

            # title winner if fuzzy similar to best_title
            if r.get('title') and best_title and similar(str(r.get('title')).lower(), str(best_title).lower()) > 0.8:
                r['is_winner_title'] = True

            # text winner if exact word count match to chosen_text or very similar
            t = r.get('text')
            if t and best_text:
                try:
                    if len(t.split()) == len(best_text.split()):
                        r['is_winner_text'] = True
                    elif similar(t[:1000], best_text[:1000]) > 0.9:
                        r['is_winner_text'] = True
                except Exception:
                    pass

            # date winner if normalized date equals best_date
            nd = normalize_date(r.get('date'))
            if nd and best_date and nd == best_date:
                r['is_winner_date'] = True

            # authors winner if overlap with best_authors
            a_list = r.get('authors') or []
            if best_authors:
                overlap = len(set([a.strip() for a in a_list if a]) & set([a.strip() for a in best_authors]))
                if overlap > 0:
                    r['is_winner_authors'] = True

        word_count = len(best_text.split()) if best_text else 0

        return {
            'success': True,
            'title': clean_text(best_title),
            'text': clean_text(best_text),
            'authors': best_authors,
            'publish_date': best_date,
            'domain': extract_domain(url),
            'word_count': word_count,
            'error': None,
            'source': results[chosen_text_index].get('source') if chosen_text_index is not None else 'hybrid',
            'debug_parsers_count': len(results),
            'parsers_debug': results  # Повернути індивідуальні результати парсера для інтерфейсу налагодження
        }

    def _get_best_text_match(self, candidates: List[str]) -> Optional[str]:
        """Знаходить рядок, який найчастіше зустрічається (з урахуванням fuzzy match)"""
        if not candidates:
            return None
        
        # Групуємо схожі рядки
        groups = []
        visited = set()
        
        for i, s1 in enumerate(candidates):
            if i in visited:
                continue
            
            group = [s1]
            visited.add(i)
            
            for j, s2 in enumerate(candidates):
                if i != j and j not in visited:
                    if similar(s1.lower(), s2.lower()) > 0.8: # 80% схожості
                        group.append(s2)
                        visited.add(j)
            groups.append(group)
        
        # Обираємо найбільшу групу
        if not groups:
            return None
            
        largest_group = max(groups, key=len)
        # Повертаємо найдовший рядок з найбільшої групи (він зазвичай найбільш повний)
        return max(largest_group, key=len)

    def _get_best_content_match(self, candidates: List[str]) -> Optional[str]:
        """
        Аналогічно для тексту, але поріг схожості менший, бо тексти довгі.
        """
        if not candidates:
            return None
            
        groups = []
        visited = set()
        
        for i, t1 in enumerate(candidates):
            if i in visited:
                continue
            
            group = [t1]
            visited.add(i)
            
            for j, t2 in enumerate(candidates):
                if i != j and j not in visited:
                    # Для довгих текстів перевіряємо чи вони приблизно однієї довжини + схожість
                    len_ratio = min(len(t1), len(t2)) / max(len(t1), len(t2))
                    if len_ratio > 0.7 and similar(t1[:1000], t2[:1000]) > 0.6:
                         group.append(t2)
                         visited.add(j)
            groups.append(group)
            
        if not groups:
            return None
            
        largest_group = max(groups, key=len)
        return max(largest_group, key=len)

    def _get_most_common(self, items: List[Any]) -> Optional[Any]:
        """Повертає найчастіший елемент (ігнорує пусті значення)"""
        # Фільтруємо None та пусті рядки
        valid_items = [i for i in items if i]
        
        if not valid_items:
            return None
            
        c = Counter(valid_items)
        return c.most_common(1)[0][0]

    def _error_response(self, error_message: str) -> Dict[str, Any]:
        return {
            'success': False,
            'title': '',
            'text': '',
            'authors': [],
            'publish_date': None,
            'domain': '',
            'word_count': 0,
            'error': error_message
        }

# Global instance
article_parser = ArticleParserService()

