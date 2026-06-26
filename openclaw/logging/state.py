"""Process-local logging state shared by logger, console capture, and test reset helpers.

Mirrors src/logging/state.ts.
"""

from __future__ import annotations

from typing import Any


class LoggingState:
    """Process-local mutable logging state."""

    def __init__(self) -> None:
        self.cached_logger: Any = None
        self.cached_settings: Any = None
        self.cached_console_settings: Any = None
        self.override_settings: Any = None
        self.invalid_env_log_level_value: str | None = None
        self.console_patched: bool = False
        self.force_console_to_stderr: bool = False
        self.console_timestamp_prefix: bool = False
        self.console_subsystem_filter: list[str] | None = None
        self.resolving_console_settings: bool = False
        self.stream_error_handlers_installed: bool = False
        self.raw_console: Any = None

    def reset(self) -> None:
        """Reset all state to defaults (for tests)."""
        self.__init__()


logging_state = LoggingState()
