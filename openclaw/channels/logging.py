"""Shared channel diagnostic formatters exposed through the plugin SDK.

Mirrors src/channels/logging.ts.
"""

from __future__ import annotations

from typing import Any

LogFn = Any

def log_inbound_drop(*args: Any, **kwargs: Any) -> Any: ...
def log_typing_failure(*args: Any, **kwargs: Any) -> Any: ...
def log_ack_failure(*args: Any, **kwargs: Any) -> Any: ...
