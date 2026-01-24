import pytest

from news import utils


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("WWW.Example.Com", "example.com"),
        ("example.com", "example.com"),
        (" www.test.org ", "test.org"),
    ],
)
def test_normalize_domain_trims_and_lowercases(raw, expected):
    # Перевірка нормалізації домену до нижнього регістру без префікса www
    assert utils.normalize_domain(raw) == expected


def test_extract_domain_handles_invalid_url():
    # Перевірка повернення порожнього рядка для невалідного URL
    assert utils.extract_domain("not-a-url") == ""


@pytest.mark.parametrize(
    "text,expected",
    [
        ("line1\n\nline2\tline3", "line1 line2 line3"),
        ("", ""),
    ],
)
def test_clean_text_removes_extra_whitespace(text, expected):
    # Перевірка очищення тексту та конденсації пробілів
    assert utils.clean_text(text) == expected


def test_is_valid_url_detects_scheme_and_netloc():
    # Перевірка валідності URL з урахуванням схеми та домену
    assert utils.is_valid_url("https://example.com") is True
    assert utils.is_valid_url("example.com") is False
