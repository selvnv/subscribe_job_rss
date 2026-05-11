import sqlite3
from pathlib import Path


from modules.log.log import log


DB_PATH = "data/rss_subscriptions.db"


def init():
    try:
        # Создать каталог для базы данных, если не существует
        Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)

        log.info("Try to connect to database")
        with sqlite3.connect(DB_PATH) as conn:
            log.info("Connected to database")
            cursor = conn.cursor()

            query = """
                CREATE TABLE IF NOT EXISTS rss_subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    rss_url TEXT NOT NULL
                )
            """

            log.info(f"Try to create table with query: {query}")

            cursor.execute(query)
    except Exception as e:
        log.error(f"Error while init database: {e}")


def add_rss_subscription(user_id, rss_url):
    try:
        log.info(f"Try to connect to database")
        with sqlite3.connect(DB_PATH) as conn:
            log.info(f"Connected to database")
            cursor = conn.cursor()

            # Проверка наличия такой подписки у пользователя
            check_query = """
                SELECT COUNT(*) FROM rss_subscriptions 
                WHERE user_id = ? AND rss_url = ?
            """
            cursor.execute(check_query, (user_id, rss_url))
            count = cursor.fetchone()[0]

            # Если подписка уже существует, не добавлять повторно
            if count > 0:
                return

            query = """
                INSERT INTO rss_subscriptions (user_id, rss_url)
                VALUES (?, ?)
            """

            log.info(f"Try to create table with query: {query}")
            cursor.execute(query, (user_id, rss_url))
    except Exception as e:
        log.error(f"Error while add rss subscription: {e}")


def delete_rss_subscription(subscription_id):
    try:
        log.info(f"Try to connect to database")
        with sqlite3.connect(DB_PATH) as conn:
            log.info(f"Connected to database")
            cursor = conn.cursor()

            query = """
                DELETE FROM rss_subscriptions 
                WHERE id = ?
                RETURNING rss_url
            """

            log.info(f"Try to delete subscription with query: {query}")
            cursor.execute(query, (subscription_id,))
            row = cursor.fetchone()

            return row[0] if row else None
    except Exception as e:
        log.error(f"Error while delete rss subscription: {e}")


def list_user_rss_subscriptions(user_id):
    try:
        log.info(f"Try to connect to database")
        with sqlite3.connect(DB_PATH) as conn:
            log.info(f"Connected to database")
            cursor = conn.cursor()

            query = """
                SELECT id, user_id, rss_url FROM rss_subscriptions 
                WHERE user_id = ?
            """

            log.info(f"Try to get user subscriptions with query: {query}")
            cursor.execute(query, (user_id,))

            return cursor.fetchall()
    except Exception as e:
        log.error(f"Error while list user rss subscriptions: {e}")


def list_rss_subscriptions():
    try:
        log.info(f"Try to connect to database")
        with sqlite3.connect(DB_PATH) as conn:
            log.info(f"Connected to database")
            cursor = conn.cursor()

            query = """
                SELECT * FROM rss_subscriptions 
            """

            log.info(f"Try to get user subscriptions with query: {query}")
            cursor.execute(query)

            return cursor.fetchall()
    except Exception as e:
        log.error(f"Error while list rss subscriptions: {e}")


def fetch_all_rss_dict():
    try:
        log.info(f"Try to connect to database")
        with sqlite3.connect(DB_PATH) as conn:
            log.info(f"Connected to database")
            cursor = conn.cursor()

            query = """
                SELECT user_id, rss_url, id
                FROM rss_subscriptions
                ORDER BY user_id, id
            """

            cursor.execute(query)

            user_subscriptions = {}
            for user_id, rss_url, sub_id in cursor.fetchall():
                if user_id not in user_subscriptions:
                    user_subscriptions[user_id] = []
                user_subscriptions[user_id].append({
                    'id': sub_id,
                    'url': rss_url
                })

            return user_subscriptions
    except Exception as e:
        log.error(f"Error while fetch rss subscriptions: {e}")
