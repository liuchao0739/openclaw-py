"""Diagnostics used when descriptor planning violates tool contract invariants.

Mirrors src/tools/diagnostics.ts.
"""

from __future__ import annotations

from typing import Literal

ToolPlanContractErrorCode = Literal["duplicate-tool-name", "missing-executor"]


class ToolPlanContractError(Exception):
    """Error thrown when a visible tool plan cannot be built from descriptors."""

    code: str
    tool_name: str

    def __init__(self, *, code: str, tool_name: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.tool_name = tool_name
