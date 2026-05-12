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


RSS_BASE_URL ="https://hh.ru/search/vacancy/rss"
# В заголовках запроса указывается User-Agent для
# эмуляции выполнения запроса из обычного браузера во избежание блокировки
REQUEST_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}


def clean_html_text(text):
    """Очищает текст от HTML-сущностей и лишних пробелов"""

    # Или через html модуль (заменяет ВСЕ сущности: &nbsp; &amp; &lt; и т.д.)
    text = html.unescape(text)

    # Убрать лишние пробелы
    text = re.sub(r'\s+', ' ', text)

    return text.strip()


def parse_vacancy_salary(soup):
    salary_block = soup.find('div', class_=re.compile(r'compensation-row'))

    if not salary_block:
        return None

    # Извлекаем текст как есть (без html.unescape)
    salary_text = clean_html_text(salary_block.text)

    return salary_text


# Загружает HTML-страницу вакансии и вытягивает из нее необходимые данные
def parse_vacancy(url):
    # Получить HTML-страницу вакансии
    try:
        log.info(f"Try to request url {url} with headers: {REQUEST_HEADERS}")
        response = requests.get(url, headers=REQUEST_HEADERS, timeout=10)
        if response.status_code != 200:
            return None
    except Exception as error:
        log.error(f" Exception while parse vacancy with url {url}: {error}")
        return None

    # Создать объект BeautifulSoup для парсинга
    soup = BeautifulSoup(response.text, 'html.parser')

    # Название
    title = soup.find(attrs={'data-qa': 'vacancy-title'})
    title = title.text.strip() if title else "Не найдено"

    # Зарплата
    # Поиск первого элемента с атрибутом data-qa=vacancy-salary
    salary = parse_vacancy_salary(soup)
    salary = salary if salary else "Не указана"

    # Компания
    company = soup.find(attrs={'data-qa': 'vacancy-company-name'})
    company = clean_html_text(company.text) if company else "Не указана"

    # Опыт (vacancy-experience или work-experience-text)
    experience = soup.find(attrs={'data-qa': 'work-experience-text'})
    experience = experience.text.strip() if experience else "Не указан"

    # График работы
    schedule = soup.find(attrs={'data-qa': 'work-schedule-by-days-text'})
    schedule = schedule.text.strip() if schedule else "Не указан"

    # Занятость
    employment = soup.find(attrs={'data-qa': 'common-employment-text'})
    employment = employment.text.strip() if employment else "Не указано"

    # Часы работы
    working_hours = soup.find(attrs={'data-qa': 'working-hours-text'})
    working_hours = working_hours.text.strip() if working_hours else "Не указано"

    # Регион (место работы)
    work_place = soup.find(attrs={'data-qa': 'vacancy-view-raw-address'})
    work_place = work_place.text.strip() if work_place else "Не указан"

    # Формат работы
    work_format = soup.find(attrs={'data-qa': 'work-formats-text'})
    work_format = clean_html_text(work_format.text) if work_format else "Не указан"

    # Описание
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
    """Парсит RSS-ленту и возвращает список ссылок на вакансии"""
    try:
        response = requests.get(rss_url, headers=REQUEST_HEADERS, timeout=10)
        if response.status_code != 200:
            log.error(f"RSS load error: HTTP {response.status_code} for {rss_url}")
            return []
    except Exception as e:
        log.error(f"RSS load failed for {rss_url}: {e}")
        return []

    # Парсим XML
    try:
        root = etree.fromstring(response.content)
    except Exception as e:
        log.error(f"XML parse error for {rss_url}: {e}")
        return []

    vacancies = []

    # Каждая вакансия расположена в теге item
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

    request_url = RSS_BASE_URL

    search_text = (search_text or "").strip()
    if not search_text:
        raise ValueError("search_text is required and must not be empty")
    request_url += f"?text={quote(search_text)}"


    if region:
        request_url += f"&area={region}"

    if work_format and work_format in WORK_FORMAT_MAP:
        request_url += f"&work_format={work_format}"

    if employment_form and employment_form in EMPLOYMENT_MAP:
        request_url += f"&employment_form={employment_form}"

    if required_experience and required_experience in EXPERIENCE_MAP:
        request_url += f"&experience={required_experience}"

    return request_url


def parse_rss_url_to_dict(rss_url):
    if "?" in rss_url:
        query_string = rss_url.split('?', 1)[1]
        params = query_string.split('&') if query_string else []
    else:
        params = []

    params_dict = {
        'text': None,
        'area': None,
        'work_format': None,
        'employment_form': None,
        'experience': None,
        'url': rss_url
    }

    for param in params:
        param_name, param_value = param.split("=", 1)

        if param_name == "work_format":
            if param_value  in WORK_FORMAT_MAP:
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

