"""Structured console and rotating file logging."""

import logging
import logging.handlers
from pathlib import Path
from typing import Any

import structlog

from ..config import PROJECT_ROOT


def configure_logging(level: str = "INFO", log_dir: Path = PROJECT_ROOT / "logs") -> None:
    """Configure JSON file logs and concise structured console logs."""
    shared: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.stdlib.add_log_level,
    ]
    formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.JSONRenderer(),
        foreign_pre_chain=shared,
    )
    console = logging.StreamHandler()
    console.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            processor=structlog.dev.ConsoleRenderer(colors=False), foreign_pre_chain=shared
        )
    )
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(console)
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            log_dir / "prospect-finder.log", maxBytes=5_000_000, backupCount=3
        )
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
    except OSError:
        # Console logging remains available when a read-only deployment blocks files.
        pass
    root.setLevel(level)
    structlog.configure(
        processors=[*shared, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
