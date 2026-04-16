import logging
from logging.handlers import TimedRotatingFileHandler
import json
import os
from app.core.config.settings import settings

class JsonFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "level": record.levelname,
            "message": record.getMessage(),
            "time": self.formatTime(record),
            "module": record.module,
            "exception": record.exc_info and self.formatException(record.exc_info)
        })

def setup_logger(name, level, file):
    # Ensure log directory exists
    log_dir = os.path.dirname(file)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    handler = TimedRotatingFileHandler(
        file, when="midnight", backupCount=30
    )
    handler.setFormatter(JsonFormatter())

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
    logger.propagate = False
    return logger

# Convert string level to logging level
log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

debug_logger = setup_logger("debug", logging.DEBUG, f"{settings.log_dir}/debug.log")
info_logger = setup_logger("info", logging.INFO, f"{settings.log_dir}/info.log")
error_logger = setup_logger("error", logging.ERROR, f"{settings.log_dir}/error.log")

def add_to_log(level: str, message: str, show_in_terminal: bool = True, **extra):
    logger_map = {
        "debug": debug_logger,
        "info": info_logger,
        "error": error_logger
    }
    logger = logger_map.get(level, info_logger)
    logger.log(getattr(logging, level.upper()), message, extra=extra)
    if show_in_terminal:
        print(message)
