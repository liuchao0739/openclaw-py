from __future__ import annotations

from typing import Any

DEFAULT_ACCOUNT_ID = "default"


def format_account_label(account_id: str, name: str | None = None) -> str:
    base = account_id or DEFAULT_ACCOUNT_ID
    if name and name.strip():
        return f"{base} ({name.strip()})"
    return base


def format_channel_account_label(
    channel: str,
    account_id: str,
    name: str | None = None,
    channel_label: str | None = None,
    channel_style: callable | None = None,
    account_style: callable | None = None,
) -> str:
    channel_text = channel_label or channel
    account_text = format_account_label(account_id, name)
    styled_channel = channel_style(channel_text) if channel_style else channel_text
    styled_account = account_style(account_text) if account_style else account_text
    return f"{styled_channel} {styled_account}"


def append_enabled_configured_linked_bits(bits: list[str], account: dict[str, Any]) -> None:
    if isinstance(account.get("enabled"), bool):
        bits.append("enabled" if account["enabled"] else "disabled")
    if isinstance(account.get("configured"), bool):
        if account["configured"]:
            bits.append("configured")
        else:
            bits.append("not configured")
    if isinstance(account.get("linked"), bool):
        bits.append("linked" if account["linked"] else "not linked")


def append_mode_bit(bits: list[str], account: dict[str, Any]) -> None:
    mode = account.get("mode")
    if isinstance(mode, str) and mode:
        bits.append(f"mode:{mode}")


def append_token_source_bits(bits: list[str], account: dict[str, Any]) -> None:
    def _append(label: str, source_key: str, status_key: str) -> None:
        source = account.get(source_key)
        if not isinstance(source, str) or not source or source == "none":
            return
        status = account.get(status_key)
        unavailable = " (unavailable)" if status == "configured_unavailable" else ""
        bits.append(f"{label}:{source}{unavailable}")

    _append("token", "tokenSource", "tokenStatus")
    _append("bot", "botTokenSource", "botTokenStatus")
    _append("app", "appTokenSource", "appTokenStatus")
    _append("signing", "signingSecretSource", "signingSecretStatus")


def append_base_url_bit(bits: list[str], account: dict[str, Any]) -> None:
    base_url = account.get("baseUrl")
    if isinstance(base_url, str) and base_url:
        bits.append(f"url:{base_url}")


def build_channel_account_line(
    provider: str,
    account: dict[str, Any],
    bits: list[str],
    channel_label: str | None = None,
) -> str:
    account_id = account.get("accountId", DEFAULT_ACCOUNT_ID)
    name = account.get("name")
    label_text = format_channel_account_label(
        channel=provider,
        account_id=account_id,
        name=name if isinstance(name, str) else None,
        channel_label=channel_label,
    )
    return f"- {label_text}: {', '.join(bits)}"


def should_use_wizard(params: dict[str, Any] | None = None) -> bool:
    if params is None:
        return False
    return params.get("hasFlags") is False
