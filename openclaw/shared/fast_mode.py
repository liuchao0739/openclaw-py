"""Fast mode helpers for auto-on/off and session/agent/config resolution."""

from __future__ import annotations

from typing import Any, Literal

FastModeSource = Literal["session", "agent", "config", "default"]
FastMode = Literal["auto", "on", "off"]

DEFAULT_FAST_MODE_AUTO_ON_SECONDS = 60


def _normalize_lowercase_or_empty(value: str | None) -> str:
    if value is None:
        return ""
    return value.strip().lower()


def _model_config_key(provider: str | None, model: str | None) -> str:
    provider_id = (provider or "").strip()
    model_id = (model or "").strip()
    if not provider_id:
        return model_id
    if not model_id:
        return provider_id
    if _normalize_lowercase_or_empty(model_id).startswith(f"{_normalize_lowercase_or_empty(provider_id)}/"):
        return model_id
    return f"{provider_id}/{model_id}"


def _model_config_keys(provider: str | None, model: str | None) -> list[str]:
    key = _model_config_key(provider, model)
    provider_id = _normalize_lowercase_or_empty(provider)
    if provider_id != "openai-codex":
        return [key]
    open_ai_key = _model_config_key("openai", model)
    return [key] if open_ai_key == key else [key, open_ai_key]


def resolve_fast_mode_model_params(
    cfg: dict[str, Any] | None,
    provider: str | None = None,
    model: str | None = None,
) -> dict[str, Any] | None:
    models = None
    if cfg:
        models = cfg.get("agents", {}).get("defaults", {}).get("models")
    if not models:
        return None
    for key in _model_config_keys(provider, model):
        model_config = models.get(key)
        if model_config and model_config.get("params"):
            return model_config["params"]
    return None


def normalize_fast_mode_auto_on_seconds(value: Any) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool) and value > 0:
        return value
    return None


def resolve_fast_mode_model_auto_on_seconds(
    cfg: dict[str, Any] | None,
    provider: str | None = None,
    model: str | None = None,
) -> int:
    model_params = resolve_fast_mode_model_params(cfg, provider, model)
    if model_params:
        for key in ("fastAutoOnSeconds", "fast_auto_on_seconds", "fastSeconds", "fast_seconds"):
            val = normalize_fast_mode_auto_on_seconds(model_params.get(key))
            if val is not None:
                return val
    return DEFAULT_FAST_MODE_AUTO_ON_SECONDS


def resolve_fast_mode_for_elapsed(
    mode: FastMode | None,
    started_at_ms: int,
    fast_auto_on_seconds: int | None = None,
    now_ms: int | None = None,
) -> dict[str, Any]:
    import time
    if now_ms is None:
        now_ms = int(time.time() * 1000)
    elapsed_ms = max(0, now_ms - started_at_ms)
    threshold = resolve_fast_mode_model_auto_on_seconds({}, None, None)
    if fast_auto_on_seconds is not None:
        threshold = normalize_fast_mode_auto_on_seconds(fast_auto_on_seconds) or DEFAULT_FAST_MODE_AUTO_ON_SECONDS
    enabled = mode == "auto" and elapsed_ms <= threshold * 1000 if mode else (mode is True)
    elapsed_seconds = elapsed_ms // 1000
    return {
        "mode": mode,
        "enabled": enabled if mode else False,
        "elapsed_seconds": elapsed_seconds,
        "fast_auto_on_seconds": threshold,
    }


def format_fast_mode_auto_progress_text(enabled: bool, elapsed_seconds: int, fast_auto_on_seconds: int | None = None) -> str:
    if enabled:
        return "💨Fast: auto-on"
    seconds = fast_auto_on_seconds or DEFAULT_FAST_MODE_AUTO_ON_SECONDS
    return f"💨Fast: auto-off({elapsed_seconds}s>={seconds}s)"


def format_fast_mode_value(mode: FastMode | None) -> str:
    if mode == "auto":
        return "auto"
    if mode is True:
        return "on"
    return "off"


def format_fast_mode_auto_label(fast_auto_on_seconds: int | None = None) -> str:
    seconds = fast_auto_on_seconds or DEFAULT_FAST_MODE_AUTO_ON_SECONDS
    return f"auto ({seconds} sec)"


def format_fast_mode_status_value(mode: FastMode | None, fast_auto_on_seconds: int | None = None) -> str:
    if mode == "auto":
        return format_fast_mode_auto_label(fast_auto_on_seconds)
    return format_fast_mode_value(mode)


def format_fast_mode_command_options(fast_auto_on_seconds: int | None = None) -> str:
    return f"on, off, {format_fast_mode_auto_label(fast_auto_on_seconds)}, default, status"


def normalize_fast_mode_source(value: Any) -> FastModeSource | None:
    if value in ("session", "agent", "config", "default"):
        return value
    return None


def format_fast_mode_source_suffix(source: FastModeSource | None) -> str:
    if source == "session":
        return " (session)"
    if source == "agent":
        return " (default: agent)"
    if source == "config":
        return " (default: model)"
    if source == "default":
        return " (default)"
    return ""


def format_fast_mode_current_status(
    mode: FastMode | None,
    source: FastModeSource | None = None,
    fast_auto_on_seconds: int | None = None,
    label: str = "Current fast mode",
) -> str:
    return f"{label}: {format_fast_mode_status_value(mode, fast_auto_on_seconds)}{format_fast_mode_source_suffix(source)}."
