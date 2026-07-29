import re
from typing import Any, Callable, Optional


def _should_patch_anthropic_messages_payload(model: Any) -> bool:
    if not isinstance(model, dict):
        return True
    api = model.get("api")
    return api is None or api == "anthropic-messages"


def _strip_trailing_assistant_prefill(messages: list) -> int:
    stripped = 0
    while messages and isinstance(messages[-1], dict) and messages[-1].get("role") == "assistant":
        messages.pop()
        stripped += 1
    return stripped


def create_cloudflare_ai_gateway_anthropic_thinking_prefill_wrapper(
    base_stream_fn: Optional[Callable],
) -> Callable:
    underlying = base_stream_fn

    async def wrapper(model: Any, context: Any, options: Any) -> Any:
        if underlying is None:
            raise NotImplementedError("stream fn not available")
        messages = None
        if isinstance(options, dict):
            messages = options.get("messages")
        if isinstance(messages, list) and _should_patch_anthropic_messages_payload(model):
            stripped = _strip_trailing_assistant_prefill(messages)
            if stripped > 0:
                pass
        async for chunk in underlying(model, context, options):
            yield chunk

    return wrapper


def wrap_cloudflare_ai_gateway_provider_stream(ctx: dict) -> Optional[Callable]:
    model = ctx.get("model")
    if not _should_patch_anthropic_messages_payload(model):
        return ctx.get("streamFn")
    return create_cloudflare_ai_gateway_anthropic_thinking_prefill_wrapper(ctx.get("streamFn"))
