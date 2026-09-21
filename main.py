import logging
import os
import sys

from voicebridge.config import CONFIG_DIR
from voicebridge.tray import run


def _setup_logging() -> None:
    os.makedirs(CONFIG_DIR, exist_ok=True)
    handlers = [logging.FileHandler(os.path.join(CONFIG_DIR, "voicebridge.log"), encoding="utf-8")]
    if sys.stdout is not None:
        handlers.append(logging.StreamHandler())
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", handlers=handlers)


if __name__ == "__main__":
    _setup_logging()
    run()
