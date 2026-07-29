"""Channel inbound debounce policy.

Mirrors src/channels/inbound-debounce-policy.ts.
"""

from __future__ import annotations

from typing import Any

def should_debounce_text_inbound(*args: Any, **kwargs: Any) -> Any: ...
def create_channel_inbound_debouncer(*args: Any, **kwargs: Any) -> Any: ...
