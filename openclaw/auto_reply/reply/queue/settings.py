"""Queue settings resolution from config."""

from __future__ import annotations

from typing import Any

from openclaw.auto_reply.reply.queue.types import QueueDropPolicy, QueueMode, QueueSettings

DEFAULT_QUEUE_SETTINGS: QueueSettings = {
    "mode": "followup",
    "debounceMs": 500,
    "cap": 10,
    "dropPolicy": "old",
}


def resolve_queue_settings(config: dict[str, Any] | None = None) -> QueueSettings:
    """Resolve queue settings from config with defaults."""
    settings = dict(DEFAULT_QUEUE_SETTINGS)

    if not config:
        return settings

    auto_reply = config.get("autoReply", {})
    if isinstance(auto_reply, dict):
        queue_config = auto_reply.get("queue", {})
        if isinstance(queue_config, dict):
            if "mode" in queue_config:
                mode = queue_config["mode"]
                if mode in ("steer", "followup", "collect", "interrupt"):
                    settings["mode"] = mode
            if "debounceMs" in queue_config:
                settings["debounceMs"] = int(queue_config["debounceMs"])
            if "cap" in queue_config:
                settings["cap"] = int(queue_config["cap"])
            if "dropPolicy" in queue_config:
                policy = queue_config["dropPolicy"]
                if policy in ("old", "new", "summarize"):
                    settings["dropPolicy"] = policy

    return settings


def normalize_queue_settings(settings: dict[str, Any]) -> QueueSettings:
    """Normalize and validate queue settings."""
    normalized: QueueSettings = {
        "mode": settings.get("mode", "followup"),
        "debounceMs": max(0, int(settings.get("debounceMs", 500))),
        "cap": max(1, int(settings.get("cap", 10))),
        "dropPolicy": settings.get("dropPolicy", "old"),
    }
    return normalized
