"""Модуль работы с базой данных SQLite для хранения RSS-подписок и отправленных вакансий.

Предоставляет функции инициализации БД, добавления/удаления/просмотра подписок,
а также учёта уже отправленных вакансий для предотвращения дубликатов.
"""
from .db import (
    init,
    add_rss_subscription,
    delete_rss_subscription,
    list_user_rss_subscriptions,
    list_rss_subscriptions,
    dict_rss_subscriptions,
    is_vacancy_already_sent,
    mark_vacancy_as_sent
)