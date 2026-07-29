from __future__ import annotations

from typing import Any


def format_error_output(error: Exception | str) -> str:
    if isinstance(error, str):
        return error
    message = str(error)
    if not message:
        return type(error).__name__
    return f"{type(error).__name__}: {message}"


def format_error_for_json(error: Exception | str) -> dict:
    if isinstance(error, str):
        return {"error": error}
    return {
        "error": type(error).__name__,
        "message": str(error),
    }
