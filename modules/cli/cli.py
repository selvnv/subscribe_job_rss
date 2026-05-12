import click
import asyncio


from modules.bot.bot import run_bot, send_vacancies_info
from modules.db import init as dbinit, list_rss_subscriptions
from modules.log import log, UserLogPrefix
from modules.utils import print_table_paged


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
        click.echo(UserLogPrefix.ERROR.value + f"Error while initializing database: {e}")


@cli.command(name="runbot")
def start_bot():
    try:
        run_bot()
    except Exception as e:
        log.error(f"Error while starting bot: {e}")
        click.echo(UserLogPrefix.ERROR.value + f"Error while starting bot: {e}")


@cli.command(name="sublist")
def list_subscriptions():
    try:
        log.info("Try to list subscriptions")
        records = list_rss_subscriptions()
        print_table_paged(records, ["record_id", "user_id", "rss_link"])
    except Exception as e:
        log.error(f"Error while list subscriptions: {e}")
        click.echo(UserLogPrefix.ERROR.value + f"Error while listing subscriptions: {e}")


@cli.command(name="bcast")
def bcast_vacancies_info():
    try:
        asyncio.run(send_vacancies_info(context=None))
    except Exception as e:
        log.error(f"Error while fetching all subscriptions: {e}")
        click.echo(UserLogPrefix.ERROR.value + f"Error while fetching all subscriptions: {e}")


