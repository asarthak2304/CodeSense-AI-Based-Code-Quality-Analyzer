"""
CodeSense - Logging System
Centralized, structured logging with file rotation and color console output.
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional


class ColorFormatter(logging.Formatter):
    """Console formatter with ANSI colors."""
    COLORS = {
        logging.DEBUG:    "\033[36m",   # Cyan
        logging.INFO:     "\033[32m",   # Green
        logging.WARNING:  "\033[33m",   # Yellow
        logging.ERROR:    "\033[31m",   # Red
        logging.CRITICAL: "\033[35m",   # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelno, self.RESET)
        record.levelname = f"{color}{record.levelname:<8}{self.RESET}"
        return super().format(record)


def setup_logger(
    name: str,
    level: str = "INFO",
    log_dir: str = "logs",
    console: bool = True,
    file: bool = True,
    max_bytes: int = 10 * 1024 * 1024,   # 10 MB
    backup_count: int = 5,
) -> logging.Logger:
    """
    Configure and return a named logger.

    Args:
        name:         Logger name (usually __name__).
        level:        Logging level string.
        log_dir:      Directory for log files.
        console:      Attach StreamHandler to stdout.
        file:         Attach RotatingFileHandler.
        max_bytes:    Max size before log rotation.
        backup_count: Number of rotated files to keep.
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    log = logging.getLogger(name)
    log.setLevel(numeric_level)

    if log.handlers:   # Avoid duplicate handlers on re-import
        return log

    fmt_str  = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    date_fmt = "%Y-%m-%d %H:%M:%S"

    if console:
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(numeric_level)
        ch.setFormatter(ColorFormatter(fmt_str, datefmt=date_fmt))
        log.addHandler(ch)

    if file:
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        log_path = Path(log_dir) / f"{name.replace('.', '_')}.log"
        fh = logging.handlers.RotatingFileHandler(
            log_path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
        )
        fh.setLevel(numeric_level)
        fh.setFormatter(logging.Formatter(fmt_str, datefmt=date_fmt))
        log.addHandler(fh)

    return log


def get_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """Return or create a logger for the given module name."""
    from config import get_config
    cfg = get_config()
    effective_level = level or cfg.log_level
    return setup_logger(name, level=effective_level, log_dir=cfg.log_dir)