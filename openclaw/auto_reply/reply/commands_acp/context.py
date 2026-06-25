"""ACP command context resolution for session metadata and prompt state."""

from __future__ import annotations

from typing import Any


def resolve_acp_command_channel(params: dict[str, Any]) -> str:
    """Resolve the channel from ACP command params."""
    command = params.get("command", {})
    ctx = params.get("ctx", {})
    channel = command.get("channel", "")
    if not channel:
        channel = ctx.get("channel", "")
    return (channel or "").strip().lower()


def resolve_acp_command_account_id(params: dict[str, Any]) -> str:
    """Resolve the account ID from ACP command params."""
    ctx = params.get("ctx", {})
    cfg = params.get("cfg", {})
    command_channel = params.get("command", {}).get("channel", "")

    # Try ctx first, then config-based resolution
    account_id = ctx.get("accountId", "")
    if account_id:
        return account_id.strip()

    # Fall back to config-based channel account resolution
    if cfg and command_channel:
        channels = cfg.get("channels", {})
        channel_config = channels.get(command_channel, {})
        if isinstance(channel_config, dict):
            account_id = channel_config.get("accountId", "")

    return (account_id or "").strip()


def resolve_acp_command_thread_id(params: dict[str, Any]) -> str | None:
    """Resolve the thread ID from ACP command params."""
    ctx = params.get("ctx", {})
    thread_id = ctx.get("threadId")
    if thread_id and isinstance(thread_id, str) and thread_id.strip():
        return thread_id.strip()
    return None


def resolve_acp_command_conversation_id(params: dict[str, Any]) -> str | None:
    """Resolve the conversation ID from ACP command params."""
    command = params.get("command", {})
    conv_id = command.get("conversationId")
    if conv_id and isinstance(conv_id, str) and conv_id.strip():
        return conv_id.strip()
    return None


def resolve_acp_command_parent_conversation_id(params: dict[str, Any]) -> str | None:
    """Resolve the parent conversation ID from ACP command params."""
    command = params.get("command", {})
    parent_id = command.get("parentConversationId")
    if parent_id and isinstance(parent_id, str) and parent_id.strip():
        return parent_id.strip()
    return None


def resolve_acp_command_binding_context(params: dict[str, Any]) -> dict[str, Any]:
    """Resolve the full binding context from ACP command params."""
    context: dict[str, Any] = {
        "channel": resolve_acp_command_channel(params),
        "accountId": resolve_acp_command_account_id(params),
    }
    thread_id = resolve_acp_command_thread_id(params)
    if thread_id:
        context["threadId"] = thread_id
    conv_id = resolve_acp_command_conversation_id(params)
    if conv_id:
        context["conversationId"] = conv_id
    parent_id = resolve_acp_command_parent_conversation_id(params)
    if parent_id:
        context["parentConversationId"] = parent_id
    return context
