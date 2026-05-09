import logging
from pathlib import Path


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