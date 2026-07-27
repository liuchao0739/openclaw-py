from typing import Callable, Dict, Any


def create_deepinfra_anthropic_cache_wrapper(base_stream_fn: Callable) -> Callable:
    def wrapper(model: Dict[str, Any], context: Dict[str, Any], options: Dict[str, Any]):
        model_id_raw = model.get("id")
        model_id = str(model_id_raw).lower() if model_id_raw else ""

        if not model_id.startswith("anthropic/"):
            return base_stream_fn(model, context, options)

        def payload_patch(payload: Dict[str, Any]) -> Dict[str, Any]:
            payload["cache_control"] = {
                "type": "ephemeral",
            }
            return payload

        return base_stream_fn(model, context, options)

    return wrapper

__all__ = ["create_deepinfra_anthropic_cache_wrapper"]