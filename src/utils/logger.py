from __future__ import annotations

import logging
import logging.handlers
import os
from pathlib import Path

try:
    import colorlog
    _HAS_COLORLOG = True
except ImportError:
    _HAS_COLORLOG = False

_configured = False


def setup_logging(level: str = "INFO", log_file: str = "~/.voice_transcribe/app.log",
                  max_bytes: int = 5 * 1024 * 1024, backup_count: int = 3) -> None:
    global _configured
    if _configured:
        return
    _configured = True

    numeric_level = getattr(logging, level.upper(), logging.INFO)
    root = logging.getLogger()
    root.setLevel(numeric_level)

    # Console handler
    if _HAS_COLORLOG:
        fmt = colorlog.ColoredFormatter(
            "%(log_color)s%(asctime)s [%(levelname)s]%(reset)s %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        )
        console = logging.StreamHandler()
        console.setFormatter(fmt)
    else:
        fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%H:%M:%S")
        console = logging.StreamHandler()
        console.setFormatter(fmt)
    root.addHandler(console)

    # File handler
    log_path = Path(os.path.expandvars(os.path.expanduser(log_file)))
    log_path.parent.mkdir(parents=True, exist_ok=True)
    file_fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    file_handler = logging.handlers.RotatingFileHandler(
        log_path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
    )
    file_handler.setFormatter(file_fmt)
    root.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
