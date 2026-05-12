import logging
from logging.handlers import RotatingFileHandler
import os
from datetime import datetime

LOG_DIR = "logs"
LOG_FILE = datetime.now().strftime("etuve-%d-%m-%Y")
os.makedirs(LOG_DIR, exist_ok=True)

def setup_logger():
    logger = logging.getLogger(LOG_FILE)
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    file_handler = RotatingFileHandler(
        f"{LOG_DIR}/{LOG_FILE}.log",
        maxBytes=1_000_000,   # 1 MB
        backupCount=5
    )
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger