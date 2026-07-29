from typing import Any, Callable, Optional

from .models import is_deepseek_v4_model_ref


def _normalize_provider_id(provider_id: str) -> str:
    return provider_id.strip().lower()


def _is_deepseek_provider_id(provider_id: str) -> bool:
    return _normalize_provider_id(provider_id) == "deepseek"


def _stream_simple(model: Any, context: Any, options: Any) -> Any:
    raise NotImplementedError("stream_simple not available")


_THINKING_LEVEL_TO_EFFORT = {
    "off": None,
    "minimal": "low",
    "low": "low",
    "medium": "medium",
    "high": "high",
    "xhigh": "high",
    "max": "max",
}


def _stream_with_payload_patch(
    stream_fn: Callable, model: Any, context: Any, options: Any, patch_fn: Callable
) -> Any:
    async def patched_stream(*args, **kwargs):
        payload_obj = {}
        patch_fn(payload_obj)
        async for chunk in stream_fn(model, context, options):
            yield chunk
    return patched_stream()


def create_deepseek_v4_thinking_wrapper(
    base_stream_fn: Optional[Callable], thinking_level: Optional[str] = None
) -> Callable:
    underlying = base_stream_fn if base_stream_fn is not None else _stream_simple
    level = thinking_level or "high"

    def wrapper(model: Any, context: Any, options: Any) -> Any:
        def patch_fn(payload_obj: dict) -> None:
            effort = _THINKING_LEVEL_TO_EFFORT.get(level)
            if effort is None:
                payload_obj["reasoning"] = False
                payload_obj.pop("reasoning_effort", None)
                payload_obj.pop("reasoningEffort", None)
            else:
                payload_obj["reasoning_effort"] = effort

        return _stream_with_payload_patch(underlying, model, context, options, patch_fn)

    return wrapper


def wrap_deepseek_provider_stream(ctx: dict) -> Optional[Callable]:
    provider = ctx.get("provider", "")
    model = ctx.get("model")
    model_id = ctx.get("modelId", "")
    if not _is_deepseek_provider_id(provider):
        return None
    if model is not None and not is_deepseek_v4_model_ref(
        {"provider": provider, "id": model_id}
    ):
        return None
    return create_deepseek_v4_thinking_wrapper(ctx.get("streamFn"), ctx.get("thinkingLevel"))
