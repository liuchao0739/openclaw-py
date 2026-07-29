from typing import Any, Callable, Optional

from .model_id import is_fireworks_kimi_model_id


def _normalize_provider_id(provider_id: str) -> str:
    return provider_id.strip().lower()


def _is_fireworks_provider_id(provider_id: str) -> bool:
    normalized = _normalize_provider_id(provider_id)
    return normalized == "fireworks" or normalized == "fireworks-ai"


def _stream_simple(model: Any, context: Any, options: Any) -> Any:
    raise NotImplementedError("stream_simple not available")


def _stream_with_payload_patch(
    stream_fn: Callable, model: Any, context: Any, options: Any, patch_fn: Callable
) -> Any:
    async def patched_stream(*args, **kwargs):
        payload_obj = {}
        patch_fn(payload_obj)
        async for chunk in stream_fn(model, context, options):
            yield chunk
    return patched_stream()


def create_fireworks_kimi_thinking_disabled_wrapper(base_stream_fn: Optional[Callable]) -> Callable:
    underlying = base_stream_fn if base_stream_fn is not None else _stream_simple

    def wrapper(model: Any, context: Any, options: Any) -> Any:
        def patch_fn(payload_obj: dict) -> None:
            payload_obj["thinking"] = {"type": "disabled"}
            payload_obj.pop("reasoning", None)
            payload_obj.pop("reasoning_effort", None)
            payload_obj.pop("reasoningEffort", None)

        return _stream_with_payload_patch(underlying, model, context, options, patch_fn)

    return wrapper


def wrap_fireworks_provider_stream(ctx: dict) -> Optional[Callable]:
    provider = ctx.get("provider", "")
    model = ctx.get("model")
    model_id = ctx.get("modelId", "")
    if (
        not _is_fireworks_provider_id(provider)
        or (model is not None and model.get("api") != "openai-completions")
        or not is_fireworks_kimi_model_id(model_id)
    ):
        return None
    return create_fireworks_kimi_thinking_disabled_wrapper(ctx.get("streamFn"))
