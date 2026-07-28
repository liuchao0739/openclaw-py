from __future__ import annotations

from typing import Any

from openclaw.commands.channels._helpers import (
    _format_docs_link,
    _normalize_optional_lowercase_string,
)


def _color_value(value: str) -> str:
    if value == "none":
        return f"\x1b[31m{value}\x1b[39m"
    if value == "env":
        return f"\x1b[36m{value}\x1b[39m"
    return f"\x1b[32m{value}\x1b[39m"


def _format_enabled(value: bool | None) -> str:
    if value is False:
        return f"\x1b[31mdisabled\x1b[39m"
    return f"\x1b[32menabled\x1b[39m"


def _format_configured(value: bool) -> str:
    if value:
        return f"\x1b[32mconfigured\x1b[39m"
    return f"\x1b[33mnot configured\x1b[39m"


def _format_installed(value: bool) -> str:
    if value:
        return f"\x1b[32minstalled\x1b[39m"
    return f"\x1b[33mnot installed\x1b[39m"


def _format_credential_source(source: str | None = None, status: str | None = None) -> str:
    value = source or "none"
    if status == "configured_unavailable" and value != "none":
        return f"\x1b[33m{value}-unavailable\x1b[39m"
    return _color_value(value)


def _format_token_source(source: str | None = None, status: str | None = None) -> str:
    return f"token={_format_credential_source(source, status)}"


def _format_source(label: str, source: str | None = None, status: str | None = None) -> str:
    return f"{label}={_format_credential_source(source, status)}"


def _format_linked(value: bool) -> str:
    if value:
        return f"\x1b[32mlinked\x1b[39m"
    return f"\x1b[33mnot linked\x1b[39m"


def _format_account_line(channel: str, snapshot: dict[str, Any], installed: bool) -> str:
    label_parts = [channel]
    account_id = snapshot.get("accountId", "default")
    name = snapshot.get("name")
    label = f"{channel} {account_id}"
    if name:
        label += f" ({name})"

    bits: list[str] = [_format_installed(installed)]
    configured = snapshot.get("configured")
    if isinstance(configured, bool):
        bits.append(_format_configured(configured))
    enabled = snapshot.get("enabled")
    if isinstance(enabled, bool):
        bits.append(_format_enabled(enabled))
    linked = snapshot.get("linked")
    if isinstance(linked, bool):
        bits.append(_format_linked(linked))
    if snapshot.get("tokenSource"):
        bits.append(_format_token_source(snapshot["tokenSource"], snapshot.get("tokenStatus")))
    if snapshot.get("botTokenSource"):
        bits.append(_format_source("bot", snapshot["botTokenSource"], snapshot.get("botTokenStatus")))
    if snapshot.get("appTokenSource"):
        bits.append(_format_source("app", snapshot["appTokenSource"], snapshot.get("appTokenStatus")))
    if snapshot.get("baseUrl"):
        bits.append(f"base=\x1b[33m{snapshot['baseUrl']}\x1b[39m")
    return f"- {label}: {', '.join(bits)}"


def _format_catalog_only_line(entry: dict[str, Any], installed: bool, configured: bool, repair_hint: str | None = None) -> str:
    channel_text = f"\x1b[36m{entry.get('label', entry.get('id', 'unknown'))}\x1b[39m"
    bits = [_format_installed(installed), _format_configured(configured), _format_enabled(False)]
    if repair_hint:
        bits.append(repair_hint)
    return f"- {channel_text}: {', '.join(bits)}"


async def channels_list_command(
    opts: dict[str, Any],
    runtime: dict[str, Any] | None = None,
) -> None:
    rt = runtime or {}
    show_all = opts.get("all", False)
    json_output = opts.get("json", False)

    if json_output:
        if rt.get("writeJson"):
            rt["writeJson"](rt, {"chat": {}})
        return

    lines: list[str] = [f"\x1b[1mChat channels:\x1b[22m"]
    lines.append("\x1b[33m- no configured chat channels\x1b[39m")

    if rt.get("log"):
        rt["log"]("\n".join(lines))
        rt["log"](f"\x1b[33mModel provider usage moved out of `channels list` — see `openclaw status` or `openclaw models list`.\x1b[39m")
        rt["log"](f"Docs: {_format_docs_link('/gateway/configuration', 'gateway/configuration')}")
