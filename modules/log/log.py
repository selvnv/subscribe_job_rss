"""Модуль настройки логирования приложения.

Создаёт каталог для логов, настраивает ротацию лог-файлов
(макс. 10 МБ, 5 резервных копий) и предоставляет объект log
с уровнем INFO для использования во всех модулях проекта.
"""

import logging
from logging.handlers import RotatingFileHandler
from enum import Enum
from pathlib import Path


class UserLogPrefix(Enum):
    """Перечисление цветных префиксов для консольных сообщений пользователю."""
    INFO = "\033[1m\033[94m[INFO] >>>>\033[0m "
    WARNING = "\033[1m\033[93m[WARN] >>>>\033[0m "
    ERROR = "\033[1m\033[91m[ERROR] >>>>\033[0m "


# Создать каталог для лог-файлов, если он ещё не существует
log_path = Path("./logs")
log_path.mkdir(exist_ok=True)


# Настроить базовую конфигурацию логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        # Ротировать лог-файлы: макс. размер 10 МБ, хранить до 5 старых копий
        RotatingFileHandler(
            log_path / "app.log",
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding="utf-8"
        ),
    ]
)


# Получить экземпляр логгера для использования во всех модулях проекта
log = logging.getLogger("subjob")