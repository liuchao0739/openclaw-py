"""Discord plugin module implements target parsing behavior."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

DiscordTargetKind = Literal["user", "channel"]


@dataclass(frozen=True)
class DiscordTarget:
    kind: DiscordTargetKind
    id: str
    raw: str


def _build_messaging_target(kind: DiscordTargetKind, target_id: str, raw: str) -> DiscordTarget:
    return DiscordTarget(kind=kind, id=target_id, raw=raw)


def _parse_discord_provider_prefixed_target(raw: str) -> DiscordTarget | None:
    match = re.match(r"^discord:(channel|user):(.+)$", raw, flags=re.IGNORECASE)
    if not match:
        return None
    kind = match.group(1).lower()
    target_id = (match.group(2) or "").strip()
    if kind not in ("channel", "user") or not target_id:
        return None
    return _build_messaging_target(kind, target_id, f"{kind}:{target_id}")


def parse_discord_target(
    raw: str,
    options: dict[str, object] | None = None,
) -> DiscordTarget | None:
    options = options or {}
    trimmed = raw.strip()
    if not trimmed:
        return None
    provider_prefixed = _parse_discord_provider_prefixed_target(trimmed)
    if provider_prefixed:
        return provider_prefixed

    mention = re.match(r"^<@!?(\d+)>$", trimmed)
    if mention:
        target_id = mention.group(1)
        return _build_messaging_target("user", target_id, trimmed)

    for prefix, kind in (("user:", "user"), ("channel:", "channel"), ("discord:", "user")):
        if trimmed.lower().startswith(prefix):
            target_id = trimmed[len(prefix) :].strip()
            if target_id:
                return _build_messaging_target(kind, target_id, trimmed)

    if re.fullmatch(r"\d+", trimmed):
        default_kind = options.get("defaultKind")
        if default_kind in ("user", "channel"):
            return _build_messaging_target(default_kind, trimmed, trimmed)
        ambiguous_message = options.get("ambiguousMessage")
        message = (
            ambiguous_message
            if isinstance(ambiguous_message, str)
            else (
                f'Ambiguous Discord recipient "{trimmed}". For DMs use "user:{trimmed}" or '
                f'"<@{trimmed}>"; for channels use "channel:{trimmed}".'
            )
        )
        raise ValueError(message)

    return _build_messaging_target("channel", trimmed, trimmed)


def resolve_discord_channel_id(raw: str) -> str:
    target = parse_discord_target(raw, {"defaultKind": "channel"})
    if target is None or target.kind != "channel":
        raise ValueError("Discord channel target is required (use channel:<id>).")
    return target.id


__all__ = ["DiscordTarget", "DiscordTargetKind", "parse_discord_target", "resolve_discord_channel_id"]
