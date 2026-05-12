"""Модуль рендеринга HTML-шаблонов для сообщений Telegram-бота.

Предоставляет функции для загрузки и рендеринга Jinja2-шаблонов:
карточек вакансий и компактного описания параметров RSS-подписки.
"""

from pathlib import Path
from jinja2 import Template

from modules.log import log


def _render_template(template_path: str, **kwargs) -> str:
    """Загрузить и отрендерить Jinja2-шаблон из файла с переданными переменными.

    Возвращает готовую HTML-строку или заглушку, если шаблон не найден
    или произошла ошибка рендеринга.
    """
    path = Path(template_path)

    # Проверить существование файла шаблона
    if not path.exists():
        log.error(f"Template not found: {template_path}")
        return "Nothing to display."

    try:
        # Загрузить содержимое шаблона и отрендерить с переданными параметрами
        with path.open(mode="r", encoding="utf-8") as f:
            template = Template(f.read())
            return template.render(**kwargs)
    except Exception as e:
        log.error(f"Error while rendering template {template_path}: {e}")
        return "Nothing to display."


def render_rss_params_template(template_path: str, params_dict: dict):
    """Отрендерить компактное описание параметров RSS-подписки из шаблона."""
    return _render_template(template_path, **params_dict)


def render_job_card_template(template_path: str, vacancy: dict):
    """Отрендерить HTML-карточку вакансии из шаблона с полным набором данных."""
    return _render_template(template_path, **vacancy)