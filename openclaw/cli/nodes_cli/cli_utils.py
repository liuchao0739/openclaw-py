"""Node CLI runtime helpers: terminal theme adaptation and standard error handling."""

from __future__ import annotations

import sys
from typing import Any, Callable


def get_nodes_theme() -> dict[str, Any]:
    """Return color helpers that degrade to plain text in non-rich terminals."""
    rich = sys.stdout.isatty()

    def _identity(value: str) -> str:
        return value

    def _color(fn: Callable[[str], str]) -> Callable[[str], str]:
        return fn if rich else _identity

    # ANSI color codes
    def _heading(v: str) -> str:
        return f"\033[1m{v}\033[0m"

    def _ok(v: str) -> str:
        return f"\033[32m{v}\033[0m"

    def _warn(v: str) -> str:
        return f"\033[33m{v}\033[0m"

    def _muted(v: str) -> str:
        return f"\033[2m{v}\033[0m"

    def _error(v: str) -> str:
        return f"\033[31m{v}\033[0m"

    return {
        "rich": rich,
        "heading": _color(_heading),
        "ok": _color(_ok),
        "warn": _color(_warn),
        "muted": _color(_muted),
        "error": _color(_error),
    }


def _unauthorized_hint_for_message(message: str) -> str | None:
    """Check if an error message indicates an auth issue and return a hint."""
    lower = message.lower()
    if "unauthorized" in lower or "401" in lower:
        return "Hint: check your gateway token with --token or OPENCLAW_GATEWAY_TOKEN."
    if "forbidden" in lower or "403" in lower:
        return "Hint: your token may lack node permissions."
    return None


async def run_nodes_command(
    label: str,
    action: Callable[[], Any],
) -> dict[str, Any]:
    """Run a node CLI action with standard failure text and authorization hints.

    Returns a dict with 'ok' and 'error' fields.
    """
    try:
        result = action()
        if hasattr(result, "__await__"):
            result = await result
        return {"ok": True, "error": None}
    except Exception as err:
        message = str(err)
        theme = get_nodes_theme()
        error_lines = [f"nodes {label} failed: {message}"]
        hint = _unauthorized_hint_for_message(message)
        if hint:
            error_lines.append(hint)
        return {"ok": False, "error": "\n".join(error_lines)}
