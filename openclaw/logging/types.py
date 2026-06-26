"""Logging shared types describe logger configuration and output options.

Mirrors src/logging/types.ts.
"""

from __future__ import annotations

from typing import Literal, TypedDict

ConsoleStyle = Literal["pretty", "compact", "json"]


class LoggerSettings(TypedDict, total=False):
    level: str
    file: str
    maxFileBytes: int
    consoleLevel: str
    consoleStyle: str
