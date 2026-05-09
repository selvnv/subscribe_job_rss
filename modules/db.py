import sqlite3

from modules.log import log


def init():
    try:
        log.info("Try to connect to database")
        with sqlite3.connect("db/rss_subscriptions.db") as conn:
            log.info("Connected to database")
            cursor = conn.cursor()

            query = """
                CREATE TABLE IF NOT EXISTS rss_subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    rss_url TEXT NOT NULL
                )
            """

            log.info(f"Try to create table with query: {query}")

            cursor.execute(query)
    except Exception as e:
        log.error(f"Error while init database: {e}")


def add_rss_subscription(username, rss_url):
    try:
        log.info(f"Try to connect to database")
        with sqlite3.connect("db/rss_subscriptions.db") as conn:
            log.info(f"Connected to database")
            cursor = conn.cursor()

            query = f"""
                INSERT INTO rss_subscriptions (username, rss_url)
                VALUES (?, ?)
            """

            log.info(f"Try to create table with query: {query}")
            cursor.execute(query, (username, rss_url))
    except Exception as e:
        log.error(f"Error while add rss subscription: {e}")


def delete_rss_subscription(subscription_id):
    try:
        log.info(f"Try to connect to database")
        with sqlite3.connect("db/rss_subscriptions.db") as conn:
            log.info(f"Connected to database")
            cursor = conn.cursor()

            query = f"""
                DELETE FROM rss_subscriptions 
                WHERE subscription_id = ?
                RETURNING rss_url
            """

            log.info(f"Try to delete subscription with query: {query}")
            cursor.execute(query, (subscription_id,))

            return cursor.fetchone()[0]
    except Exception as e:
        log.error(f"Error while delete rss subscription: {e}")


def list_user_rss_subscriptions(username):
    try:
        log.info(f"Try to connect to database")
        with sqlite3.connect("db/rss_subscriptions.db") as conn:
            log.info(f"Connected to database")
            cursor = conn.cursor()

            query = f"""
                SELECT id, username, rss_url FROM rss_subscriptions 
                WHERE username = ?
            """

            log.info(f"Try to get user subscriptions with query: {query}")
            cursor.execute(query, (username,))

            return cursor.fetchall()
    except Exception as e:
        log.error(f"Error while list user rss subscriptions: {e}")