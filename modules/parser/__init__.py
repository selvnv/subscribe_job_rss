"""Модуль парсинга RSS-лент и страниц вакансий с HH.ru.

Предоставляет функции для формирования URL RSS-запроса,
парсинга RSS-ленты, извлечения данных со страницы вакансии
и обратного разбора параметров из URL.
"""
from .parser import (
    create_rss_request_url,
    parse_rss_url_to_dict,
    parse_rss_feed,
    parse_vacancy
)