"""LLM Core diagnostics helpers.

Mirrors packages/llm-core/src/utils/diagnostics.ts.
"""

from __future__ import annotations

import time
from typing import Any, TypedDict


class DiagnosticErrorInfo(TypedDict, total=False):
    name: str
    message: str
    stack: str
    code: str | int


class AssistantMessageDiagnostic(TypedDict, total=False):
    type: str
    timestamp: int
    error: DiagnosticErrorInfo
    details: dict[str, Any]


def format_thrown_value(value: Any) -> str:
    """Format arbitrary thrown values into diagnostic-safe text."""
    if isinstance(value, BaseException):
        return value.args[0] if value.args and isinstance(value.args[0], str) else str(value)
    if isinstance(value, str):
        return value
    return str(value)


def extract_diagnostic_error(error: Any) -> DiagnosticErrorInfo:
    """Extract serializable diagnostic error fields from Error and non-Error throws."""
    if not isinstance(error, BaseException):
        return {"name": "ThrownValue", "message": format_thrown_value(error)}

    code = getattr(error, "code", None)
    name = type(error).__name__ or None
    message = str(error) or name or ""
    result: DiagnosticErrorInfo = {
        "name": name,
        "message": message,
    }
    stack = getattr(error, "__traceback__", None)
    if stack is not None:
        import traceback

        result["stack"] = "".join(traceback.format_exception(type(error), error, stack))
    if isinstance(code, (str, int)):
        result["code"] = code
    return result


def create_assistant_message_diagnostic(
    diagnostic_type: str,
    error: Any,
    details: dict[str, Any] | None = None,
) -> AssistantMessageDiagnostic:
    """Create a timestamped assistant-message diagnostic entry."""
    diagnostic: AssistantMessageDiagnostic = {
        "type": diagnostic_type,
        "timestamp": int(time.time() * 1000),
        "error": extract_diagnostic_error(error),
    }
    if details is not None:
        diagnostic["details"] = details
    return diagnostic


def append_assistant_message_diagnostic(
    message: dict[str, Any],
    diagnostic: AssistantMessageDiagnostic,
) -> None:
    """Append a diagnostic while preserving existing message diagnostics."""
    existing = message.get("diagnostics")
    message["diagnostics"] = [*existing, diagnostic] if isinstance(existing, list) else [diagnostic]


__all__ = [
    "AssistantMessageDiagnostic",
    "DiagnosticErrorInfo",
    "append_assistant_message_diagnostic",
    "create_assistant_message_diagnostic",
    "extract_diagnostic_error",
    "format_thrown_value",
]
