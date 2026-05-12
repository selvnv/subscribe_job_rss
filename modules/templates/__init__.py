"""Модуль шаблонизации для рендеринга HTML-сообщений бота.

Предоставляет функции для рендеринга карточек вакансий и
компактного описания параметров RSS-подписки через Jinja2.
"""
from .templates import (
    render_rss_params_template, render_job_card_template
)