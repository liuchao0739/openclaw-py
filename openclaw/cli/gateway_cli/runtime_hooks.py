"""Gateway run runtime hooks — managed proxy lifecycle callbacks."""

from __future__ import annotations

from typing import Any, Callable


_active_gateway_run_runtime_hooks: dict[str, Any] = {}


def get_gateway_run_runtime_hooks() -> dict[str, Any]:
    """Get the active gateway run runtime hooks."""
    return _active_gateway_run_runtime_hooks


def install_gateway_run_runtime_hooks(hooks: dict[str, Any]) -> Callable[[], None]:
    """Install gateway run runtime hooks. Returns a restore function."""
    global _active_gateway_run_runtime_hooks
    previous = _active_gateway_run_runtime_hooks
    _active_gateway_run_runtime_hooks = hooks

    def _restore() -> None:
        global _active_gateway_run_runtime_hooks
        if _active_gateway_run_runtime_hooks is hooks:
            _active_gateway_run_runtime_hooks = previous

    return _restore
