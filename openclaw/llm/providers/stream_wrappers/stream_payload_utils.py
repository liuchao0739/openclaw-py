"""Stream payload utilities normalize provider stream payload fields for wrappers.

Mirrors src/llm/providers/stream-wrappers/stream-payload-utils.ts.
"""

from __future__ import annotations

from typing import Any, Callable


def stream_with_payload_patch(
    underlying: Callable,
    model: Any,
    context: Any,
    options: dict | None,
    patch_payload: Callable[[dict], None],
) -> Any:
    """Wrap a stream function and let callers mutate outgoing provider payload objects."""
    original_on_payload = (options or {}).get("onPayload")

    def _on_payload(payload: Any, *args: Any) -> Any:
        if payload is not None and isinstance(payload, dict):
            patch_payload(payload)
        if original_on_payload is not None:
            return original_on_payload(payload, *args)
        return None

    new_options = {**(options or {}), "onPayload": _on_payload}
    return underlying(model, context, new_options)
