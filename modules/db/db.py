import sqlite3
from pathlib import Path


from modules.log.log import log


DB_PATH = "data/rss_subscriptions.db"


def init():
    try:
        # Создать каталог для базы данных, если не существует
        Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)

        log.debug("Trying to connect to database")
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            log.debug("Connected to database")
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rss_subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    rss_url TEXT NOT NULL
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS rss_subscriptions_user_id
                ON rss_subscriptions (user_id)
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sent_vacancies (
                    user_id TEXT NOT NULL,
                    vacancy_url TEXT NOT NULL,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, vacancy_url)
                )
            """)
    except Exception as e:
        log.error(f"Error while init database: {e}")


def add_rss_subscription(user_id, rss_url) -> bool:
    try:
        log.debug(f"Trying to connect to database")
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            log.debug(f"Connected to database")
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
                return True

            query = """
                INSERT INTO rss_subscriptions (user_id, rss_url)
                VALUES (?, ?)
            """

            log.debug(f"Insert subscription: {user_id} -> {rss_url}")
            cursor.execute(query, (user_id, rss_url))
            return True
    except Exception as e:
        log.error(f"Error while add rss subscription: {e}")
        return False


def delete_rss_subscription(subscription_id):
    try:
        log.debug(f"Trying to connect to database")
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            log.debug(f"Connected to database")
            cursor = conn.cursor()

            query = """
                DELETE FROM rss_subscriptions 
                WHERE id = ?
                RETURNING rss_url
            """

            log.debug(f"Try to delete subscription with query: {query}")
            cursor.execute(query, (subscription_id,))
            row = cursor.fetchone()

            return row[0] if row else None
    except Exception as e:
        log.error(f"Error while delete rss subscription: {e}")
        return None


def list_user_rss_subscriptions(user_id) -> list:
    try:
        log.debug(f"Trying to connect to database")
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            log.debug(f"Connected to database")
            cursor = conn.cursor()

            query = """
                SELECT id, user_id, rss_url FROM rss_subscriptions 
                WHERE user_id = ?
            """

            log.debug(f"Try to get user subscriptions with query: {query}")
            cursor.execute(query, (user_id,))

            return cursor.fetchall()
    except Exception as e:
        log.error(f"Error while list user rss subscriptions: {e}")
        return []


def list_rss_subscriptions() -> list:
    try:
        log.debug(f"Trying to connect to database")
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            log.debug(f"Connected to database")
            cursor = conn.cursor()

            query = """
                SELECT * FROM rss_subscriptions 
            """

            log.debug(f"Try to get user subscriptions with query: {query}")
            cursor.execute(query)

            return cursor.fetchall()
    except Exception as e:
        log.error(f"Error while list rss subscriptions: {e}")
        return []


def dict_rss_subscriptions() -> dict:
    try:
        log.debug(f"Trying to connect to database")
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            log.debug(f"Connected to database")
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
        return {}


def is_vacancy_already_sent(user_id, vacancy_url) -> bool:
    try:
        log.debug(f"Trying to connect to database")
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            log.debug(f"Connected to database")
            cursor = conn.cursor()

            query = """
                SELECT COUNT(*) FROM sent_vacancies 
                WHERE user_id = ? AND vacancy_url = ?
            """

            cursor.execute(
                query,
                (user_id, vacancy_url)
            )

            return cursor.fetchone()[0] > 0
    except Exception as e:
        log.error(f"Error checking sent vacancy: {e}")
        return False


def mark_vacancy_as_sent(user_id, vacancy_url):
    try:
        log.debug(f"Trying to connect to database")
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            log.debug(f"Connected to database")
            cursor = conn.cursor()

            query = """
                INSERT OR IGNORE INTO sent_vacancies (user_id, vacancy_url)
                VALUES (?, ?)
            """

            cursor.execute(
                query,
                (user_id, vacancy_url)
            )
    except Exception as e:
        log.error(f"Error marking vacancy as sent: {e}")