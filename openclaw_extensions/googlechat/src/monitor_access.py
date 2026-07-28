from __future__ import annotations

from openclaw.plugin_sdk.channel_ingress_runtime import (
    channel_ingress_routes,
    create_channel_ingress_resolver,
    define_stable_channel_ingress_identity,
)
from openclaw.plugin_sdk.string_coerce_runtime import (
    normalize_lowercase_string_or_empty,
    normalize_optional_string,
    normalize_string_entries,
)
from openclaw_extensions.googlechat.runtime_api import (
    GROUP_POLICY_BLOCKED_LABEL,
    create_channel_pairing_controller,
    is_dangerous_name_matching_enabled,
    resolve_allowlist_provider_runtime_group_policy,
    resolve_default_group_policy,
    warn_missing_provider_group_policy_fallback_once,
)
from openclaw_extensions.googlechat.src.accounts import ResolvedGoogleChatAccount
from openclaw_extensions.googlechat.src.api import send_google_chat_message
from openclaw_extensions.googlechat.src.monitor_types import WebhookTarget
from openclaw_extensions.googlechat.src.types import GoogleChatAnnotation, GoogleChatMessage, GoogleChatSpace


def _normalize_user_id(raw: str | None = None) -> str:
    trimmed = normalize_optional_string(raw) or ""
    if not trimmed:
        return ""
    return normalize_lowercase_string_or_empty(trimmed.replace(r"^users/", ""))


GOOGLECHAT_EMAIL_KIND = "plugin:googlechat-email"


def _normalize_entry_value(raw: str | None = None) -> str:
    return normalize_lowercase_string_or_empty(raw or "")


def _normalize_google_chat_stable_entry(entry: str) -> str | None:
    without_provider = normalize_entry_value(entry).replace(
        r"^(googlechat|google-chat|gchat):", ""
    )
    if not without_provider:
        return None
    if without_provider.startswith("users/"):
        return normalize_user_id(without_provider)
    return without_provider


def _normalize_google_chat_email_entry(entry: str) -> str | None:
    without_provider = normalize_entry_value(entry).replace(
        r"^(googlechat|google-chat|gchat):", ""
    )
    if without_provider.startswith("users/"):
        return None
    stable = _normalize_google_chat_stable_entry(entry)
    if stable and "@" in stable:
        return stable
    return None


google_chat_ingress_identity = define_stable_channel_ingress_identity({
    "key": "sender-id",
    "normalizeEntry": _normalize_google_chat_stable_entry,
    "normalizeSubject": _normalize_user_id,
    "aliases": [
        {
            "key": "email",
            "kind": GOOGLECHAT_EMAIL_KIND,
            "normalizeEntry": _normalize_google_chat_email_entry,
            "normalizeSubject": _normalize_entry_value,
            "dangerous": True,
        },
    ],
    "isWildcardEntry": lambda entry: normalize_entry_value(entry) == "*",
    "resolveEntryId": lambda params: (
        f"entry-{params['entryIndex'] + 1}:user"
        if params["fieldKey"] == "stableId"
        else f"entry-{params['entryIndex'] + 1}:{params['fieldKey']}"
    ),
})

_warned_deprecated_users_email_allow_from: set[str] = set()
_warned_mutable_group_keys: set[str] = set()


def _resolve_group_config(params: dict) -> dict:
    group_id = params["groupId"]
    group_name = params.get("groupName")
    groups = params.get("groups", {})
    entries = groups or {}
    keys = list(entries.keys())
    if len(keys) == 0:
        return {"entry": None, "allowlistConfigured": False, "deprecatedNameMatch": False}
    entry = entries.get(group_id)
    normalized_group_name = normalize_lowercase_string_or_empty(group_name or "")
    deprecated_name_match = False
    if not entry and group_name:
        deprecated_name_match = any(
            (
                not not key.strip()
                and key.strip() != "*"
                and not re.match(r"^spaces/", key.strip(), re.IGNORECASE)
                and (key.strip() == group_name or normalize_lowercase_string_or_empty(key.strip()) == normalized_group_name)
            )
            for key in keys
        )
    fallback = entries.get("*")
    return {
        "entry": None if deprecated_name_match else (entry or fallback),
        "allowlistConfigured": True,
        "fallback": fallback,
        "deprecatedNameMatch": deprecated_name_match,
    }


import re


def _extract_mention_info(annotations: list | None, bot_user: str | None = None) -> dict:
    if not annotations:
        annotations = []
    mention_annotations = [a for a in annotations if a.get("type") == "USER_MENTION"]
    has_any_mention = len(mention_annotations) > 0
    bot_targets = {"users/app", (bot_user or "").strip()}.difference({""})
    was_mentioned = False
    for entry in mention_annotations:
        user_name = (entry.get("userMention") or {}).get("user", {}).get("name")
        if not user_name:
            continue
        if user_name in bot_targets:
            was_mentioned = True
            break
        if _normalize_user_id(user_name) == "app":
            was_mentioned = True
            break
    return {"hasAnyMention": has_any_mention, "wasMentioned": was_mentioned}


def _warn_deprecated_users_email_entries(log_verbose, entries: list) -> None:
    deprecated = [
        v for v in [normalize_optional_string(e) for e in entries]
        if v and re.match(r"^users/.+@.+", v, re.IGNORECASE)
    ]
    if len(deprecated) == 0:
        return
    key = ",".join(sorted([normalize_lowercase_string_or_empty(v) for v in deprecated]))
    if key in _warned_deprecated_users_email_allow_from:
        return
    _warned_deprecated_users_email_allow_from.add(key)
    log_verbose(
        f'Deprecated allowFrom entry detected: "users/<email>" is no longer treated as an email allowlist. '
        f'Use raw email (alice@example.com) or immutable user id (users/<id>). entries={", ".join(deprecated)}'
    )


def _warn_mutable_group_keys_configured(log_verbose, groups: dict | None) -> None:
    if groups is None:
        groups = {}
    mutable_keys = [
        key.strip() for key in groups.keys()
        if key.strip() and key.strip() != "*" and not re.match(r"^spaces/", key.strip(), re.IGNORECASE)
    ]
    if len(mutable_keys) == 0:
        return
    warning_key = ",".join(sorted([normalize_lowercase_string_or_empty(k) for k in mutable_keys]))
    if warning_key in _warned_mutable_group_keys:
        return
    _warned_mutable_group_keys.add(warning_key)
    log_verbose(
        f"Deprecated Google Chat group key detected: group routing now requires stable space ids (spaces/<spaceId>). "
        f"Update channels.googlechat.groups keys: {', '.join(mutable_keys)}"
    )


async def apply_google_chat_inbound_access_policy(params: dict) -> dict:
    account = params["account"]
    config = params["config"]
    core = params["core"]
    space = params["space"]
    message = params["message"]
    is_group = params["isGroup"]
    sender_id = params["senderId"]
    sender_name = params["senderName"]
    sender_email = params.get("senderEmail")
    raw_body = params["rawBody"]
    status_sink = params.get("statusSink")
    log_verbose = params["logVerbose"]

    allow_name_matching = is_dangerous_name_matching_enabled(account.config)
    space_id = space.get("name", "")
    pairing = create_channel_pairing_controller({
        "core": core,
        "channel": "googlechat",
        "accountId": account.account_id,
    })

    default_group_policy = resolve_default_group_policy(config)
    group_policy_result = resolve_allowlist_provider_runtime_group_policy({
        "providerConfigPresent": config.get("channels", {}).get("googlechat") is not None,
        "groupPolicy": account.config.get("groupPolicy"),
        "defaultGroupPolicy": default_group_policy,
    })
    group_policy = group_policy_result.get("groupPolicy")
    provider_missing_fallback_applied = group_policy_result.get("providerMissingFallbackApplied")

    warn_missing_provider_group_policy_fallback_once({
        "providerMissingFallbackApplied": provider_missing_fallback_applied,
        "providerKey": "googlechat",
        "accountId": account.account_id,
        "blockedLabel": GROUP_POLICY_BLOCKED_LABEL.get("space", ""),
        "log": log_verbose,
    })

    _warn_mutable_group_keys_configured(log_verbose, account.config.get("groups"))

    group_config_resolved = _resolve_group_config({
        "groupId": space_id,
        "groupName": space.get("displayName"),
        "groups": account.config.get("groups"),
    })
    group_entry = group_config_resolved.get("entry")
    group_users = (group_entry or {}).get("users") or account.config.get("groupAllowFrom", [])

    effective_was_mentioned = None
    dm_policy = (account.config.get("dm") or {}).get("policy", "pairing")
    raw_config_allow_from = normalize_string_entries((account.config.get("dm") or {}).get("allowFrom"))

    should_compute_auth = core.channel.commands.should_compute_command_authorized(raw_body, config)

    group_activation = None
    if is_group:
        require_mention = (group_entry or {}).get("requireMention", account.config.get("requireMention", True))
        mention_info = _extract_mention_info(message.get("annotations"), account.config.get("botUser"))
        group_activation = {
            "requireMention": require_mention,
            "allowTextCommands": core.channel.commands.should_handle_text_commands({
                "cfg": config,
                "surface": "googlechat",
            }),
            "hasControlCommand": core.channel.text.has_control_command(raw_body, config),
            "wasMentioned": mention_info.get("wasMentioned", False),
            "hasAnyMention": mention_info.get("hasAnyMention", False),
        }

    command = {
        "hasControlCommand": (group_activation or {}).get("hasControlCommand", should_compute_auth),
        "groupOwnerAllowFrom": "none",
    }

    group_allow_from = normalize_string_entries(group_users)
    sender_group_policy = group_policy
    if group_config_resolved.get("allowlistConfigured") and len(group_allow_from) == 0:
        sender_group_policy = group_policy
    elif group_policy == "disabled":
        sender_group_policy = "disabled"
    elif len(group_allow_from) > 0:
        sender_group_policy = "allowlist"
    else:
        sender_group_policy = "open"

    route = channel_ingress_routes(
        is_group and group_policy != "disabled" and (group_entry or {}).get("enabled") is False and {
            "id": "googlechat:space",
            "enabled": False,
            "matched": True,
            "matchId": "googlechat-space",
            "blockReason": "route_disabled",
        },
        is_group and group_policy == "allowlist" and (group_entry or {}).get("enabled") is not False and not group_config_resolved.get("allowlistConfigured") and {
            "id": "googlechat:space",
            "allowed": False,
            "blockReason": "empty_allowlist",
        },
        is_group and group_policy == "allowlist" and (group_entry or {}).get("enabled") is not False and group_config_resolved.get("allowlistConfigured") and {
            "id": "googlechat:space",
            "senderPolicy": "deny-when-empty",
            **({"senderAllowFromSource": "effective-group"} if group_entry else {}),
            "allowed": bool(group_entry),
            "matchId": "googlechat-space",
            "blockReason": "sender_empty_allowlist" if group_entry else "route_not_allowlisted",
        },
    )

    resolver = create_channel_ingress_resolver({
        "channelId": "googlechat",
        "accountId": account.account_id,
        "identity": google_chat_ingress_identity,
        "cfg": config,
        "readStoreAllowFrom": pairing.read_allow_from_store,
    })

    resolved_access = resolver.message({
        "subject": {
            "stableId": sender_id,
            "aliases": {"email": sender_email},
        },
        "conversation": {
            "kind": "group" if is_group else "direct",
            "id": space_id,
        },
        "route": route,
        "allowFrom": raw_config_allow_from,
        "groupAllowFrom": group_allow_from,
        "dmPolicy": dm_policy,
        "groupPolicy": sender_group_policy,
        "policy": {
            "groupAllowFromFallbackToAllowFrom": False,
            "mutableIdentifierMatching": "enabled" if allow_name_matching else "disabled",
            **(group_activation and {
                "activation": {
                    "requireMention": group_activation["requireMention"],
                    "allowTextCommands": group_activation["allowTextCommands"],
                },
            } or {}),
        },
        **(group_activation is not None and {
            "mentionFacts": {
                "canDetectMention": True,
                "wasMentioned": group_activation["wasMentioned"],
                "hasAnyMention": group_activation["hasAnyMention"],
                "implicitMentionKinds": [],
            },
        } or {}),
        "command": command,
    })

    sender_access = resolved_access["senderAccess"]
    command_authorized = None
    if resolved_access["commandAccess"]["requested"]:
        command_authorized = resolved_access["commandAccess"]["authorized"]

    if is_group:
        if group_config_resolved.get("deprecatedNameMatch"):
            log_verbose(f"drop group message (deprecated mutable group key matched, space={space_id})")
            return {"ok": False}

        route_block_reason = resolved_access["routeAccess"].get("reason")
        if route_block_reason and route_block_reason != "sender_empty_allowlist":
            if route_block_reason == "empty_allowlist":
                log_verbose("drop group message (groupPolicy=allowlist, no allowlist)")
            elif route_block_reason == "route_not_allowlisted":
                log_verbose("drop group message (not allowlisted)")
            elif route_block_reason == "route_disabled":
                log_verbose("drop group message (space disabled)")
            return {"ok": False}

        if len(sender_access.get("effectiveGroupAllowFrom", [])) > 0 and sender_access.get("decision") != "allow":
            _warn_deprecated_users_email_entries(log_verbose, sender_access.get("effectiveGroupAllowFrom", []))
            log_verbose(f"drop group message (sender not allowed, {sender_id})")
            return {"ok": False}

    effective_allow_from = sender_access.get("effectiveAllowFrom", [])
    _warn_deprecated_users_email_entries(log_verbose, effective_allow_from)

    if is_group and resolved_access["activationAccess"].get("ran"):
        effective_was_mentioned = resolved_access["activationAccess"].get("effectiveWasMentioned")
        if resolved_access["activationAccess"].get("shouldSkip"):
            log_verbose("drop group message (mention required)")
            return {"ok": False}

    if is_group and sender_access.get("decision") != "allow":
        reason = resolved_access["ingress"].get("reasonCode", "")
        log_verbose(f"drop group message (sender policy blocked, reason={reason})")
        return {"ok": False}

    if not is_group:
        if (account.config.get("dm") or {}).get("enabled") is False:
            log_verbose(f"Blocked Google Chat DM from {sender_id} (dmPolicy=disabled)")
            return {"ok": False}

        if sender_access.get("decision") != "allow":
            if sender_access.get("decision") == "pairing":
                async def _send_pairing_reply(text: str) -> None:
                    await send_google_chat_message({
                        "account": account,
                        "space": space_id,
                        "text": text,
                    })
                    if status_sink:
                        status_sink({"lastOutboundAt": __import__("time").time() * 1000})

                await pairing.issue_challenge({
                    "senderId": sender_id,
                    "senderIdLine": f"Your Google Chat user id: {sender_id}",
                    "meta": {"name": sender_name, "email": sender_email},
                    "onCreated": lambda: log_verbose(f"googlechat pairing request sender={sender_id}"),
                    "sendPairingReply": _send_pairing_reply,
                    "onReplyError": lambda err: log_verbose(f"pairing reply failed for {sender_id}: {err}"),
                })
            else:
                log_verbose(f"Blocked unauthorized Google Chat sender {sender_id} (dmPolicy={dm_policy})")
            return {"ok": False}

    if is_group and core.channel.commands.is_control_command_message(raw_body, config) and command_authorized is not True:
        log_verbose(f"googlechat: drop control command from {sender_id}")
        return {"ok": False}

    return {
        "ok": True,
        "commandAuthorized": command_authorized,
        "effectiveWasMentioned": effective_was_mentioned,
        "groupBotLoopProtection": (group_entry or {}).get("botLoopProtection"),
        "groupSystemPrompt": normalize_optional_string((group_entry or {}).get("systemPrompt")),
    }


__all__ = ["apply_google_chat_inbound_access_policy"]