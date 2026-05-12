"""Модуль парсинга RSS-лент и страниц вакансий с HH.ru.

Предоставляет функции для формирования URL RSS-запроса с фильтрами,
парсинга RSS-ленты в список вакансий, извлечения структурированных данных
со страницы конкретной вакансии и обратного разбора параметров из RSS-URL.
"""

import html
import re

import requests
import xml.etree.ElementTree as etree
from bs4 import BeautifulSoup
from urllib.parse import quote, unquote

from modules.log.log import log
from modules.constants import (
    WORK_FORMAT_MAP, EMPLOYMENT_MAP, EXPERIENCE_MAP, REGION_MAP
)


# Базовый URL для RSS-ленты поиска вакансий на HH.ru
RSS_BASE_URL = "https://hh.ru/search/vacancy/rss"
# Заголовки запроса для эмуляции обращения из обычного браузера во избежание блокировки
REQUEST_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}


def clean_html_text(text):
    """Очистить текст от HTML-сущностей, управляющих последовательностей и лишних пробелов."""

    # Заменить все HTML-сущности (&nbsp; & < и т.д.) на соответствующие символы
    text = html.unescape(text)

    # Заменить последовательности пробельных символов (включая переносы строк) на одиночный пробел
    text = re.sub(r'\s+', ' ', text)

    return text.strip()


def parse_vacancy_salary(soup):
    """Извлечь информацию о зарплате из HTML-страницы вакансии.

    Ищет блок с классом compensation-row и возвращает очищенную строку зарплаты.
    Возвращает None, если блок зарплаты не найден.
    """
    # Найти блок с информацией о зарплате по CSS-классу
    salary_block = soup.find('div', class_=re.compile(r'compensation-row'))

    if not salary_block:
        return None

    # Извлечь и очистить текст зарплаты
    salary_text = clean_html_text(salary_block.text)

    return salary_text


def parse_vacancy(url):
    """Загрузить HTML-страницу вакансии и извлечь из неё структурированные данные.

    Возвращает словарь с полями: title, salary, company, experience, schedule,
    working_hours, work_format, employment, work_place, description, url.
    Возвращает None, если страница не загружена.
    """
    # Загрузить HTML-страницу вакансии по URL
    try:
        log.info(f"Try to request url {url} with headers: {REQUEST_HEADERS}")
        response = requests.get(url, headers=REQUEST_HEADERS, timeout=10)
        if response.status_code != 200:
            return None
    except Exception as error:
        log.error(f" Exception while parse vacancy with url {url}: {error}")
        return None

    # Создать объект BeautifulSoup для парсинга HTML
    soup = BeautifulSoup(response.text, 'html.parser')

    # Извлечь название вакансии
    title = soup.find(attrs={'data-qa': 'vacancy-title'})
    title = title.text.strip() if title else "Не найдено"

    # Извлечь зарплату (первый элемент с data-qa=vacancy-salary)
    salary = parse_vacancy_salary(soup)
    salary = salary if salary else "Не указана"

    # Извлечь название компании
    company = soup.find(attrs={'data-qa': 'vacancy-company-name'})
    company = clean_html_text(company.text) if company else "Не указана"

    # Извлечь требуемый опыт работы
    experience = soup.find(attrs={'data-qa': 'work-experience-text'})
    experience = experience.text.strip() if experience else "Не указан"

    # Извлечь график работы
    schedule = soup.find(attrs={'data-qa': 'work-schedule-by-days-text'})
    schedule = schedule.text.strip() if schedule else "Не указан"

    # Извлечь тип занятости
    employment = soup.find(attrs={'data-qa': 'common-employment-text'})
    employment = employment.text.strip() if employment else "Не указано"

    # Извлечь рабочие часы
    working_hours = soup.find(attrs={'data-qa': 'working-hours-text'})
    working_hours = working_hours.text.strip() if working_hours else "Не указано"

    # Извлечь регион/адрес места работы
    work_place = soup.find(attrs={'data-qa': 'vacancy-view-raw-address'})
    work_place = work_place.text.strip() if work_place else "Не указан"

    # Извлечь формат работы (офис/удалённо/гибрид)
    work_format = soup.find(attrs={'data-qa': 'work-formats-text'})
    work_format = clean_html_text(work_format.text) if work_format else "Не указан"

    # Извлечь описание вакансии с сохранением переносов строк
    description = soup.find(attrs={'data-qa': 'vacancy-description'})
    description = description.get_text(separator="\n", strip=True) if description else ""

    return {
        'title': title,
        'salary': salary,
        'company': company,
        'experience': experience,
        'schedule': schedule,
        'working_hours': working_hours,
        'work_format': work_format,
        'employment': employment,
        'work_place': work_place,
        'description': description,
        'url': url
    }


def parse_rss_feed(rss_url):
    """Загрузить и распарсить RSS-ленту, вернуть список словарей с информацией о вакансиях.

    Каждый элемент списка — словарь с ключами: title, link, published.
    Возвращает пустой список при ошибке загрузки или парсинга XML.
    """
    # Загрузить RSS-ленту по URL
    try:
        response = requests.get(rss_url, headers=REQUEST_HEADERS, timeout=10)
        if response.status_code != 200:
            log.error(f"RSS load error: HTTP {response.status_code} for {rss_url}")
            return []
    except Exception as e:
        log.error(f"RSS load failed for {rss_url}: {e}")
        return []

    # Распарсить XML-содержимое RSS-ленты
    try:
        root = etree.fromstring(response.content)
    except Exception as e:
        log.error(f"XML parse error for {rss_url}: {e}")
        return []

    vacancies = []

    # Итерировать по элементам item — каждый соответствует одной вакансии
    for item in root.findall('.//item'):
        title_elem = item.find('title')
        link_elem = item.find('link')
        pubdate_elem = item.find('pubDate')

        if link_elem is not None and link_elem.text:
            vacancies.append({
                'title': title_elem.text if title_elem is not None else 'Без названия',
                'link': link_elem.text,
                'published': pubdate_elem.text if pubdate_elem is not None else 'Дата публикации неизвестна'
            })

    return vacancies


def create_rss_request_url(
        search_text: str,
        region: str = None,
        work_format: str = None,
        employment_form: str = None,
        required_experience: str = None
        ) -> str:
    """Сформировать URL RSS-запроса к HH.ru с заданными фильтрами.

    Параметры, соответствующие ключам словарей-констант, добавляются
    как query-параметры. Значение search_text обязательно и кодируется через quote.
    """

    request_url = RSS_BASE_URL

    # Добавить обязательный параметр поискового запроса
    search_text = (search_text or "").strip()
    if not search_text:
        raise ValueError("search_text is required and must not be empty")
    request_url += f"?text={quote(search_text)}"

    # Добавить фильтр по региону, если указан
    if region:
        request_url += f"&area={region}"

    # Добавить фильтр по формату работы, если указан и валиден
    if work_format and work_format in WORK_FORMAT_MAP:
        request_url += f"&work_format={work_format}"

    # Добавить фильтр по типу занятости, если указан и валиден
    if employment_form and employment_form in EMPLOYMENT_MAP:
        request_url += f"&employment_form={employment_form}"

    # Добавить фильтр по требуемому опыту, если указан и валиден
    if required_experience and required_experience in EXPERIENCE_MAP:
        request_url += f"&experience={required_experience}"

    return request_url


def parse_rss_url_to_dict(rss_url):
    """Разобрать RSS-URL на составляющие параметры фильтрации.

    Возвращает словарь с ключами: text, area, work_format, employment_form,
    experience, url. Значения параметров преобразуются в читаемый вид
    через соответствующие словари констант, текстовый запрос декодируется.
    """
    # Извлечь строку запроса из URL
    if "?" in rss_url:
        query_string = rss_url.split('?', 1)[1]
        params = query_string.split('&') if query_string else []
    else:
        params = []

    # Инициализировать словарь параметров значениями по умолчанию
    params_dict = {
        'text': None,
        'area': None,
        'work_format': None,
        'employment_form': None,
        'experience': None,
        'url': rss_url
    }

    # Разобрать каждый параметр и преобразовать в читаемый вид
    for param in params:
        param_name, param_value = param.split("=", 1)

        if param_name == "work_format":
            if param_value in WORK_FORMAT_MAP:
                params_dict["work_format"] = WORK_FORMAT_MAP[param_value]
        elif param_name == "employment_form":
            if param_value in EMPLOYMENT_MAP:
                params_dict["employment_form"] = EMPLOYMENT_MAP[param_value]
        elif param_name == "experience":
            if param_value in EXPERIENCE_MAP:
                params_dict["experience"] = EXPERIENCE_MAP[param_value]
        elif param_name == "area":
            if param_value in REGION_MAP:
                params_dict["area"] = REGION_MAP[param_value]
        elif param_name in params_dict:
            params_dict[param_name] = unquote(param_value)

    return params_dict