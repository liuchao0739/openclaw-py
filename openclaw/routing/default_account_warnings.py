"""Shared warning text builders for channels that rely on implicit default accounts.

Mirrors src/routing/default-account-warnings.ts.
"""

from __future__ import annotations


def _format_channel_default_account_path(channel_key: str) -> str:
    return f"channels.{channel_key}.defaultAccount"


def format_channel_accounts_default_path(channel_key: str) -> str:
    """Format the accounts.default config path for a channel."""
    return f"channels.{channel_key}.accounts.default"


def format_set_explicit_default_instruction(channel_key: str) -> str:
    """Format instruction to set an explicit default account."""
    return f"Set {_format_channel_default_account_path(channel_key)} or add {format_channel_accounts_default_path(channel_key)}"


def format_set_explicit_default_to_configured_instruction(
    params: dict[str, str],
) -> str:
    """Format instruction when a channel already has configured accounts."""
    channel_key = params["channelKey"]
    return f"Set {_format_channel_default_account_path(channel_key)} to one of these accounts, or add {format_channel_accounts_default_path(channel_key)}"
