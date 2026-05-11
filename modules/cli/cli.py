import click
import asyncio
from enum import Enum

from modules.bot.bot import run_bot, send_vacancies_info
from modules.db.db import init as dbinit, list_rss_subscriptions, fetch_all_rss_dict
from modules.log.log import log
from modules.utils.utils import print_table_paged


class UserLogPrefix(Enum):
    INFO = "\033[1m\033[94m[INFO] >>>>\033[0m "
    WARNING = "\033[1m\033[93m[WARN] >>>>\033[0m "
    ERROR = "\033[1m\033[91m[ERROR] >>>>\033[0m "


@click.group()
def cli():
    pass


@cli.command(name="init")
def init():
    try:
        log.info("Try to init database")
        dbinit()
    except Exception as e:
        log.error(f"Error while initializing database: {e}")
        print(UserLogPrefix.ERROR.value + f"Error while initializing database: {e}")


@cli.command(name="runbot")
def start_bot():
    try:
        run_bot()
    except Exception as e:
        log.error(f"Error while starting bot: {e}")


@cli.command(name="sublist")
def list_subscriptions():
    try:
        log.info("Try to list subscriptions")
        records = list_rss_subscriptions()
        print_table_paged(records, ["record_id", "user_id", "rss_link"])
    except Exception as e:
        log.error(f"Error while list subscriptions: {e}")
        print(UserLogPrefix.ERROR.value + f"Error while list subscriptions: {e}")


@cli.command(name="bcast")
def bcast_vacancies_info():
    try:
        asyncio.run(send_vacancies_info())
    except Exception as e:
        log.error(f"Error while fetch all subscriptions: {e}")


