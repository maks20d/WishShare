import logging
from pathlib import Path

from app.core.config import settings


def configure_logging() -> logging.Logger:
    level_name = (settings.log_level or "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    root = logging.getLogger()
    handlers: list[logging.Handler] = []
    if not root.handlers:
        stream_handler = logging.StreamHandler()
        handlers.append(stream_handler)
    if settings.log_file:
        log_path = Path(settings.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        has_file_handler = any(
            isinstance(handler, logging.FileHandler)
            and getattr(handler, "baseFilename", None) == str(log_path)
            for handler in root.handlers
        )
        if not has_file_handler:
            file_handler = logging.FileHandler(log_path, encoding="utf-8")
            handlers.append(file_handler)

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s"
    )
    for handler in handlers:
        handler.setFormatter(formatter)

    for handler in handlers:
        root.addHandler(handler)
    root.setLevel(level)

    logger = logging.getLogger("wishshare")
    logger.setLevel(level)
    return logger
