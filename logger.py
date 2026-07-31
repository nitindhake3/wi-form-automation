import logging
import os
from pathlib import Path
from typing import Optional

LOGS_DIR = Path("logs")

def setup_logger(name: str = "attendance_bot", log_level: int = logging.INFO) -> logging.Logger:
    """Configures and returns a logger instance writing to both console and log files."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOGS_DIR / "attendance_bot.log"

    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    # Avoid duplicate handlers if setup_logger is called multiple times
    if not logger.handlers:
        formatter = logging.Formatter(
            fmt="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        # File Handler
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        file_handler.setLevel(log_level)

        # Console Handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(log_level)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger

def get_logger(name: str = "attendance_bot") -> logging.Logger:
    """Retrieves an existing logger or initializes a default one."""
    return logging.getLogger(name) if logging.getLogger(name).handlers else setup_logger(name)
