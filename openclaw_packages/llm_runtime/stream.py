"""LLM runtime stream helpers."""

from __future__ import annotations

from openclaw.llm.core import AssistantMessage, Model

from .api_registry import get_api_provider
from .types import (
    Api,
    Context,
    ProviderStreamOptions,
    SimpleStreamOptions,
)


def _resolve_api_provider(api: Api):
    provider = get_api_provider(api)
    if provider is None:
        raise RuntimeError(f"No API provider registered for api: {api}")
    return provider


def stream(
    model: Model,
    context: Context,
    options: ProviderStreamOptions | None = None,
):
    """Stream a provider turn through the registered implementation for the model API."""
    provider = _resolve_api_provider(model.api)
    return provider["stream"](model, context, options)


async def complete(
    model: Model,
    context: Context,
    options: ProviderStreamOptions | None = None,
) -> AssistantMessage:
    """Run a provider turn and resolve the final assistant message result."""
    event_stream = stream(model, context, options)
    return await event_stream.result()


def stream_simple(
    model: Model,
    context: Context,
    options: SimpleStreamOptions | None = None,
):
    """Stream a simple provider turn through the registered implementation."""
    provider = _resolve_api_provider(model.api)
    return provider["stream_simple"](model, context, options)


async def complete_simple(
    model: Model,
    context: Context,
    options: SimpleStreamOptions | None = None,
) -> AssistantMessage:
    """Run a simple provider turn and resolve the final assistant message result."""
    event_stream = stream_simple(model, context, options)
    return await event_stream.result()
