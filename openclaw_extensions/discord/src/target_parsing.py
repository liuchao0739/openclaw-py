import re
from typing import Any, Dict, Optional


DiscordTargetKind = str


def build_messaging_target(kind: str, id_value: str, raw: str) -> Dict[str, Any]:
    return {"kind": kind, "id": id_value, "raw": raw, "normalized": f"{kind}:{id_value}"}


def parse_mention_prefix_or_at_user_target(raw: str, options: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    mention_pattern = options.get("mentionPattern")
    if mention_pattern:
        match = re.match(mention_pattern, raw)
        if match:
            return build_messaging_target("user", match.group(1), raw)

    for prefix in options.get("prefixes", []):
        prefix_str = prefix["prefix"]
        if raw.lower().startswith(prefix_str.lower()):
            id_value = raw[len(prefix_str):].strip()
            if id_value:
                return build_messaging_target(prefix["kind"], id_value, raw)

    at_user_pattern = options.get("atUserPattern")
    if at_user_pattern and re.match(at_user_pattern, raw):
        error_message = options.get("atUserErrorMessage")
        if error_message:
            raise ValueError(error_message)

    return None


def parse_discord_provider_prefixed_target(raw: str) -> Optional[Dict[str, Any]]:
    match = re.match(r"^discord:(channel|user):(.+)$", raw, re.I)
    if not match:
        return None
    kind = match.group(1).lower()
    id_value = (match.group(2) or "").strip()
    if not kind or not id_value:
        return None
    return build_messaging_target(kind, id_value, f"{kind}:{id_value}")


def parse_discord_target(
    raw: str,
    options: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    options = options or {}
    trimmed = raw.strip()
    if not trimmed:
        return None

    provider_prefixed_target = parse_discord_provider_prefixed_target(trimmed)
    if provider_prefixed_target:
        return provider_prefixed_target

    user_target = parse_mention_prefix_or_at_user_target(
        trimmed,
        {
            "mentionPattern": r"^<@!?(\d+)>$",
            "prefixes": [
                {"prefix": "user:", "kind": "user"},
                {"prefix": "channel:", "kind": "channel"},
                {"prefix": "discord:", "kind": "user"},
            ],
            "atUserPattern": r"^\d+$",
            "atUserErrorMessage": "Discord DMs require a user id (use user:<id> or a <@id> mention)",
        },
    )
    if user_target:
        return user_target

    if re.match(r"^\d+$", trimmed):
        if options.get("defaultKind"):
            return build_messaging_target(options["defaultKind"], trimmed, trimmed)
        ambiguous_message = options.get("ambiguousMessage")
        if ambiguous_message:
            raise ValueError(ambiguous_message)
        raise ValueError(
            f'Ambiguous Discord recipient "{trimmed}". For DMs use "user:{trimmed}" or "<@{trimmed}>"; for channels use "channel:{trimmed}".'
        )

    return build_messaging_target("channel", trimmed, trimmed)


def require_target_kind(params: Dict[str, Any]) -> str:
    target = params.get("target")
    kind = params.get("kind")
    if not target:
        raise ValueError(f'{params.get("platform", "Discord")} target is required')
    if target["kind"] != kind:
        raise ValueError(
            f'{params.get("platform", "Discord")} target {target["normalized"]} is not a {kind}'
        )
    return target["id"]


def resolve_discord_channel_id(raw: str) -> str:
    target = parse_discord_target(raw, {"defaultKind": "channel"})
    return require_target_kind({"platform": "Discord", "target": target, "kind": "channel"})
