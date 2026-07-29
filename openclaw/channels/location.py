"""Infer once so text formatting and structured context agree on pin/place/live semantics.

Mirrors src/channels/location.ts.
"""

from __future__ import annotations

from typing import Any

LocationSource = Any
NormalizedLocation = Any

def format_location_text(*args: Any, **kwargs: Any) -> Any: ...
def to_location_context(*args: Any, **kwargs: Any) -> Any: ...
