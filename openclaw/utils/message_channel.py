from __future__ import annotations

from typing import Any

from openclaw.utils.message_channel_constants import (
    INTERNAL_MESSAGE_CHANNEL,
    is_internal_non_delivery_channel,
    is_native_approval_channel,
    NATIVE_APPROVAL_CHANNELS,
)
from openclaw.utils.message_channel_normalize import (
    is_deliverable_message_channel,
    is_gateway_message_channel,
    list_deliverable_message_channels,
    normalize_message_channel,
    resolve_gateway_message_channel,
    resolve_message_channel,
)

try:
    from openclaw.protocol.client_info import (
        GATEWAY_CLIENT_MODES,
        GATEWAY_CLIENT_NAMES,
        normalize_gateway_client_mode,
        normalize_gateway_client_name,
    )
except ImportError:
    GATEWAY_CLIENT_MODES = Any
    GATEWAY_CLIENT_NAMES = Any

    def normalize_gateway_client_mode(value: Any) -> Any:
        return value

    def normalize_gateway_client_name(value: Any) -> Any:
        return value


def is_gateway_cli_client(client: Any = None) -> bool:
    return normalize_gateway_client_mode(getattr(client, "mode", None)) == getattr(GATEWAY_CLIENT_MODES, "CLI", "cli")


def is_operator_ui_client(client: Any = None) -> bool:
    client_id = normalize_gateway_client_name(getattr(client, "id", None))
    return client_id in (
        getattr(GATEWAY_CLIENT_NAMES, "CONTROL_UI", "control-ui"),
        getattr(GATEWAY_CLIENT_NAMES, "TUI", "tui"),
    )


def is_browser_operator_ui_client(client: Any = None) -> bool:
    client_id = normalize_gateway_client_name(getattr(client, "id", None))
    return client_id == getattr(GATEWAY_CLIENT_NAMES, "CONTROL_UI", "control-ui")


def is_internal_message_channel(raw: str | None = None) -> bool:
    return normalize_message_channel(raw) == INTERNAL_MESSAGE_CHANNEL


def is_webchat_client(client: Any = None) -> bool:
    mode = normalize_gateway_client_mode(getattr(client, "mode", None))
    if mode == getattr(GATEWAY_CLIENT_MODES, "WEBCHAT", "webchat"):
        return True
    return normalize_gateway_client_name(getattr(client, "id", None)) == getattr(
        GATEWAY_CLIENT_NAMES, "WEBCHAT_UI", "webchat-ui"
    )


def is_markdown_capable_message_channel(raw: str | None = None) -> bool:
    channel = normalize_message_channel(raw)
    if not channel:
        return False
    if channel == INTERNAL_MESSAGE_CHANNEL or channel == "tui":
        return True
    try:
        from openclaw.channels.registry import normalize_chat_channel_id, get_registered_channel_plugin_meta

        built_in_channel = normalize_chat_channel_id(channel)
        if built_in_channel:
            try:
                from openclaw.channels.chat_meta import get_chat_channel_meta

                built_in_meta = get_chat_channel_meta(built_in_channel)
                if built_in_meta:
                    return built_in_meta.get("markdownCapable") is True
            except ImportError:
                pass
        meta = get_registered_channel_plugin_meta(channel)
        if meta:
            return meta.get("markdownCapable") is True
    except ImportError:
        pass
    return False
