import logging
from pathlib import Path
from datetime import datetime

# Global log level variable (default: INFO)
LOG_LEVEL = logging.INFO

class Logger:
    def __init__(self, log_file: str = "app_log.txt"):
        # Set up default log directory and daily log file
       

        # Set default log directory
        default_log_dir = Path("log")
        default_log_dir.mkdir(parents=True, exist_ok=True)

        # Use daily log file naming: e.g., "log_YYYYMMDD.txt"
        today_str = datetime.now().strftime("%Y%m%d")
        default_log_file = default_log_dir / f"log_{today_str}.txt"

        # If no log_file is provided, use the daily log file in log/
        if log_file == "app_log.txt":
            log_file = str(default_log_file)

        # Ensure the log file exists (touch)
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        Path(log_file).touch(exist_ok=True)
        self.log_file = log_file
        self.logger = logging.getLogger("VidanBhavanLogger")
        self.set_log_level(LOG_LEVEL)
        self._setup_logger()

    def _setup_logger(self):
        # Prevent adding multiple handlers if logger is re-instantiated
        if not self.logger.handlers:
            log_path = Path(self.log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(self.log_file, encoding="utf-8")
            formatter = logging.Formatter(
                "%(asctime)s - %(levelname)s - %(message)s"
            )
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
            self.logger.propagate = False

    def set_log_level(self, level):
        self.logger.setLevel(level)

    def info(self, message: str):
        if self.logger.isEnabledFor(logging.INFO):
            self.logger.info(message)

    def debug(self, message: str):
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(message)

    def error(self, message: str):
        if self.logger.isEnabledFor(logging.ERROR):
            self.logger.error(message)

    def warning(self, message: str):
        if self.logger.isEnabledFor(logging.WARNING):
            self.logger.warning(message)


