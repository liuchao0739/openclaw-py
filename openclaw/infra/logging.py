"""Structured logging for OpenClaw."""

from __future__ import annotations

import logging
import os

import structlog


def _configure_logging() -> None:
    level_name = (os.environ.get("OPENCLAW_LOG_LEVEL") or "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(level=level, format="%(message)s")
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )


_configured = False


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    global _configured
    if not _configured:
        _configure_logging()
        _configured = True
    return structlog.get_logger(name)
