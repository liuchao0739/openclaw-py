"""Gateway control-reply text classifier.

Mirrors src/gateway/control-reply-text.ts.
"""

from __future__ import annotations

from typing import Any

def is_suppressed_control_reply_text(*args: Any, **kwargs: Any) -> Any: ...
def is_suppressed_control_reply_lead_fragment(*args: Any, **kwargs: Any) -> Any: ...
