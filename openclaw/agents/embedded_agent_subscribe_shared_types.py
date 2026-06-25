"""Shared display and chunking types for embedded-agent subscription handlers."""

from __future__ import annotations

from typing import Literal

ToolResultFormat = Literal["markdown", "plain"]
ToolProgressDetailMode = Literal["explain", "raw"]
