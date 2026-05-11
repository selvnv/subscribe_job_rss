import logging
from enum import Enum
from pathlib import Path


class UserLogPrefix(Enum):
    INFO = "\033[1m\033[94m[INFO] >>>>\033[0m "
    WARNING = "\033[1m\033[93m[WARN] >>>>\033[0m "
    ERROR = "\033[1m\033[91m[ERROR] >>>>\033[0m "


log_path = Path("./logs")
log_path.mkdir(exist_ok=True)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_path / "app.log", encoding="utf-8"),
    ]
)


log = logging.getLogger(__name__)