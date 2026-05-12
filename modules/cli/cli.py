"""Модуль интерфейса командной строки для управления подписками на RSS-рассылку.

Предоставляет команды click: init — инициализация БД, runbot — запуск бота,
sublist — просмотр подписок, bcast — ручная широковещательная рассылка вакансий.
"""

import click
import asyncio


from modules.bot.bot import run_bot, send_vacancies_info
from modules.db import init as dbinit, list_rss_subscriptions
from modules.log import log, UserLogPrefix
from modules.utils import print_table_paged


@click.group()
def cli():
    """Группа команд CLI для управления подписками на RSS-рассылку вакансий."""
    pass


@cli.command(name="init")
def init():
    """Выполнить инициализацию базы данных: создать таблицы и индексы."""
    try:
        log.info("Try to init database")
        # Инициализировать структуру базы данных
        dbinit()
    except Exception as e:
        log.error(f"Error while initializing database: {e}")
        click.echo(UserLogPrefix.ERROR.value + f"Error while initializing database: {e}")


@cli.command(name="runbot")
def start_bot():
    """Запустить Telegram-бота в режиме длительного опроса обновлений."""
    try:
        # Запустить основной цикл бота
        run_bot()
    except Exception as e:
        log.error(f"Error while starting bot: {e}")
        click.echo(UserLogPrefix.ERROR.value + f"Error while starting bot: {e}")


@cli.command(name="sublist")
def list_subscriptions():
    """Отобразить список всех RSS-подписок в постраничной таблице."""
    try:
        log.info("Try to list subscriptions")
        # Получить все записи подписок из базы данных
        records = list_rss_subscriptions()
        # Вывести записи в постраничной таблице
        print_table_paged(records, ["record_id", "user_id", "rss_link"])
    except Exception as e:
        log.error(f"Error while list subscriptions: {e}")
        click.echo(UserLogPrefix.ERROR.value + f"Error while listing subscriptions: {e}")


@cli.command(name="bcast")
def bcast_vacancies_info():
    """Выполнить ручную широковещательную рассылку вакансий всем подписчикам."""
    try:
        # Запустить асинхронную задачу рассылки вакансий
        asyncio.run(send_vacancies_info(context=None))
    except Exception as e:
        log.error(f"Error while fetching all subscriptions: {e}")
        click.echo(UserLogPrefix.ERROR.value + f"Error while fetching all subscriptions: {e}")