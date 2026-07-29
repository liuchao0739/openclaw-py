from __future__ import annotations

INTERNAL_MESSAGE_CHANNEL = "webchat"

INTERNAL_NON_DELIVERY_CHANNELS = (
    "heartbeat",
    "cron",
    "webhook",
    "voice",
    "sessions_send",
)


def is_internal_non_delivery_channel(value: str) -> bool:
    return value in INTERNAL_NON_DELIVERY_CHANNELS


NATIVE_APPROVAL_CHANNELS = (
    "webchat",
    "discord",
    "googlechat",
    "imessage",
    "matrix",
    "qqbot",
    "signal",
    "slack",
    "telegram",
    "whatsapp",
)


def is_native_approval_channel(value: str | None) -> bool:
    if not isinstance(value, str):
        return False
    return value in NATIVE_APPROVAL_CHANNELS
