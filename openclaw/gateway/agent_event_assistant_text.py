"""Gateway assistant-event text extractor.

Mirrors src/gateway/agent-event-assistant-text.ts.
"""

from __future__ import annotations

from typing import Any

def resolve_assistant_stream_delta_text(*args: Any, **kwargs: Any) -> Any: ...
def is_replaceable_assistant_stream_event(*args: Any, **kwargs: Any) -> Any: ...
def resolve_assistant_stream_snapshot_text(*args: Any, **kwargs: Any) -> Any: ...
