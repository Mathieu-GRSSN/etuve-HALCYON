import logging
from logging.handlers import TimedRotatingFileHandler
import os
from datetime import datetime

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)


class DailyDateFileHandler(TimedRotatingFileHandler):
    def __init__(self, log_dir, **kwargs):
        self.log_dir = log_dir
        filename = self._get_dated_filename()
        super().__init__(filename, **kwargs)

    def _get_dated_filename(self):
        date_str = datetime.now().strftime("%d-%m-%Y")
        return os.path.join(self.log_dir, f"etuve-{date_str}.log")

    def doRollover(self):
        """� minuit, ferme l'ancien fichier et ouvre celui du nouveau jour."""
        self.stream.close()
        self.baseFilename = os.path.abspath(self._get_dated_filename())
        self.stream = self._open()
        self.rolloverAt = self.computeRollover(datetime.now().timestamp())


def setup_logger():
    logger = logging.getLogger("etuve")
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    file_handler = DailyDateFileHandler(
        log_dir=LOG_DIR,
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger