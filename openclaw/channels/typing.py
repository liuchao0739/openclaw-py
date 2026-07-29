"""Typing indicator lifecycle controller for reply dispatchers.

Mirrors src/channels/typing.ts.
"""

from __future__ import annotations

from typing import Any

TypingCallbacks = Any
CreateTypingCallbacksParams = Any

def create_typing_callbacks(*args: Any, **kwargs: Any) -> Any: ...
