"""Alibaba Model Studio video provider adapter.

Mirrors extensions/alibaba/video-generation-provider.ts.
"""

from __future__ import annotations

from typing import Any

from openclaw.plugin_sdk.provider_auth import is_provider_api_key_configured
from openclaw.plugin_sdk.provider_auth_runtime import resolve_api_key_for_provider
from openclaw.plugin_sdk.provider_http import (
    default_fetch_fn,
    resolve_provider_http_request_config,
)
from openclaw.plugin_sdk.video_generation import (
    DASHSCOPE_WAN_VIDEO_CAPABILITIES,
    DASHSCOPE_WAN_VIDEO_MODELS,
    DEFAULT_DASHSCOPE_WAN_VIDEO_MODEL,
    DEFAULT_VIDEO_GENERATION_TIMEOUT_MS,
    run_dashscope_video_generation_task,
)

DEFAULT_ALIBABA_VIDEO_BASE_URL = "https://dashscope-intl.aliyuncs.com"
DEFAULT_ALIBABA_VIDEO_MODEL = DEFAULT_DASHSCOPE_WAN_VIDEO_MODEL


def _resolve_alibaba_video_base_url(req: dict[str, Any]) -> str:
    cfg = req.get("cfg") if isinstance(req.get("cfg"), dict) else {}
    models = cfg.get("models") if isinstance(cfg.get("models"), dict) else {}
    providers = models.get("providers") if isinstance(models.get("providers"), dict) else {}
    alibaba = providers.get("alibaba") if isinstance(providers.get("alibaba"), dict) else {}
    base_url = alibaba.get("baseUrl")
    if isinstance(base_url, str) and base_url.strip():
        return base_url.strip()
    return DEFAULT_ALIBABA_VIDEO_BASE_URL


def _resolve_dashscope_aigc_api_base_url(base_url: str) -> str:
    return base_url.rstrip("/")


def build_alibaba_video_generation_provider() -> dict[str, Any]:
    """Build the Alibaba/DashScope video generation provider descriptor."""
    async def generate_video(req: dict[str, Any]) -> dict[str, Any]:
        auth = await resolve_api_key_for_provider(
            {
                "provider": "alibaba",
                "cfg": req.get("cfg"),
                "agentDir": req.get("agentDir"),
                "store": req.get("authStore"),
            }
        )
        api_key = auth.get("apiKey")
        if not api_key:
            raise ValueError("Alibaba Model Studio API key missing")

        request_base_url = _resolve_alibaba_video_base_url(req)
        request_config = resolve_provider_http_request_config(
            {
                "baseUrl": request_base_url,
                "defaultBaseUrl": DEFAULT_ALIBABA_VIDEO_BASE_URL,
                "defaultHeaders": {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "X-DashScope-Async": "enable",
                },
                "provider": "alibaba",
                "capability": "video",
                "transport": "http",
            }
        )
        model = req.get("model")
        resolved_model = model.strip() if isinstance(model, str) and model.strip() else DEFAULT_ALIBABA_VIDEO_MODEL
        base_url = _resolve_dashscope_aigc_api_base_url(request_config["baseUrl"])
        return await run_dashscope_video_generation_task(
            {
                "providerLabel": "Alibaba Wan",
                "model": resolved_model,
                "req": req,
                "url": f"{base_url}/api/v1/services/aigc/video-generation/video-synthesis",
                "headers": request_config["headers"],
                "baseUrl": base_url,
                "timeoutMs": req.get("timeoutMs"),
                "fetchFn": default_fetch_fn,
                "allowPrivateNetwork": request_config["allowPrivateNetwork"],
                "dispatcherPolicy": request_config["dispatcherPolicy"],
                "defaultTimeoutMs": DEFAULT_VIDEO_GENERATION_TIMEOUT_MS,
            }
        )

    return {
        "id": "alibaba",
        "label": "Alibaba Model Studio",
        "defaultModel": DEFAULT_ALIBABA_VIDEO_MODEL,
        "models": list(DASHSCOPE_WAN_VIDEO_MODELS),
        "isConfigured": lambda ctx: is_provider_api_key_configured(
            {
                "provider": "alibaba",
                "agentDir": ctx.get("agentDir"),
            }
        ),
        "capabilities": DASHSCOPE_WAN_VIDEO_CAPABILITIES,
        "generateVideo": generate_video,
    }
