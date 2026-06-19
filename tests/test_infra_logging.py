"""Tests for openclaw.infra.logging."""

from __future__ import annotations

from openclaw.infra.logging import get_logger


def test_get_logger_returns_bound_logger() -> None:
    logger = get_logger("test")
    logger.info("hello", component="logging")
