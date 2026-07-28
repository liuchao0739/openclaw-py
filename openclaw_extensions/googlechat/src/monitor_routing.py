from __future__ import annotations

from openclaw.plugin_sdk.webhook_ingress import (
    WEBHOOK_RATE_LIMIT_DEFAULTS,
    create_fixed_window_rate_limiter,
)
from openclaw.plugin_sdk.webhook_request_guards import create_webhook_in_flight_limiter
from openclaw.plugin_sdk.webhook_targets import register_webhook_target_with_plugin_route
from openclaw_extensions.googlechat.src.monitor_types import WebhookTarget
from openclaw_extensions.googlechat.src.types import GoogleChatEvent

webhook_targets: dict[str, list[WebhookTarget]] = {}
webhook_rate_limiter = create_fixed_window_rate_limiter({
    "windowMs": WEBHOOK_RATE_LIMIT_DEFAULTS["windowMs"],
    "maxRequests": WEBHOOK_RATE_LIMIT_DEFAULTS["maxRequests"],
    "maxTrackedKeys": WEBHOOK_RATE_LIMIT_DEFAULTS["maxTrackedKeys"],
})
webhook_in_flight_limiter = create_webhook_in_flight_limiter()

_process_google_chat_event = None


def set_google_chat_webhook_event_processor(process_event) -> None:
    global _process_google_chat_event
    _process_google_chat_event = process_event


async def _handle_google_chat_webhook_request(req, res) -> bool:
    global _process_google_chat_event
    from openclaw_extensions.googlechat.src.monitor_webhook import create_google_chat_webhook_request_handler

    handler = create_google_chat_webhook_request_handler({
        "webhookTargets": webhook_targets,
        "webhookRateLimiter": webhook_rate_limiter,
        "webhookInFlightLimiter": webhook_in_flight_limiter,
        "processEvent": _process_google_chat_event or (lambda e, t: None),
    })
    return await handler(req, res)


def register_google_chat_webhook_target(target: WebhookTarget):
    return register_webhook_target_with_plugin_route({
        "targetsByPath": webhook_targets,
        "target": target,
        "route": {
            "auth": "plugin",
            "match": "exact",
            "pluginId": "googlechat",
            "source": "googlechat-webhook",
            "accountId": target["account"].account_id,
            "log": target["runtime"].get("log"),
            "handler": lambda req, res: _handle_google_chat_webhook_request(req, res),
        },
    })


async def handle_google_chat_webhook_request(req, res) -> bool:
    return await _handle_google_chat_webhook_request(req, res)


__all__ = [
    "set_google_chat_webhook_event_processor",
    "register_google_chat_webhook_target",
    "handle_google_chat_webhook_request",
]