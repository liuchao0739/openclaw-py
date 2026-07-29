from __future__ import annotations

from typing import Any


def format_failure_message(error: Exception | str) -> str:
    if isinstance(error, str):
        return f"Error: {error}"
    message = str(error) or type(error).__name__
    return f"Error: {message}"


def format_failure_for_json(error: Exception | str) -> dict:
    if isinstance(error, str):
        return {"ok": False, "error": error}
    return {"ok": False, "error": type(error).__name__, "message": str(error)}


def is_recoverable_error(error: Exception) -> bool:
    if isinstance(error, (KeyboardInterrupt, SystemExit)):
        return False
    return True
