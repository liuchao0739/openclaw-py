"""Control UI HTTP utilities provide tiny plain-text helpers for static routes

Mirrors src/gateway/control-ui-http-utils.ts.
"""

from __future__ import annotations

from typing import Any

def is_read_http_method(*args: Any, **kwargs: Any) -> Any: ...
def respond_plain_text(*args: Any, **kwargs: Any) -> Any: ...
def respond_not_found(*args: Any, **kwargs: Any) -> Any: ...
