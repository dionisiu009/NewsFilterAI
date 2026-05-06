import os
import json
import re
from pathlib import Path
import pytest

from news.parser_service import (
    TrafilaturaParser, NewspaperParser, ReadabilityParser, 
    GooseParser, BS4Parser
)

FIXTURES_DIR = Path(os.path.dirname(__file__)) / 'fixtures'

def extract_expected_results(md_content):
    results = {}
    pattern = re.compile(r'## (\w+)\n+```json\n(.*?)\n```', re.DOTALL)
    for match in pattern.finditer(md_content):
        parser_name = match.group(1)
        json_str = match.group(2)
        try:
            results[parser_name] = json.loads(json_str)
        except json.JSONDecodeError as e:
            pytest.fail(f"Failed to parse JSON for {parser_name}: {e}")
    return results

def get_fixture_files():
    if not FIXTURES_DIR.exists():
        return []
    return list(FIXTURES_DIR.glob('*.html'))

@pytest.mark.parametrize("html_file", get_fixture_files(), ids=lambda p: p.name)
def test_tc_mod_02_parsers_against_fixtures(html_file):
    """
    TC-MOD-02: Перевірка логіки вилучення тексту п'ятьма незалежними парсерами на еталонних HTML-сторінках.
    """
    with open(html_file, 'r', encoding='utf-8') as f:
        html = f.read()

    md_file = html_file.with_suffix('.md')
    assert md_file.exists(), f"Еталонний markdown файл {md_file.name} не існує."
    
    with open(md_file, 'r', encoding='utf-8') as f:
        md_content = f.read()

    expected_results = extract_expected_results(md_content)

    url = f"http://mock.local/{html_file.name}"

    parsers = [
        TrafilaturaParser(),
        NewspaperParser(),
        ReadabilityParser(),
        GooseParser(),
        BS4Parser()
    ]

    for parser in parsers:
        parser_name = parser.__class__.__name__
        
        assert parser_name in expected_results, f"Немає еталонного результату для {parser_name} у файлі {md_file.name}"
        expected_result = expected_results[parser_name]
        
        try:
            actual_result = parser.parse(html, url)
        except Exception as e:
            actual_result = {"error": str(e)}

        actual_json = json.loads(json.dumps(actual_result, ensure_ascii=False, default=str))
        
        assert actual_json == expected_result, f"Невідповідність результату для парсера {parser_name} на файлі {html_file.name}"
