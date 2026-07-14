"""Structured logging setup (loguru).

Dev: human-readable colored lines. Prod: JSON lines to stdout for log drains.
Scan tasks bind a correlation id: logger.bind(scan_run_id=...).
"""
import sys

from loguru import logger

from app.config import get_settings


def setup_logging() -> None:
    settings = get_settings()
    logger.remove()
    if settings.is_dev:
        logger.add(
            sys.stdout,
            level=settings.log_level,
            format=(
                "<green>{time:HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | "
                "<cyan>{name}</cyan> | {message} | {extra}"
            ),
        )
    else:
        logger.add(sys.stdout, level=settings.log_level, serialize=True)
