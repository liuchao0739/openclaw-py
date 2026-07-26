"""Provider stream shared helpers implement reusable stream wrappers and payload policies."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from openclaw.llm.providers.stream_wrappers.stream_payload_utils import stream_with_payload_patch

__all__ = ["create_payload_patch_stream_wrapper"]


def create_payload_patch_stream_wrapper(
    base_stream_fn: Callable[..., Any] | None,
    patch_payload: Callable[[dict[str, Any]], None],
    wrapper_options: dict[str, Any] | None = None,
) -> Callable[..., Any]:
    """Wrap a provider stream so callers can patch the outbound provider payload once."""

    def wrapped(model: Any, context: Any, options: dict[str, Any] | None = None) -> Any:
        if wrapper_options and wrapper_options.get("shouldPatch"):
            should_patch = wrapper_options["shouldPatch"]
            if not should_patch({"model": model, "context": context, "options": options}):
                if base_stream_fn is None:
                    raise RuntimeError("stream function is not configured")
                return base_stream_fn(model, context, options)

        def patch(payload: dict[str, Any]) -> None:
            patch_payload(
                {
                    "payload": payload,
                    "model": model,
                    "context": context,
                    "options": options,
                }
            )

        if base_stream_fn is None:
            raise RuntimeError("stream function is not configured")
        return stream_with_payload_patch(base_stream_fn, model, context, options, patch)

    return wrapped
